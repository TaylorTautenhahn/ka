#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFilter
except ImportError as exc:  # pragma: no cover - import guard for user envs
    raise SystemExit(
        "This script needs Pillow and NumPy.\n"
        "Install them in the repo virtualenv with:\n"
        "  ./.venv/bin/pip install pillow numpy"
    ) from exc


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "output" / "block_blast_calibration.json"
DEFAULT_ASSIST_TEXT_PATH = ROOT / "output" / "block_blast_assist.txt"
MOUSE_HELPER_SOURCE = ROOT / "scripts" / "block_blast_mouse.swift"
MOUSE_HELPER_BINARY = ROOT / "tmp" / "block_blast_mouse"
BOARD_SIZE = 10
AUTO_BOARD_RATIOS = {
    "left": 0.018211920529801324,
    "top": 0.2742155525238745,
    "right": 0.9867549668874173,
    "bottom": 0.7162346521145976,
}
AUTO_SLOT_RATIOS = (
    (0.23013245033112584, 0.8717598908594816),
    (0.5016556291390728, 0.8703956343792633),
    (0.7251655629139073, 0.8710777626193724),
)
AUTO_WINDOW_EXCLUDE_OWNERS = {
    "Codex",
    "Terminal",
    "Finder",
    "Google Chrome",
    "Dock",
    "Notification Center",
    "Control Center",
    "Window Server",
}
DEFAULT_TUNING = {
    "empty_cell_threshold": 28.0,
    "piece_block_scale": 0.5,
    "slot_crop_width_scale": 5.8,
    "slot_crop_height_scale": 5.5,
}
MAX_SEARCH_PLACEMENTS_PER_PIECE = 18
MAX_LIVE_PLACEMENTS_PER_PIECE = 8


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Rect:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    def contains(self, point: Point) -> bool:
        return self.left <= point.x <= self.right and self.top <= point.y <= self.bottom

    def to_capture_tuple(self) -> tuple[int, int, int, int]:
        return (
            int(round(self.left)),
            int(round(self.top)),
            int(round(self.width)),
            int(round(self.height)),
        )


def playable_board_rect(board_rect: Rect) -> Rect:
    inset_x = board_rect.width * 0.028
    inset_y = board_rect.height * 0.028
    return Rect(
        left=board_rect.left + inset_x,
        top=board_rect.top + inset_y,
        right=board_rect.right - inset_x,
        bottom=board_rect.bottom - inset_y,
    )


def overlay_board_rect(board_rect: Rect) -> Rect:
    inset_x = board_rect.width * 0.044
    inset_y = board_rect.height * 0.044
    return Rect(
        left=board_rect.left + inset_x,
        top=board_rect.top + inset_y,
        right=board_rect.right - inset_x,
        bottom=board_rect.bottom - inset_y,
    )


def _smooth_scores(values: np.ndarray) -> np.ndarray:
    kernel = np.array([1.0, 2.0, 3.0, 2.0, 1.0], dtype=np.float32)
    kernel /= kernel.sum()
    return np.convolve(values.astype(np.float32), kernel, mode="same")


def _find_dark_line_peaks(scores: np.ndarray, rough_spacing: float) -> list[int]:
    smoothed = _smooth_scores(scores)
    threshold = float(np.percentile(smoothed, 72))
    min_gap = max(3, int(round(rough_spacing * 0.45)))
    peaks: list[int] = []
    for index in range(1, len(smoothed) - 1):
        if smoothed[index] < threshold:
            continue
        if smoothed[index] < smoothed[index - 1] or smoothed[index] < smoothed[index + 1]:
            continue
        if peaks and (index - peaks[-1]) < min_gap:
            if smoothed[index] > smoothed[peaks[-1]]:
                peaks[-1] = index
            continue
        peaks.append(index)
    return peaks


def _grid_lines_from_peaks(peaks: Sequence[int], rough_spacing: float, expected_lines: int) -> list[float] | None:
    if len(peaks) < 2:
        return None

    candidates: list[tuple[tuple[int, float, float], list[float]]] = []
    tolerance = max(3.0, rough_spacing * 0.24)

    for start_index, start_peak in enumerate(peaks):
        for end_index in range(start_index + 1, len(peaks)):
            span = peaks[end_index] - start_peak
            steps = end_index - start_index
            if steps <= 0:
                continue
            spacing = span / steps
            if not (rough_spacing * 0.65 <= spacing <= rough_spacing * 1.35):
                continue

            expected = [start_peak + (spacing * idx) for idx in range(expected_lines)]
            matches = 0
            total_error = 0.0
            snapped: list[float] = []
            for value in expected:
                nearest = min(peaks, key=lambda peak: abs(peak - value))
                error = abs(nearest - value)
                if error <= tolerance:
                    snapped.append(float(nearest))
                    matches += 1
                    total_error += error
                else:
                    snapped.append(float(value))
                    total_error += tolerance * 1.5
            spacing_error = abs(spacing - rough_spacing)
            candidates.append(((matches, -total_error, -spacing_error), snapped))

    if not candidates:
        return None

    best = max(candidates, key=lambda item: item[0])[1]
    if len(best) != expected_lines:
        return None
    return best


def detect_grid_aligned_board_rect(image: Image.Image, board_rect: Rect, capture_region: Rect) -> Rect:
    scale_x, scale_y = capture_scale(image, capture_region)
    rel_left = int(round((board_rect.left - capture_region.left) * scale_x))
    rel_top = int(round((board_rect.top - capture_region.top) * scale_y))
    rel_right = int(round((board_rect.right - capture_region.left) * scale_x))
    rel_bottom = int(round((board_rect.bottom - capture_region.top) * scale_y))
    board_crop = np.array(image.crop((rel_left, rel_top, rel_right, rel_bottom)).convert("L")).astype(np.float32)
    if board_crop.size == 0:
        return playable_board_rect(board_rect)

    darkness = 255.0 - board_crop
    score_x = np.percentile(darkness, 70, axis=0)
    score_y = np.percentile(darkness, 70, axis=1)
    rough_spacing_x = board_crop.shape[1] / BOARD_SIZE
    rough_spacing_y = board_crop.shape[0] / BOARD_SIZE
    line_x = _grid_lines_from_peaks(_find_dark_line_peaks(score_x, rough_spacing_x), rough_spacing_x, BOARD_SIZE + 1)
    line_y = _grid_lines_from_peaks(_find_dark_line_peaks(score_y, rough_spacing_y), rough_spacing_y, BOARD_SIZE + 1)
    if line_x is None or line_y is None:
        return playable_board_rect(board_rect)

    pitch_x = float(np.median(np.diff(line_x))) if len(line_x) >= 2 else rough_spacing_x
    pitch_y = float(np.median(np.diff(line_y))) if len(line_y) >= 2 else rough_spacing_y
    left_local = max(0.0, line_x[0] - (pitch_x / 2.0))
    top_local = max(0.0, line_y[0] - (pitch_y / 2.0))
    right_local = min(float(board_crop.shape[1]), line_x[-1] + (pitch_x / 2.0))
    bottom_local = min(float(board_crop.shape[0]), line_y[-1] + (pitch_y / 2.0))

    return Rect(
        left=board_rect.left + (left_local / scale_x),
        top=board_rect.top + (top_local / scale_y),
        right=board_rect.left + (right_local / scale_x),
        bottom=board_rect.top + (bottom_local / scale_y),
    )


@dataclass(frozen=True)
class Piece:
    cells: tuple[tuple[int, int], ...]
    source_centroid: Point
    source_grab_point: Point
    grab_cell: tuple[int, int]
    slot_index: int

    @property
    def width(self) -> int:
        return max(x for x, _ in self.cells) + 1

    @property
    def height(self) -> int:
        return max(y for _, y in self.cells) + 1

    @property
    def size(self) -> int:
        return len(self.cells)

    def label(self) -> str:
        return f"slot-{self.slot_index + 1}:{self.cells}"


@dataclass(frozen=True)
class Move:
    piece_index: int
    slot_index: int
    anchor_col: int
    anchor_row: int
    cleared_lines: int
    target_centroid: Point
    target_grab_point: Point


@dataclass(frozen=True)
class SearchResult:
    score: tuple[int, int, int, int, int, int]
    moves: tuple[Move, ...]
    placed_count: int


@dataclass(frozen=True)
class WindowInfo:
    owner_name: str
    window_name: str
    layer: int
    x: float
    y: float
    width: float
    height: float

    @property
    def rect(self) -> Rect:
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)


@dataclass(frozen=True)
class InferredPlacement:
    anchor_col: int
    anchor_row: int
    board: tuple[tuple[bool, ...], ...]


@dataclass(frozen=True)
class BoardDetectionDebug:
    board: tuple[tuple[bool, ...], ...]
    color_scores: tuple[tuple[float, ...], ...]
    bright_scores: tuple[tuple[float, ...], ...]
    std_scores: tuple[tuple[float, ...], ...]
    occupied_scores: tuple[tuple[float, ...], ...]
    thresholds: dict[str, float]


def run_command(args: Sequence[str], *, capture_output: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=True,
        capture_output=capture_output,
        text=True,
    )


def ensure_mouse_helper() -> Path:
    if MOUSE_HELPER_BINARY.exists() and MOUSE_HELPER_BINARY.stat().st_mtime >= MOUSE_HELPER_SOURCE.stat().st_mtime:
        return MOUSE_HELPER_BINARY

    MOUSE_HELPER_BINARY.parent.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            "swiftc",
            str(MOUSE_HELPER_SOURCE),
            "-O",
            "-o",
            str(MOUSE_HELPER_BINARY),
        ],
        capture_output=True,
    )
    return MOUSE_HELPER_BINARY


def helper_position() -> Point:
    helper = ensure_mouse_helper()
    result = run_command([str(helper), "position"])
    raw = result.stdout.strip().split()
    if len(raw) != 2:
        raise RuntimeError(f"Unexpected mouse helper output: {result.stdout!r}")
    return Point(float(raw[0]), float(raw[1]))


def helper_windows() -> list[WindowInfo]:
    helper = ensure_mouse_helper()
    result = run_command([str(helper), "windows"])
    payload = json.loads(result.stdout)
    return [
        WindowInfo(
            owner_name=str(item.get("ownerName", "")),
            window_name=str(item.get("windowName", "")),
            layer=int(item.get("layer", 0)),
            x=float(item.get("x", 0.0)),
            y=float(item.get("y", 0.0)),
            width=float(item.get("width", 0.0)),
            height=float(item.get("height", 0.0)),
        )
        for item in payload
    ]


def helper_drag(start: Point, end: Point, duration_ms: int) -> None:
    helper = ensure_mouse_helper()
    run_command(
        [
            str(helper),
            "drag",
            str(start.x),
            str(start.y),
            str(end.x),
            str(end.y),
            str(duration_ms),
        ],
        capture_output=True,
    )


def helper_mouse_down(point: Point) -> None:
    helper = ensure_mouse_helper()
    run_command([str(helper), "down", str(point.x), str(point.y)], capture_output=True)


def helper_drag_to(point: Point, duration_ms: int) -> None:
    helper = ensure_mouse_helper()
    run_command(
        [str(helper), "dragto", str(point.x), str(point.y), str(duration_ms)],
        capture_output=True,
    )


def helper_mouse_up(point: Point | None = None) -> None:
    helper = ensure_mouse_helper()
    args = [str(helper), "up"]
    if point is not None:
        args.extend([str(point.x), str(point.y)])
    run_command(args, capture_output=True)


def prompt_point(prompt: str) -> Point:
    print(prompt)
    input("Press Enter when the cursor is in place...")
    point = helper_position()
    print(f"Captured: ({int(point.x)}, {int(point.y)})")
    return point


def rect_from_points(a: Point, b: Point) -> Rect:
    return Rect(
        left=min(a.x, b.x),
        top=min(a.y, b.y),
        right=max(a.x, b.x),
        bottom=max(a.y, b.y),
    )


def save_config(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def auto_config_from_window(window: WindowInfo) -> dict:
    capture_region = window.rect
    board_rect = Rect(
        left=capture_region.left + (capture_region.width * AUTO_BOARD_RATIOS["left"]),
        top=capture_region.top + (capture_region.height * AUTO_BOARD_RATIOS["top"]),
        right=capture_region.left + (capture_region.width * AUTO_BOARD_RATIOS["right"]),
        bottom=capture_region.top + (capture_region.height * AUTO_BOARD_RATIOS["bottom"]),
    )
    slot_centers = [
        Point(
            capture_region.left + (capture_region.width * ratio_x),
            capture_region.top + (capture_region.height * ratio_y),
        )
        for ratio_x, ratio_y in AUTO_SLOT_RATIOS
    ]
    return {
        "capture_region": rect_to_dict(capture_region),
        "board_rect": rect_to_dict(board_rect),
        "piece_slot_centers": [point_to_dict(point) for point in slot_centers],
        "tuning": {
            "empty_cell_threshold": 28.0,
            "piece_block_scale": 0.5,
            "slot_crop_width_scale": 5.8,
            "slot_crop_height_scale": 5.5,
        },
        "auto_window": {
            "owner_name": window.owner_name,
            "window_name": window.window_name,
            "bounds": rect_to_dict(capture_region),
        },
    }


def ratios_from_config(config: dict) -> tuple[dict[str, float], tuple[tuple[float, float], ...]]:
    capture_region = rect_from_dict(config["capture_region"])
    board_rect = rect_from_dict(config["board_rect"])
    slot_centers = [point_from_dict(item) for item in config["piece_slot_centers"]]

    if capture_region.width <= 0 or capture_region.height <= 0:
        raise ValueError("Capture region must have positive size to derive ratios.")

    board_ratios = {
        "left": (board_rect.left - capture_region.left) / capture_region.width,
        "top": (board_rect.top - capture_region.top) / capture_region.height,
        "right": (board_rect.right - capture_region.left) / capture_region.width,
        "bottom": (board_rect.bottom - capture_region.top) / capture_region.height,
    }
    slot_ratios = tuple(
        (
            (point.x - capture_region.left) / capture_region.width,
            (point.y - capture_region.top) / capture_region.height,
        )
        for point in slot_centers
    )
    return board_ratios, slot_ratios


def auto_config_from_window_with_ratios(
    window: WindowInfo,
    board_ratios: dict[str, float],
    slot_ratios: Sequence[tuple[float, float]],
) -> dict:
    capture_region = window.rect
    board_rect = Rect(
        left=capture_region.left + (capture_region.width * board_ratios["left"]),
        top=capture_region.top + (capture_region.height * board_ratios["top"]),
        right=capture_region.left + (capture_region.width * board_ratios["right"]),
        bottom=capture_region.top + (capture_region.height * board_ratios["bottom"]),
    )
    slot_centers = [
        Point(
            capture_region.left + (capture_region.width * ratio_x),
            capture_region.top + (capture_region.height * ratio_y),
        )
        for ratio_x, ratio_y in slot_ratios
    ]
    auto_config = auto_config_from_window(window)
    auto_config["capture_region"] = rect_to_dict(capture_region)
    auto_config["board_rect"] = rect_to_dict(board_rect)
    auto_config["piece_slot_centers"] = [point_to_dict(point) for point in slot_centers]
    auto_config["auto_window"]["ratio_source"] = "saved_calibration"
    return auto_config


def find_mirroring_window() -> WindowInfo | None:
    windows = helper_windows()
    candidates = [window for window in windows if window.layer == 0 and window.width >= 220 and window.height >= 500]
    if not candidates:
        return None

    preferred_keywords = ("iphone mirroring", "iphone", "mirroring")
    matching_candidates = [
        window
        for window in candidates
        if any(keyword in window.owner_name.lower() for keyword in preferred_keywords)
        or any(keyword in window.window_name.lower() for keyword in preferred_keywords)
    ]
    if not matching_candidates:
        return None

    def score(window: WindowInfo) -> tuple[int, float, float]:
        owner_lower = window.owner_name.lower()
        name_lower = window.window_name.lower()
        keyword_score = 0
        if any(keyword in owner_lower for keyword in preferred_keywords):
            keyword_score += 3
        if any(keyword in name_lower for keyword in preferred_keywords):
            keyword_score += 2
        if window.owner_name in AUTO_WINDOW_EXCLUDE_OWNERS:
            keyword_score -= 3

        aspect_ratio = window.width / max(window.height, 1.0)
        ratio_distance = abs(aspect_ratio - 0.412)
        area = window.width * window.height
        return (keyword_score, -ratio_distance, area)

    return max(matching_candidates, key=score)


def resolve_runtime_config(config_path: Path, allow_auto_window: bool) -> dict:
    saved_config = load_config(config_path) if config_path.exists() else None
    if allow_auto_window:
        try:
            window = find_mirroring_window()
        except Exception:
            window = None
        if window is not None:
            base_tuning = saved_config.get("tuning", {}) if saved_config is not None else {}
            saved_slot_ratios = None
            if saved_config is not None:
                try:
                    _, saved_slot_ratios = ratios_from_config(saved_config)
                except Exception:
                    saved_slot_ratios = None
            try:
                image = capture_image(window.rect)
                return build_live_auto_config(window, image, base_tuning, saved_slot_ratios)
            except Exception:
                if saved_config is not None:
                    try:
                        board_ratios, slot_ratios = ratios_from_config(saved_config)
                        return auto_config_from_window_with_ratios(window, board_ratios, slot_ratios)
                    except Exception:
                        pass
                return auto_config_from_window(window)

    if saved_config is None:
        raise SystemExit(
            f"Calibration file not found at {config_path}.\n"
            "Run this first:\n"
            "  ./.venv/bin/python scripts/block_blast_bot.py --calibrate"
        )
    return saved_config


def validate_config(config: dict) -> None:
    capture_region = rect_from_dict(config["capture_region"])
    board_rect = rect_from_dict(config["board_rect"])
    slot_centers = [point_from_dict(item) for item in config["piece_slot_centers"]]
    tolerance = 4.0
    auto_window = config.get("auto_window")

    issues: list[str] = []

    if board_rect.left < (capture_region.left - tolerance) or board_rect.top < (capture_region.top - tolerance):
        issues.append("The board top-left corner sits outside the captured mirroring region.")
    if board_rect.right > (capture_region.right + tolerance) or board_rect.bottom > (capture_region.bottom + tolerance):
        issues.append("The board bottom-right corner sits outside the captured mirroring region.")

    for index, point in enumerate(slot_centers, start=1):
        if not capture_region.contains(point):
            issues.append(f"Piece slot {index} is outside the captured mirroring region.")

    x_values = [point.x for point in slot_centers]
    if x_values != sorted(x_values):
        issues.append("The three piece slots are not ordered left-to-right.")

    min_expected_slot_y = board_rect.bottom + (board_rect.height * (0.12 if auto_window else 0.2))
    if slot_centers and max(point.y for point in slot_centers) < min_expected_slot_y:
        issues.append("The three slot clicks are too high on the screen. Click the centers of the playable block pieces in the bottom tray, not the top score/multiplier area.")

    if issues:
        joined = "\n- ".join(issues)
        raise SystemExit(
            "Calibration looks invalid:\n"
            f"- {joined}\n\n"
            "Run calibration again and click the mirrored iPhone bounds first, then the board interior, then the centers of the three pieces in the bottom tray:\n"
            "  ./.venv/bin/python scripts/block_blast_bot.py --calibrate"
        )


def point_from_dict(data: dict) -> Point:
    return Point(float(data["x"]), float(data["y"]))


def rect_from_dict(data: dict) -> Rect:
    return Rect(
        left=float(data["left"]),
        top=float(data["top"]),
        right=float(data["right"]),
        bottom=float(data["bottom"]),
    )


def capture_image(capture_region: Rect) -> Image.Image:
    left, top, width, height = capture_region.to_capture_tuple()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        run_command(
            [
                "/usr/sbin/screencapture",
                "-x",
                "-R",
                f"{left},{top},{width},{height}",
                str(temp_path),
            ]
        )
        with Image.open(temp_path) as image:
            return image.convert("RGB").copy()
    finally:
        temp_path.unlink(missing_ok=True)


def helper_capture_image(capture_region: Rect) -> Image.Image:
    helper = ensure_mouse_helper()
    left, top, width, height = capture_region.to_capture_tuple()
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        temp_path = Path(temp_file.name)
    try:
        run_command(
            [
                str(helper),
                "capture",
                str(left),
                str(top),
                str(width),
                str(height),
                str(temp_path),
            ],
            capture_output=True,
        )
        with Image.open(temp_path) as image:
            return image.convert("RGB").copy()
    finally:
        temp_path.unlink(missing_ok=True)


def game_color_metrics(image: Image.Image) -> tuple[float, float]:
    arr = np.asarray(image).astype(np.float32) / 255.0
    channel_max = arr.max(axis=2)
    channel_min = arr.min(axis=2)
    saturation = np.divide(
        channel_max - channel_min,
        channel_max,
        out=np.zeros_like(channel_max),
        where=channel_max > 0,
    )
    return float(saturation.mean()), float((saturation > 0.25).mean())


def ensure_game_screen_visible(image: Image.Image) -> None:
    mean_saturation, colorful_fraction = game_color_metrics(image)
    if mean_saturation < 0.18 and colorful_fraction < 0.25:
        raise RuntimeError(
            "The iPhone Mirroring window does not currently show the game screen. "
            "It looks disconnected or covered. Bring Block Blast back into view in iPhone Mirroring and try again."
        )


def describe_capture_source(config: dict) -> str:
    auto_window = config.get("auto_window")
    if auto_window:
        owner_name = str(auto_window.get("owner_name", "")).strip() or "unknown owner"
        window_name = str(auto_window.get("window_name", "")).strip() or "unnamed window"
        return f"auto-window: {owner_name} / {window_name}"
    return "saved calibration region"


def configured_board_region_looks_plausible(image: Image.Image, board_rect: Rect, capture_region: Rect) -> bool:
    scale_x, scale_y = capture_scale(image, capture_region)
    rel_left = int(round((board_rect.left - capture_region.left) * scale_x))
    rel_top = int(round((board_rect.top - capture_region.top) * scale_y))
    rel_right = int(round((board_rect.right - capture_region.left) * scale_x))
    rel_bottom = int(round((board_rect.bottom - capture_region.top) * scale_y))
    if rel_right <= rel_left or rel_bottom <= rel_top:
        return False

    crop = np.array(image.crop((rel_left, rel_top, rel_right, rel_bottom)).convert("RGB"))
    if crop.size == 0:
        return False

    height, width = crop.shape[:2]
    aspect_ratio = width / max(height, 1)
    if not 0.82 <= aspect_ratio <= 1.18:
        return False

    crop_hsv = np.array(Image.fromarray(crop).convert("HSV"))
    hue = crop_hsv[:, :, 0]
    sat = crop_hsv[:, :, 1]
    val = crop_hsv[:, :, 2]
    purple_mask = (
        (hue >= 150)
        & (hue <= 220)
        & (sat >= 45)
        & (val >= 40)
        & (val <= 185)
    )
    return float(purple_mask.mean()) >= 0.18


def capture_looks_like_block_blast(image: Image.Image, config: dict) -> bool:
    try:
        detect_board_rect_from_capture_image(image)
        return True
    except Exception:
        pass

    try:
        return configured_board_region_looks_plausible(
            image,
            rect_from_dict(config["board_rect"]),
            rect_from_dict(config["capture_region"]),
        )
    except Exception:
        return False


def ensure_block_blast_visible(image: Image.Image, config: dict) -> None:
    ensure_game_screen_visible(image)
    if capture_looks_like_block_blast(image, config):
        return
    raise RuntimeError(
        "The current capture does not look like a Block Blast board. "
        f"Capture source: {describe_capture_source(config)}. "
        "Open iPhone Mirroring with Block Blast visible, or use --analyze-image on a screenshot."
    )


def rgb_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a.astype(float) - b.astype(float)))


def capture_scale(image: Image.Image, capture_region: Rect) -> tuple[float, float]:
    scale_x = image.width / max(capture_region.width, 1.0)
    scale_y = image.height / max(capture_region.height, 1.0)
    return scale_x, scale_y


def local_rect_to_global(local_rect: Rect, image: Image.Image, capture_region: Rect) -> Rect:
    scale_x, scale_y = capture_scale(image, capture_region)
    return Rect(
        left=capture_region.left + (local_rect.left / scale_x),
        top=capture_region.top + (local_rect.top / scale_y),
        right=capture_region.left + (local_rect.right / scale_x),
        bottom=capture_region.top + (local_rect.bottom / scale_y),
    )


def local_point_to_global(local_point: Point, image: Image.Image, capture_region: Rect) -> Point:
    scale_x, scale_y = capture_scale(image, capture_region)
    return Point(
        x=capture_region.left + (local_point.x / scale_x),
        y=capture_region.top + (local_point.y / scale_y),
    )


def board_cell_medians_rgb(image: Image.Image, board_rect: Rect, capture_region: Rect) -> list[list[np.ndarray]]:
    board_rect = detect_grid_aligned_board_rect(image, board_rect, capture_region)
    scale_x, scale_y = capture_scale(image, capture_region)
    rel_left = int(round((board_rect.left - capture_region.left) * scale_x))
    rel_top = int(round((board_rect.top - capture_region.top) * scale_y))
    rel_right = int(round((board_rect.right - capture_region.left) * scale_x))
    rel_bottom = int(round((board_rect.bottom - capture_region.top) * scale_y))
    board_crop = np.array(image.crop((rel_left, rel_top, rel_right, rel_bottom)).convert("RGB"))
    cell_w = board_crop.shape[1] / BOARD_SIZE
    cell_h = board_crop.shape[0] / BOARD_SIZE

    cell_colors: list[list[np.ndarray]] = []
    for row in range(BOARD_SIZE):
        row_colors = []
        for col in range(BOARD_SIZE):
            x0 = int(round((col * cell_w) + (cell_w * 0.25)))
            x1 = int(round(((col + 1) * cell_w) - (cell_w * 0.25)))
            y0 = int(round((row * cell_h) + (cell_h * 0.25)))
            y1 = int(round(((row + 1) * cell_h) - (cell_h * 0.25)))
            patch = board_crop[y0:y1, x0:x1]
            row_colors.append(np.median(patch.reshape(-1, 3), axis=0))
        cell_colors.append(row_colors)
    return cell_colors


def component_bboxes(mask: np.ndarray, min_area: int = 1) -> list[tuple[int, int, int, int, int]]:
    components = connected_components(mask)
    boxes: list[tuple[int, int, int, int, int]] = []
    for component in components:
        if len(component) < min_area:
            continue
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        boxes.append((len(component), min(xs), min(ys), max(xs), max(ys)))
    return boxes


def detect_board_rect_from_capture_image(image: Image.Image) -> Rect:
    arr = np.array(image.convert("RGB"))
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    mask = (r < 90) & (g < 80) & (b > 70) & (b < 170)
    boxes = component_bboxes(mask, min_area=max(1000, (image.width * image.height) // 200))

    candidates: list[tuple[tuple[float, float, float], Rect]] = []
    for area, left, top, right, bottom in boxes:
        width = right - left + 1
        height = bottom - top + 1
        aspect = width / max(height, 1)
        if not (0.82 <= aspect <= 1.18):
            continue
        if top < image.height * 0.2:
            continue
        if height < image.height * 0.2 or width < image.width * 0.4:
            continue
        center_y = top + (height / 2.0)
        score = (float(area), -abs(aspect - 1.0), center_y)
        candidates.append((score, Rect(float(left), float(top), float(right + 1), float(bottom + 1))))

    if not candidates:
        raise RuntimeError("Could not auto-detect the board in the mirrored window.")
    return max(candidates, key=lambda item: item[0])[1]


def detect_phone_rect_from_image(image: Image.Image) -> Rect | None:
    arr = np.array(image.convert("RGB"))
    hsv = np.array(image.convert("HSV"))
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    mask = (sat >= 55) & (val >= 55)
    boxes = component_bboxes(mask, min_area=max(3000, (image.width * image.height) // 180))

    candidates: list[tuple[tuple[float, float, float], Rect]] = []
    for area, left, top, right, bottom in boxes:
        width = right - left + 1
        height = bottom - top + 1
        aspect = width / max(height, 1)
        if not (0.22 <= aspect <= 0.72):
            continue
        if height < image.height * 0.35 or width < image.width * 0.08:
            continue
        center_x = left + (width / 2.0)
        score = (float(area), float(height), -abs(aspect - 0.46) - (center_x / max(image.width, 1.0)))
        candidates.append((score, Rect(float(left), float(top), float(right + 1), float(bottom + 1))))

    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def detect_piece_slot_centers_from_capture_image(image: Image.Image, board_local_rect: Rect) -> list[Point]:
    arr = np.array(image.convert("RGB"))
    crop_top = int(round(board_local_rect.bottom + (image.height * 0.01)))
    crop_bottom = min(image.height, int(round(image.height * 0.98)))
    crop_left = max(0, int(round(board_local_rect.left - (image.width * 0.02))))
    crop_right = min(image.width, int(round(board_local_rect.right + (image.width * 0.02))))
    crop = arr[crop_top:crop_bottom, crop_left:crop_right]
    block_est = board_local_rect.width / BOARD_SIZE * 0.35
    mask = piece_foreground_mask(crop)
    components = connected_components(mask)
    components = merge_nearby_components(
        components,
        x_gap_limit=block_est * 0.9,
        y_gap_limit=block_est * 0.9,
    )

    dense_candidates: list[tuple[int, float, Point]] = []
    for component in components:
        if len(component) < max(120, int(block_est * block_est * 0.55)):
            continue
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        width = (max(xs) - min(xs)) + 1
        height = (max(ys) - min(ys)) + 1
        fill_ratio = len(component) / max(width * height, 1)
        if fill_ratio < 0.45:
            continue
        if width < block_est * 0.75 or height < block_est * 0.75:
            continue
        if width > block_est * 6.8 or height > block_est * 6.8:
            continue
        dense_candidates.append(
            (
                len(component),
                fill_ratio,
                Point(
                    x=crop_left + ((min(xs) + max(xs)) / 2.0),
                    y=crop_top + ((min(ys) + max(ys)) / 2.0),
                ),
            )
        )

    if len(dense_candidates) >= 3:
        best_centers = [item[2] for item in sorted(dense_candidates, key=lambda item: (item[0], item[1]), reverse=True)[:3]]
        return sorted(best_centers, key=lambda point: point.x)

    hsv = np.array(Image.fromarray(crop).convert("HSV"))
    hue, sat, val = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    fallback_mask = (sat >= 75) & (val >= 110) & ~((hue >= 165) & (hue <= 235))
    boxes = component_bboxes(fallback_mask, min_area=max(40, int(block_est * block_est * 0.18)))

    block_centers: list[Point] = []
    for area, left, top, right, bottom in boxes:
        width = right - left + 1
        height = bottom - top + 1
        if (
            block_est * 0.45 <= width <= block_est * 1.9
            and block_est * 0.45 <= height <= block_est * 1.9
        ):
            block_centers.append(
                Point(
                    x=crop_left + ((left + right) / 2.0),
                    y=crop_top + ((top + bottom) / 2.0),
                )
            )

    if not block_centers:
        return []

    block_centers = sorted(block_centers, key=lambda point: point.x)
    groups: list[list[Point]] = [[block_centers[0]]]
    gap_threshold = max(block_est * 1.7, 40.0)
    for center in block_centers[1:]:
        if center.x - groups[-1][-1].x > gap_threshold:
            groups.append([center])
        else:
            groups[-1].append(center)

    return [
        Point(
            x=sum(point.x for point in group) / len(group),
            y=sum(point.y for point in group) / len(group),
        )
        for group in groups
    ]


def detect_tray_rect_from_capture_image(image: Image.Image, board_local_rect: Rect) -> Rect | None:
    hsv = np.array(image.convert("HSV"))
    hue = hsv[:, :, 0]
    sat = hsv[:, :, 1]
    val = hsv[:, :, 2]
    mask = (hue >= 145) & (hue <= 225) & (sat >= 40) & (val >= 55) & (val <= 210)
    search_top = int(round(board_local_rect.bottom + (image.height * 0.005)))
    mask[:search_top, :] = False
    boxes = component_bboxes(mask, min_area=max(1000, (image.width * image.height) // 500))

    candidates: list[tuple[tuple[float, float, float], Rect]] = []
    for area, left, top, right, bottom in boxes:
        width = right - left + 1
        height = bottom - top + 1
        aspect = width / max(height, 1)
        if width < board_local_rect.width * 0.7:
            continue
        if height < image.height * 0.08:
            continue
        if not (1.4 <= aspect <= 3.6):
            continue
        center_y = top + (height / 2.0)
        score = (float(area), float(width), -abs(center_y - (board_local_rect.bottom + (height * 0.35))))
        candidates.append((score, Rect(float(left), float(top), float(right + 1), float(bottom + 1))))

    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def tray_slot_centers_from_rect(tray_rect: Rect) -> list[Point]:
    slot_y = tray_rect.top + (tray_rect.height * 0.38)
    return [
        Point(tray_rect.left + (tray_rect.width * ratio), slot_y)
        for ratio in (1.0 / 6.0, 0.5, 5.0 / 6.0)
    ]


def detect_tray_inner_horizontal_bounds(tray_crop_rgb: np.ndarray) -> tuple[float, float] | None:
    tray_hsv = np.array(Image.fromarray(tray_crop_rgb).convert("HSV"))
    hue = tray_hsv[:, :, 0]
    sat = tray_hsv[:, :, 1]
    val = tray_hsv[:, :, 2]
    interior_mask = (hue >= 145) & (hue <= 225) & (sat >= 22) & (val >= 32) & (val <= 135)

    row_start = int(round(tray_crop_rgb.shape[0] * 0.18))
    row_end = int(round(tray_crop_rgb.shape[0] * 0.72))
    runs: list[tuple[int, int]] = []
    min_width = tray_crop_rgb.shape[1] * 0.45

    for y in range(max(0, row_start), min(tray_crop_rgb.shape[0], row_end)):
        row = interior_mask[y]
        best_run: tuple[int, int] | None = None
        run_start: int | None = None
        for x, value in enumerate(row):
            if value and run_start is None:
                run_start = x
            if not value and run_start is not None:
                run = (run_start, x - 1)
                if (run[1] - run[0] + 1) >= min_width and (
                    best_run is None or (run[1] - run[0]) > (best_run[1] - best_run[0])
                ):
                    best_run = run
                run_start = None
        if run_start is not None:
            run = (run_start, len(row) - 1)
            if (run[1] - run[0] + 1) >= min_width and (
                best_run is None or (run[1] - run[0]) > (best_run[1] - best_run[0])
            ):
                best_run = run
        if best_run is not None:
            runs.append(best_run)

    if not runs:
        return None

    widest_runs = sorted(runs, key=lambda run: run[1] - run[0], reverse=True)[: min(12, len(runs))]
    left = float(np.median([run[0] for run in widest_runs]))
    right = float(np.median([run[1] + 1 for run in widest_runs]))
    if (right - left) < (tray_crop_rgb.shape[1] * 0.45):
        return None
    return left, right


def collapse_slot_centers(slot_centers: Sequence[Point], target_count: int = 3) -> list[Point]:
    if len(slot_centers) <= target_count:
        return sorted(slot_centers, key=lambda point: point.x)

    groups: list[list[Point]] = [[point] for point in sorted(slot_centers, key=lambda point: point.x)]
    while len(groups) > target_count:
        best_index = min(
            range(len(groups) - 1),
            key=lambda index: (
                ((sum(point.x for point in groups[index + 1]) / len(groups[index + 1]))
                 - (sum(point.x for point in groups[index]) / len(groups[index]))),
                abs(
                    (sum(point.y for point in groups[index + 1]) / len(groups[index + 1]))
                    - (sum(point.y for point in groups[index]) / len(groups[index]))
                ),
            ),
        )
        groups[best_index].extend(groups.pop(best_index + 1))

    return [
        Point(
            x=sum(point.x for point in group) / len(group),
            y=sum(point.y for point in group) / len(group),
        )
        for group in groups
    ]


def detected_slot_centers_look_plausible(
    slot_centers: Sequence[Point],
    board_rect: Rect,
    capture_region: Rect,
) -> bool:
    if len(slot_centers) != 3:
        return False

    ordered = sorted(slot_centers, key=lambda point: point.x)
    ys = [point.y for point in ordered]
    xs = [point.x for point in ordered]
    min_tray_y = board_rect.bottom + (board_rect.height * 0.04)
    max_tray_y = board_rect.bottom + (board_rect.height * 0.32)
    if any(point.y < min_tray_y or point.y > max_tray_y for point in ordered):
        return False
    if max(ys) - min(ys) > board_rect.height * 0.08:
        return False

    board_mid_x = (board_rect.left + board_rect.right) / 2.0
    span_left = board_rect.left - (board_rect.width * 0.18)
    span_right = board_rect.right + (board_rect.width * 0.18)
    if any(point.x < span_left or point.x > span_right for point in ordered):
        return False
    if not (xs[0] < board_mid_x < xs[2]):
        return False

    gap1 = xs[1] - xs[0]
    gap2 = xs[2] - xs[1]
    if gap1 <= board_rect.width * 0.12 or gap2 <= board_rect.width * 0.12:
        return False
    if max(gap1, gap2) / max(min(gap1, gap2), 1.0) > 1.9:
        return False
    return True


def board_cell_centers(board_rect: Rect) -> list[list[Point]]:
    board_rect = playable_board_rect(board_rect)
    cell_w = board_rect.width / BOARD_SIZE
    cell_h = board_rect.height / BOARD_SIZE
    return [
        [
            Point(
                board_rect.left + ((col + 0.5) * cell_w),
                board_rect.top + ((row + 0.5) * cell_h),
            )
            for col in range(BOARD_SIZE)
        ]
        for row in range(BOARD_SIZE)
    ]


def detect_board_debug(board_image: Image.Image, board_rect: Rect, capture_region: Rect, empty_threshold: float) -> BoardDetectionDebug:
    cell_colors = board_cell_medians_rgb(board_image, board_rect, capture_region)
    scale_x, scale_y = capture_scale(board_image, capture_region)
    rel_left = int(round((board_rect.left - capture_region.left) * scale_x))
    rel_top = int(round((board_rect.top - capture_region.top) * scale_y))
    rel_right = int(round((board_rect.right - capture_region.left) * scale_x))
    rel_bottom = int(round((board_rect.bottom - capture_region.top) * scale_y))
    board_crop = np.array(board_image.crop((rel_left, rel_top, rel_right, rel_bottom)).convert("RGB")).astype(np.float32)
    cell_w = board_crop.shape[1] / BOARD_SIZE
    cell_h = board_crop.shape[0] / BOARD_SIZE

    bright_scores: list[list[float]] = []
    std_scores: list[list[float]] = []
    for row in range(BOARD_SIZE):
        bright_row: list[float] = []
        std_row: list[float] = []
        for col in range(BOARD_SIZE):
            x0 = int(round((col * cell_w) + (cell_w * 0.08)))
            x1 = int(round(((col + 1) * cell_w) - (cell_w * 0.08)))
            y0 = int(round((row * cell_h) + (cell_h * 0.08)))
            y1 = int(round(((row + 1) * cell_h) - (cell_h * 0.08)))
            patch = board_crop[y0:y1, x0:x1]
            channel_max = patch.max(axis=2)
            bright_row.append(float(np.quantile(channel_max, 0.97)))
            std_row.append(float(patch.std()))
        bright_scores.append(bright_row)
        std_scores.append(std_row)

    flat_cells: list[tuple[np.ndarray, float, float, float]] = []
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            color = cell_colors[row][col]
            bright = bright_scores[row][col]
            std = std_scores[row][col]
            activity = bright + (std * 2.2)
            flat_cells.append((color, bright, std, activity))

    flat_cells.sort(key=lambda item: (item[3], item[1], item[2]))
    empty_sample_count = max(10, min(len(flat_cells), len(flat_cells) // 3))
    empty_candidates = flat_cells[:empty_sample_count]
    empty_color = np.median(np.array([item[0] for item in empty_candidates]), axis=0)
    baseline_bright = float(np.median([item[1] for item in empty_candidates]))
    baseline_std = float(np.median([item[2] for item in empty_candidates]))
    bright_threshold = baseline_bright + 35.0
    std_threshold = baseline_std + 12.0
    color_scores = [
        [rgb_distance(cell_colors[row][col], empty_color) for col in range(BOARD_SIZE)]
        for row in range(BOARD_SIZE)
    ]

    board = []
    occupied_scores: list[list[float]] = []
    for row in range(BOARD_SIZE):
        current = []
        current_scores: list[float] = []
        for col in range(BOARD_SIZE):
            color_ratio = color_scores[row][col] / max(empty_threshold, 1.0)
            bright_ratio = bright_scores[row][col] / max(bright_threshold, 1.0)
            std_ratio = std_scores[row][col] / max(std_threshold, 1.0)
            texture_ratio = max(bright_ratio, std_ratio)
            color_bonus = max(0.0, color_ratio - 1.0) * 0.12 if texture_ratio >= 0.8 else 0.0
            occupied_score = texture_ratio + color_bonus
            current_scores.append(occupied_score)
            current.append(occupied_score >= 1.0)
        board.append(current)
        occupied_scores.append(current_scores)
    return BoardDetectionDebug(
        board=board_to_tuple(board),
        color_scores=tuple(tuple(float(value) for value in row) for row in color_scores),
        bright_scores=tuple(tuple(float(value) for value in row) for row in bright_scores),
        std_scores=tuple(tuple(float(value) for value in row) for row in std_scores),
        occupied_scores=tuple(tuple(float(value) for value in row) for row in occupied_scores),
        thresholds={
            "empty_cell_threshold": float(empty_threshold),
            "bright_threshold": float(bright_threshold),
            "std_threshold": float(std_threshold),
        },
    )


def detect_board(board_image: Image.Image, board_rect: Rect, capture_region: Rect, empty_threshold: float) -> list[list[bool]]:
    return board_from_signature(detect_board_debug(board_image, board_rect, capture_region, empty_threshold).board)


def preview_delta_score(before_rgb: np.ndarray, after_rgb: np.ndarray) -> float:
    before_max = float(np.max(before_rgb))
    after_max = float(np.max(after_rgb))
    return max(0.0, after_max - before_max) + max(0.0, float(after_rgb[0] - before_rgb[0])) + max(
        0.0, float(after_rgb[2] - before_rgb[2])
    )


def detect_preview_anchor(
    before_image: Image.Image,
    after_image: Image.Image,
    board_rect: Rect,
    capture_region: Rect,
    board: Sequence[Sequence[bool]],
    piece: Piece,
) -> tuple[tuple[int, int] | None, float]:
    before_cells = board_cell_medians_rgb(before_image, board_rect, capture_region)
    after_cells = board_cell_medians_rgb(after_image, board_rect, capture_region)
    deltas = [
        [preview_delta_score(before_cells[row][col], after_cells[row][col]) for col in range(BOARD_SIZE)]
        for row in range(BOARD_SIZE)
    ]

    best_anchor: tuple[int, int] | None = None
    best_score_tuple = (float("-inf"), float("-inf"), float("-inf"))
    visible_cells = tuple(cell for cell in piece.cells if cell != piece.grab_cell) or piece.cells
    subset_size = max(1, min(len(visible_cells), max(1, (len(visible_cells) + 1) // 2)))
    for anchor_col, anchor_row in legal_placements(board, piece):
        visible_scores = sorted(
            (deltas[anchor_row + y][anchor_col + x] for x, y in visible_cells),
            reverse=True,
        )
        top_visible_sum = sum(visible_scores[:subset_size])
        strong_visible_count = sum(score >= 30.0 for score in visible_scores)
        full_sum = sum(deltas[anchor_row + y][anchor_col + x] for x, y in piece.cells)
        score_tuple = (top_visible_sum, float(strong_visible_count), full_sum)
        if score_tuple > best_score_tuple:
            best_score_tuple = score_tuple
            best_anchor = (anchor_col, anchor_row)
    return best_anchor, best_score_tuple[0]


def connected_components(mask: np.ndarray) -> list[list[tuple[int, int]]]:
    height, width = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    components: list[list[tuple[int, int]]] = []

    for y in range(height):
        for x in range(width):
            if not mask[y, x] or seen[y, x]:
                continue
            queue = deque([(x, y)])
            seen[y, x] = True
            points: list[tuple[int, int]] = []
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        queue.append((nx, ny))
            components.append(points)
    return components


def merge_nearby_components(
    components: Sequence[list[tuple[int, int]]],
    x_gap_limit: float,
    y_gap_limit: float,
) -> list[list[tuple[int, int]]]:
    groups = [list(component) for component in components]
    changed = True
    while changed and len(groups) > 1:
        changed = False
        merged: list[list[tuple[int, int]]] = []
        consumed = [False] * len(groups)
        for index, component in enumerate(groups):
            if consumed[index]:
                continue
            xs = [point[0] for point in component]
            ys = [point[1] for point in component]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            current = list(component)
            consumed[index] = True
            for other_index in range(index + 1, len(groups)):
                if consumed[other_index]:
                    continue
                other = groups[other_index]
                other_xs = [point[0] for point in other]
                other_ys = [point[1] for point in other]
                other_min_x, other_max_x = min(other_xs), max(other_xs)
                other_min_y, other_max_y = min(other_ys), max(other_ys)

                gap_x = max(0, max(min_x, other_min_x) - min(max_x, other_max_x) - 1)
                gap_y = max(0, max(min_y, other_min_y) - min(max_y, other_max_y) - 1)
                overlap_x = min(max_x, other_max_x) - max(min_x, other_min_x)
                overlap_y = min(max_y, other_max_y) - max(min_y, other_min_y)
                close_enough = (
                    (gap_y <= y_gap_limit and overlap_x >= -x_gap_limit * 0.4)
                    or (gap_x <= x_gap_limit and overlap_y >= -y_gap_limit * 0.4)
                )
                if not close_enough:
                    continue

                current.extend(other)
                min_x, max_x = min(min_x, other_min_x), max(max_x, other_max_x)
                min_y, max_y = min(min_y, other_min_y), max(max_y, other_max_y)
                consumed[other_index] = True
                changed = True
            merged.append(current)
        groups = merged
    return groups


def cluster_axis(values: Iterable[float], tolerance: float) -> list[float]:
    ordered = sorted(values)
    if not ordered:
        return []

    groups: list[list[float]] = [[ordered[0]]]
    for value in ordered[1:]:
        if abs(value - (sum(groups[-1]) / len(groups[-1]))) <= tolerance:
            groups[-1].append(value)
        else:
            groups.append([value])
    return [sum(group) / len(group) for group in groups]


def infer_piece_from_blob(
    component: list[tuple[int, int]],
    left: int,
    top: int,
    scale_x: float,
    scale_y: float,
    capture_region: Rect,
    piece_est: float,
    slot_index: int,
) -> Piece | None:
    block_points = infer_block_points_from_blob(component, left, top, scale_x, scale_y, capture_region, piece_est)
    if not block_points:
        return None
    return build_piece_from_detected_points(block_points, piece_est, scale_x, scale_y, slot_index)


def infer_block_points_from_blob(
    component: list[tuple[int, int]],
    left: int,
    top: int,
    scale_x: float,
    scale_y: float,
    capture_region: Rect,
    piece_est: float,
) -> list[Point]:
    xs = [point[0] for point in component]
    ys = [point[1] for point in component]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = (max_x - min_x) + 1
    height = (max_y - min_y) + 1

    mask = np.zeros((height, width), dtype=bool)
    for x, y in component:
        mask[y - min_y, x - min_x] = True

    est_cell_w = max(piece_est * scale_x, 1.0)
    est_cell_h = max(piece_est * scale_y, 1.0)
    width_ratio = width / est_cell_w
    height_ratio = height / est_cell_h
    cols_guess = max(1, min(5, int(round(width_ratio))))
    rows_guess = max(1, min(5, int(round(height_ratio))))
    area_ratio = len(component) / max(est_cell_w * est_cell_h, 1.0)
    expected_cells = max(1, min(9, int(round(area_ratio))))
    if min(width_ratio, height_ratio) <= 1.35 and max(width_ratio, height_ratio) >= 2.4:
        expected_cells = max(expected_cells, min(9, int(math.ceil(max(width_ratio, height_ratio) - 0.12))))
    if width_ratio >= 1.35 and height_ratio >= 1.55:
        expected_cells = max(expected_cells, 2)
    if width_ratio >= 1.35 and height_ratio >= 1.78:
        expected_cells = max(expected_cells, 3)
    if (width_ratio * height_ratio) >= 2.25:
        expected_cells = max(expected_cells, 2)

    candidate_dims: list[tuple[int, int]] = []
    for rows in range(1, 6):
        for cols in range(1, 6):
            if abs(rows - rows_guess) > 2 and abs(cols - cols_guess) > 2:
                continue
            if (rows, cols) not in candidate_dims:
                candidate_dims.append((rows, cols))

    occupancy_threshold = max(0.34, min(0.62, float(mask.mean()) * 0.78))
    if max(width_ratio, height_ratio) >= 1.45 or area_ratio >= 1.15:
        occupancy_threshold = max(0.30, occupancy_threshold - 0.10)
    best_score = -1e9
    best_points: list[Point] = []
    best_size_delta = 999

    for rows, cols in candidate_dims:
        cell_w = width / cols
        cell_h = height / rows
        occupied_points: list[Point] = []
        occupied_cells: list[tuple[int, int]] = []
        occupied_means: list[float] = []
        empty_means: list[float] = []

        for row in range(rows):
            for col in range(cols):
                x0 = int(round(col * cell_w))
                x1 = int(round((col + 1) * cell_w))
                y0 = int(round(row * cell_h))
                y1 = int(round((row + 1) * cell_h))
                patch = mask[y0:y1, x0:x1]
                if patch.size == 0:
                    continue
                mean_value = float(patch.mean())
                if mean_value >= occupancy_threshold:
                    occupied_cells.append((col, row))
                    occupied_means.append(mean_value)
                    center_x = min_x + ((x0 + x1) / 2.0)
                    center_y = min_y + ((y0 + y1) / 2.0)
                    occupied_points.append(
                        Point(
                            x=(left + center_x) / scale_x + capture_region.left,
                            y=(top + center_y) / scale_y + capture_region.top,
                        )
                    )
                else:
                    empty_means.append(mean_value)

        if not occupied_cells or len(occupied_cells) > 9:
            continue
        if not piece_is_connected(occupied_cells):
            continue

        size_delta = abs(cols - cols_guess) + abs(rows - rows_guess)
        count_delta = abs(len(occupied_cells) - expected_cells)
        occupied_score = sum(occupied_means) / len(occupied_means)
        empty_score = (sum(empty_means) / len(empty_means)) if empty_means else 0.0
        square_penalty = abs((cell_w / max(cell_h, 1.0)) - 1.0)
        aspect_target = width / max(height, 1.0)
        aspect_penalty = abs((cols / max(rows, 1.0)) - aspect_target)
        fill_target = len(component) / max((rows * cols * cell_w * cell_h), 1.0)
        occupancy_ratio = len(occupied_cells) / max(rows * cols, 1)
        fill_penalty = abs(occupancy_ratio - fill_target)
        shape_score = (
            occupied_score
            - (empty_score * 0.85)
            - (0.10 * size_delta)
            - (0.28 * count_delta)
            - (0.60 * square_penalty)
            - (0.18 * aspect_penalty)
            - (0.20 * fill_penalty)
        )

        if shape_score > best_score or (math.isclose(shape_score, best_score) and size_delta < best_size_delta):
            best_score = shape_score
            best_size_delta = size_delta
            best_points = occupied_points

    return best_points


def piece_is_connected(cells: Sequence[tuple[int, int]]) -> bool:
    if not cells:
        return False
    cell_set = set(cells)
    queue = deque([next(iter(cell_set))])
    seen = {queue[0]}
    while queue:
        col, row = queue.popleft()
        for next_col, next_row in ((col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)):
            if (next_col, next_row) in cell_set and (next_col, next_row) not in seen:
                seen.add((next_col, next_row))
                queue.append((next_col, next_row))
    return len(seen) == len(cell_set)


def piece_is_plausible(piece: Piece | None) -> bool:
    if piece is None:
        return False
    if piece.size < 1 or piece.size > 9:
        return False
    if piece.width < 1 or piece.height < 1 or piece.width > 5 or piece.height > 5:
        return False
    return piece_is_connected(piece.cells)


def build_piece_from_detected_points(
    global_centers: Sequence[Point],
    piece_est: float,
    scale_x: float,
    scale_y: float,
    slot_index: int,
) -> Piece | None:
    if not global_centers:
        return None
    local_centers = [(point.x * scale_x, point.y * scale_y) for point in global_centers]
    clustered_x = cluster_axis((value[0] for value in local_centers), (piece_est * scale_x) * 0.42)
    clustered_y = cluster_axis((value[1] for value in local_centers), (piece_est * scale_y) * 0.42)

    cells_with_points: list[tuple[tuple[int, int], Point]] = []
    for (x, y), global_point in zip(local_centers, global_centers):
        col = min(range(len(clustered_x)), key=lambda idx: abs(clustered_x[idx] - x))
        row = min(range(len(clustered_y)), key=lambda idx: abs(clustered_y[idx] - y))
        cells_with_points.append(((col, row), global_point))

    min_col = min(col for (col, _), _ in cells_with_points)
    min_row = min(row for (_, row), _ in cells_with_points)
    normalized_points = [
        ((col - min_col, row - min_row), point)
        for (col, row), point in cells_with_points
    ]
    normalized = tuple(sorted({cell for cell, _ in normalized_points}))
    source_centroid = Point(
        sum(point.x for point in global_centers) / len(global_centers),
        sum(point.y for point in global_centers) / len(global_centers),
    )
    grab_cell, source_grab_point = min(
        normalized_points,
        key=lambda item: (
            abs(item[1].x - source_centroid.x) + abs(item[1].y - source_centroid.y),
            item[0][1],
            item[0][0],
        ),
    )
    return Piece(
        cells=normalized,
        source_centroid=source_centroid,
        source_grab_point=source_grab_point,
        grab_cell=grab_cell,
        slot_index=slot_index,
    )


def piece_foreground_mask(crop_rgb: np.ndarray) -> np.ndarray:
    crop_hsv = np.array(Image.fromarray(crop_rgb).convert("HSV"))
    hue = crop_hsv[:, :, 0]
    sat = crop_hsv[:, :, 1]
    val = crop_hsv[:, :, 2]
    rgb = crop_rgb.astype(np.int16)
    blurred = np.array(Image.fromarray(crop_rgb).filter(ImageFilter.GaussianBlur(radius=3))).astype(np.int16)
    delta = np.abs(rgb - blurred)
    delta_max = delta.max(axis=2)
    channel_range = (rgb.max(axis=2) - rgb.min(axis=2)).astype(np.int16)

    dominant_hue = int(np.median(hue))
    hue_delta = np.abs(hue.astype(np.int16) - dominant_hue)
    hue_delta = np.minimum(hue_delta, 255 - hue_delta)

    non_tray_hue = hue_delta >= 12
    vivid_blocks = non_tray_hue & (sat >= 50) & (val >= 88) & (channel_range >= 16)
    bright_blocks = non_tray_hue & (val >= 150) & (channel_range >= 12)
    icon_blocks = non_tray_hue & (sat >= 42) & (val >= 96) & (channel_range >= 12)

    mask = ((vivid_blocks | bright_blocks | icon_blocks) & (delta_max >= 10))
    mask |= icon_blocks & (val >= 88)
    mask[:, :2] = False
    mask[:, -2:] = False

    # Ignore only the deepest tray lip area near the bottom of the slot crop.
    # Keeping more of the lower slot is important for tall 1x4 / 1x5 bars,
    # which otherwise get clipped into shorter pieces.
    cutoff = int(mask.shape[0] * 0.94)
    mask[cutoff:, :] = False

    # Remove oversized low-detail bowl regions; real pieces break into block-sized blobs.
    components = connected_components(mask)
    for component in components:
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        width = (max(xs) - min(xs)) + 1
        height = (max(ys) - min(ys)) + 1
        fill_ratio = len(component) / max(width * height, 1)
        if width >= (crop_rgb.shape[1] * 0.62) and height >= (crop_rgb.shape[0] * 0.45) and fill_ratio < 0.55:
            for x, y in component:
                mask[y, x] = False
    return mask


def slot_crop_boxes(image: Image.Image, config: dict) -> list[tuple[int, int, int, int]]:
    capture_region = rect_from_dict(config["capture_region"])
    board_rect = rect_from_dict(config["board_rect"])
    slot_centers = [point_from_dict(item) for item in config["piece_slot_centers"]]
    tray_rect_data = config.get("tray_rect")
    tuning = config.get("tuning", {})
    slot_crop_scale = (
        float(tuning.get("slot_crop_width_scale", 8.0)),
        float(tuning.get("slot_crop_height_scale", 5.5)),
    )
    piece_block_scale = float(tuning.get("piece_block_scale", 0.35))

    board_cell = board_rect.width / BOARD_SIZE
    piece_est = board_cell * piece_block_scale
    base_crop_w = int(round(piece_est * slot_crop_scale[0]))
    crop_h = int(round(piece_est * slot_crop_scale[1]))
    scale_x, scale_y = capture_scale(image, capture_region)

    boxes: list[tuple[int, int, int, int]] = []
    if tray_rect_data:
        tray_rect = rect_from_dict(tray_rect_data)
        # The bowl edges are visually stable, but the darker inner bounds can
        # drift badly on screenshots with surrounding UI or reflections. Use a
        # fixed inset of the detected tray rect instead of re-detecting the
        # inner horizontal span.
        inner_left = tray_rect.left + (tray_rect.width * 0.075)
        inner_right = tray_rect.right - (tray_rect.width * 0.075)
        inner_top = tray_rect.top + (tray_rect.height * 0.03)
        # Leave much more of the lower tray visible so long vertical pieces
        # in the bottom tray are not clipped before masking.
        inner_bottom = tray_rect.bottom - (tray_rect.height * 0.06)
        section_width = (inner_right - inner_left) / 3.0
        overlap_x = section_width * 0.08
        for slot_index in range(3):
            left = inner_left + (section_width * slot_index) - (overlap_x if slot_index > 0 else 0.0)
            right = inner_left + (section_width * (slot_index + 1)) + (overlap_x if slot_index < 2 else 0.0)
            boxes.append(
                (
                    int(round((left - capture_region.left) * scale_x)),
                    int(round((inner_top - capture_region.top) * scale_y)),
                    int(round((right - capture_region.left) * scale_x)),
                    int(round((inner_bottom - capture_region.top) * scale_y)),
                )
            )
        return boxes

    for slot_index, slot_center in enumerate(slot_centers):
        rel_center = Point(slot_center.x - capture_region.left, slot_center.y - capture_region.top)
        if slot_index > 0:
            prev_center = slot_centers[slot_index - 1]
            left_bound = ((prev_center.x + slot_center.x) / 2.0) - capture_region.left
        else:
            left_bound = rel_center.x - (base_crop_w / 2.0)

        if slot_index < (len(slot_centers) - 1):
            next_center = slot_centers[slot_index + 1]
            right_bound = ((slot_center.x + next_center.x) / 2.0) - capture_region.left
        else:
            right_bound = rel_center.x + (base_crop_w / 2.0)

        left = int(round(left_bound * scale_x))
        crop_w = int(round((right_bound - left_bound) * scale_x))
        top = int(round((rel_center.y - (crop_h / 2)) * scale_y))
        crop_h_pixels = int(round(crop_h * scale_y))
        boxes.append((left, top, left + crop_w, top + crop_h_pixels))
    return boxes


def detect_piece(
    image: Image.Image,
    capture_region: Rect,
    board_rect: Rect,
    slot_center: Point,
    slot_centers: Sequence[Point],
    slot_index: int,
    slot_crop_scale: tuple[float, float],
    piece_block_scale: float,
    slot_box: tuple[int, int, int, int] | None = None,
) -> Piece | None:
    board_cell = playable_board_rect(board_rect).width / BOARD_SIZE
    piece_est = board_cell * piece_block_scale
    scale_x, scale_y = capture_scale(image, capture_region)
    if slot_box is None:
        left, top, right, bottom = slot_crop_boxes(image, {
            "capture_region": rect_to_dict(capture_region),
            "board_rect": rect_to_dict(board_rect),
            "piece_slot_centers": [point_to_dict(point) for point in slot_centers],
            "tuning": {
                "slot_crop_width_scale": slot_crop_scale[0],
                "slot_crop_height_scale": slot_crop_scale[1],
                "piece_block_scale": piece_block_scale,
            },
        })[slot_index]
    else:
        left, top, right, bottom = slot_box
    crop_w = right - left
    crop_h_pixels = bottom - top
    crop_rgb = np.array(image.crop((left, top, left + crop_w, top + crop_h_pixels)).convert("RGB"))
    scaled_piece_width = piece_est * scale_x
    scaled_piece_height = piece_est * scale_y
    mask = piece_foreground_mask(crop_rgb)
    components = connected_components(mask)
    components = merge_nearby_components(
        components,
        x_gap_limit=scaled_piece_width * 0.85,
        y_gap_limit=scaled_piece_height * 0.85,
    )

    block_points: list[Point] = []
    border_margin = max(2, int(round(min(crop_w, crop_h_pixels) * 0.03)))
    for component in components:
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        width = (max(xs) - min(xs)) + 1
        height = (max(ys) - min(ys)) + 1
        fill_ratio = len(component) / max(width * height, 1)
        min_area = max(140.0, (scaled_piece_width * scaled_piece_height) * 0.35)
        if len(component) < min_area:
            continue
        if min(ys) >= crop_h_pixels * 0.82:
            continue
        touches_left = min(xs) <= border_margin
        touches_right = max(xs) >= (crop_w - border_margin - 1)
        touches_top = min(ys) <= border_margin
        touches_bottom = max(ys) >= (crop_h_pixels - border_margin - 1)
        if (
            touches_top
            and (touches_left or touches_right)
            and width >= scaled_piece_width * 1.45
            and height <= scaled_piece_height * 1.4
            and fill_ratio <= 0.62
        ):
            continue
        if (
            touches_bottom
            and (touches_left or touches_right)
            and height <= scaled_piece_height * 0.95
            and width >= scaled_piece_width * 0.75
            and fill_ratio <= 0.7
        ):
            continue
        if (touches_left and touches_right) or (touches_bottom and min(ys) > crop_h_pixels * 0.52):
            continue
        if (touches_left or touches_right) and width > scaled_piece_width * 2.65 and fill_ratio < 0.82:
            continue
        if touches_top and height < scaled_piece_height * 0.55 and width > scaled_piece_width * 1.3:
            continue
        if fill_ratio < 0.25 and max(width, height) >= min(crop_w, crop_h_pixels) * 0.45:
            continue

        if (
            (scaled_piece_width * 0.55) <= width <= (scaled_piece_width * 1.55)
            and (scaled_piece_height * 0.55) <= height <= (scaled_piece_height * 1.55)
        ):
            center_x = (min(xs) + max(xs)) / 2.0
            center_y = (min(ys) + max(ys)) / 2.0
            block_points.append(
                Point(
                    x=(left + center_x) / scale_x + capture_region.left,
                    y=(top + center_y) / scale_y + capture_region.top,
                )
            )
            continue

        if (
            width <= crop_w * 0.8
            and height <= crop_h_pixels * 0.8
            and max(width, height) >= min(scaled_piece_width * 1.4, scaled_piece_height * 1.4)
            and fill_ratio >= 0.28
        ):
            block_points.extend(
                infer_block_points_from_blob(component, left, top, scale_x, scale_y, capture_region, piece_est)
            )

    if not block_points:
        return None

    deduped_points: list[Point] = []
    merge_tolerance_x = (piece_est / 2.2)
    merge_tolerance_y = (piece_est / 2.2)
    for point in block_points:
        if any(abs(point.x - other.x) <= merge_tolerance_x and abs(point.y - other.y) <= merge_tolerance_y for other in deduped_points):
            continue
        deduped_points.append(point)

    piece = build_piece_from_detected_points(deduped_points, piece_est, scale_x, scale_y, slot_index)
    if piece_is_plausible(piece):
        return piece
    if components:
        best_blob = max(
            components,
            key=lambda component: (
                len(component) / max(
                    (((max(point[0] for point in component) - min(point[0] for point in component)) + 1)
                    * ((max(point[1] for point in component) - min(point[1] for point in component)) + 1)),
                    1,
                ),
                len(component),
            ),
        )
        inferred_piece = infer_piece_from_blob(best_blob, left, top, scale_x, scale_y, capture_region, piece_est, slot_index)
        if piece_is_plausible(inferred_piece):
            return inferred_piece
    return None


def detect_pieces(image: Image.Image, config: dict) -> list[Piece]:
    capture_region = rect_from_dict(config["capture_region"])
    board_rect = rect_from_dict(config["board_rect"])
    slot_centers = [point_from_dict(item) for item in config["piece_slot_centers"]]
    slot_boxes = slot_crop_boxes(image, config)

    tuning = config.get("tuning", {})
    slot_crop_scale = (
        float(tuning.get("slot_crop_width_scale", 8.0)),
        float(tuning.get("slot_crop_height_scale", 5.5)),
    )
    piece_block_scale = float(tuning.get("piece_block_scale", 0.35))

    detected: list[Piece] = []
    for index, center in enumerate(slot_centers):
        piece = detect_piece(
            image=image,
            capture_region=capture_region,
            board_rect=board_rect,
            slot_center=center,
            slot_centers=slot_centers,
            slot_index=index,
            slot_crop_scale=slot_crop_scale,
            piece_block_scale=piece_block_scale,
            slot_box=slot_boxes[index],
        )
        if piece is not None:
            detected.append(piece)
    return detected


def placement_centroid(board_rect: Rect, anchor_col: int, anchor_row: int, piece: Piece) -> Point:
    centers = board_cell_centers(board_rect)
    targets = [centers[anchor_row + y][anchor_col + x] for x, y in piece.cells]
    return Point(
        sum(point.x for point in targets) / len(targets),
        sum(point.y for point in targets) / len(targets),
    )


def placement_grab_point(board_rect: Rect, anchor_col: int, anchor_row: int, piece: Piece) -> Point:
    centers = board_cell_centers(board_rect)
    grab_x, grab_y = piece.grab_cell
    return centers[anchor_row + grab_y][anchor_col + grab_x]


def clone_board(board: Sequence[Sequence[bool]]) -> list[list[bool]]:
    return [list(row) for row in board]


def apply_piece(board: Sequence[Sequence[bool]], piece: Piece, anchor_col: int, anchor_row: int) -> tuple[list[list[bool]], int]:
    next_board = clone_board(board)
    for x, y in piece.cells:
        next_board[anchor_row + y][anchor_col + x] = True

    full_rows = [row for row in range(BOARD_SIZE) if all(next_board[row][col] for col in range(BOARD_SIZE))]
    full_cols = [col for col in range(BOARD_SIZE) if all(next_board[row][col] for row in range(BOARD_SIZE))]

    for row in full_rows:
        for col in range(BOARD_SIZE):
            next_board[row][col] = False
    for col in full_cols:
        for row in range(BOARD_SIZE):
            next_board[row][col] = False

    return next_board, len(full_rows) + len(full_cols)


def legal_placements(board: Sequence[Sequence[bool]], piece: Piece) -> list[tuple[int, int]]:
    placements = []
    for row in range(BOARD_SIZE - piece.height + 1):
        for col in range(BOARD_SIZE - piece.width + 1):
            if all(not board[row + y][col + x] for x, y in piece.cells):
                placements.append((col, row))
    return placements


def ranked_placements(board: Sequence[Sequence[bool]], piece: Piece, limit: int = MAX_SEARCH_PLACEMENTS_PER_PIECE) -> list[tuple[int, int]]:
    placements = legal_placements(board, piece)
    if len(placements) <= limit:
        return placements

    scored: list[tuple[tuple[int, int, int, int], tuple[int, int]]] = []
    for col, row in placements:
        next_board, cleared = apply_piece(board, piece, col, row)
        empty_cells = sum(not value for next_row in next_board for value in next_row)
        scored.append(
            (
                (
                    cleared,
                    count_empty_windows(next_board, 3),
                    count_empty_windows(next_board, 2),
                    empty_cells,
                ),
                (col, row),
            )
        )
    scored.sort(reverse=True)
    return [placement for _, placement in scored[:limit]]


def count_empty_windows(board: Sequence[Sequence[bool]], window: int) -> int:
    total = 0
    for row in range(BOARD_SIZE - window + 1):
        for col in range(BOARD_SIZE - window + 1):
            if all(not board[row + dy][col + dx] for dy in range(window) for dx in range(window)):
                total += 1
    return total


def empty_fragmentation(board: Sequence[Sequence[bool]]) -> int:
    seen: set[tuple[int, int]] = set()
    components = 0
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col] or (row, col) in seen:
                continue
            components += 1
            queue = deque([(row, col)])
            seen.add((row, col))
            while queue:
                y, x = queue.popleft()
                for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= ny < BOARD_SIZE and 0 <= nx < BOARD_SIZE and not board[ny][nx] and (ny, nx) not in seen:
                        seen.add((ny, nx))
                        queue.append((ny, nx))
    return components


def score_board(board: Sequence[Sequence[bool]], placed_count: int, cleared_lines: int) -> tuple[int, int, int, int, int, int]:
    empty_cells = sum(not value for row in board for value in row)
    return (
        placed_count,
        cleared_lines,
        count_empty_windows(board, 3),
        count_empty_windows(board, 2),
        empty_cells,
        -empty_fragmentation(board),
    )


def board_from_signature(board_signature: tuple[tuple[bool, ...], ...]) -> list[list[bool]]:
    return [list(row) for row in board_signature]


def search_best_sequence(
    board: Sequence[Sequence[bool]],
    pieces: Sequence[Piece],
    board_rect: Rect,
) -> SearchResult:
    @lru_cache(maxsize=None)
    def heuristic_score(board_signature: tuple[tuple[bool, ...], ...]) -> tuple[int, int, int, int]:
        current_board = board_from_signature(board_signature)
        empty_cells = sum(not value for row in current_board for value in row)
        return (
            count_empty_windows(current_board, 3),
            count_empty_windows(current_board, 2),
            empty_cells,
            -empty_fragmentation(current_board),
        )

    @lru_cache(maxsize=None)
    def walk(
        board_signature: tuple[tuple[bool, ...], ...],
        remaining: tuple[int, ...],
    ) -> tuple[tuple[int, int, int, int, int, int], tuple[tuple[int, int, int, int], ...]]:
        current_board = board_from_signature(board_signature)
        best_score = (0, 0, *heuristic_score(board_signature))
        best_plan: tuple[tuple[int, int, int, int], ...] = ()

        for piece_index in remaining:
            piece = pieces[piece_index]
            next_remaining = tuple(index for index in remaining if index != piece_index)
            for anchor_col, anchor_row in ranked_placements(current_board, piece):
                next_board, cleared_now = apply_piece(current_board, piece, anchor_col, anchor_row)
                child_score, child_plan = walk(board_to_tuple(next_board), next_remaining)
                candidate_score = (
                    1 + child_score[0],
                    cleared_now + child_score[1],
                    child_score[2],
                    child_score[3],
                    child_score[4],
                    child_score[5],
                )
                if candidate_score > best_score:
                    best_score = candidate_score
                    best_plan = ((piece_index, anchor_col, anchor_row, cleared_now),) + child_plan
        return best_score, best_plan

    best_score, best_plan = walk(board_to_tuple(board), tuple(range(len(pieces))))
    moves = tuple(
        Move(
            piece_index=piece_index,
            slot_index=pieces[piece_index].slot_index,
            anchor_col=anchor_col,
            anchor_row=anchor_row,
            cleared_lines=cleared_now,
            target_centroid=placement_centroid(board_rect, anchor_col, anchor_row, pieces[piece_index]),
            target_grab_point=placement_grab_point(board_rect, anchor_col, anchor_row, pieces[piece_index]),
        )
        for piece_index, anchor_col, anchor_row, cleared_now in best_plan
    )
    return SearchResult(score=best_score, moves=moves, placed_count=best_score[0])


def search_best_live_move(
    board: Sequence[Sequence[bool]],
    pieces: Sequence[Piece],
    board_rect: Rect,
) -> SearchResult:
    best_move: Move | None = None
    best_score: tuple[int, int, int, int, int, int] = (0, 0, 0, 0, 0, -999)

    for piece_index, piece in enumerate(pieces):
        for anchor_col, anchor_row in ranked_placements(board, piece, limit=MAX_LIVE_PLACEMENTS_PER_PIECE):
            next_board, cleared_now = apply_piece(board, piece, anchor_col, anchor_row)
            candidate_score = score_board(next_board, 1, cleared_now)
            if candidate_score <= best_score:
                continue
            best_score = candidate_score
            best_move = Move(
                piece_index=piece_index,
                slot_index=piece.slot_index,
                anchor_col=anchor_col,
                anchor_row=anchor_row,
                cleared_lines=cleared_now,
                target_centroid=placement_centroid(board_rect, anchor_col, anchor_row, piece),
                target_grab_point=placement_grab_point(board_rect, anchor_col, anchor_row, piece),
            )

    moves = (best_move,) if best_move is not None else ()
    return SearchResult(score=best_score, moves=moves, placed_count=1 if best_move is not None else 0)


def render_debug(
    image: Image.Image,
    capture_region: Rect,
    board_rect: Rect,
    board: Sequence[Sequence[bool]],
    pieces: Sequence[Piece],
    result: SearchResult,
    output_path: Path,
) -> None:
    draw = ImageDraw.Draw(image)
    scale_x, scale_y = capture_scale(image, capture_region)
    move_colors = ("yellow", "orange", "deepskyblue", "magenta", "lime")

    board_rel = Rect(
        left=(board_rect.left - capture_region.left) * scale_x,
        top=(board_rect.top - capture_region.top) * scale_y,
        right=(board_rect.right - capture_region.left) * scale_x,
        bottom=(board_rect.bottom - capture_region.top) * scale_y,
    )
    draw.rectangle([board_rel.left, board_rel.top, board_rel.right, board_rel.bottom], outline="cyan", width=3)

    cell_w = board_rel.width / BOARD_SIZE
    cell_h = board_rel.height / BOARD_SIZE
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if board[row][col]:
                x0 = board_rel.left + (col * cell_w)
                y0 = board_rel.top + (row * cell_h)
                x1 = x0 + cell_w
                y1 = y0 + cell_h
                draw.rectangle([x0, y0, x1, y1], outline="red", width=2)

    for piece in pieces:
        rel = Point(
            (piece.source_grab_point.x - capture_region.left) * scale_x,
            (piece.source_grab_point.y - capture_region.top) * scale_y,
        )
        radius = 10
        draw.ellipse([rel.x - radius, rel.y - radius, rel.x + radius, rel.y + radius], outline="lime", width=3)
        draw.text((rel.x + 12, rel.y - 8), f"S{piece.slot_index + 1}", fill="lime")

    for index, move in enumerate(result.moves, start=1):
        rel = Point(
            (move.target_grab_point.x - capture_region.left) * scale_x,
            (move.target_grab_point.y - capture_region.top) * scale_y,
        )
        color = move_colors[(index - 1) % len(move_colors)]
        radius = 12
        draw.ellipse([rel.x - radius, rel.y - radius, rel.x + radius, rel.y + radius], outline=color, width=3)
        draw.text((rel.x + 14, rel.y - 10), f"{index}", fill=color)

        piece = pieces[move.piece_index]
        for cell_row, cell_col in move_cells(move, piece):
            x0 = board_rel.left + (cell_col * cell_w)
            y0 = board_rel.top + (cell_row * cell_h)
            x1 = x0 + cell_w
            y1 = y0 + cell_h
            draw.rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], outline=color, width=3)

        label_row, label_col = move_cells(move, piece)[0]
        text_x = board_rel.left + (label_col * cell_w) + 4
        text_y = board_rel.top + (label_row * cell_h) + 2
        draw.text((text_x, text_y), str(index), fill=color)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def board_to_text(board: Sequence[Sequence[bool]]) -> str:
    return "\n".join("".join("[]" if value else ".." for value in row) for row in board)


def board_to_coordinate_text(
    board: Sequence[Sequence[bool]],
    overlay_cells: dict[tuple[int, int], str] | None = None,
) -> str:
    overlay_cells = overlay_cells or {}
    lines = ["    " + " ".join(str(index) for index in range(1, BOARD_SIZE + 1))]
    for row in range(BOARD_SIZE):
        tokens = []
        for col in range(BOARD_SIZE):
            label = overlay_cells.get((row, col))
            if label is not None:
                tokens.append(label)
            elif board[row][col]:
                tokens.append("#")
            else:
                tokens.append(".")
        lines.append(f"R{row + 1}  " + " ".join(tokens))
    return "\n".join(lines)


def move_cells(move: Move, piece: Piece) -> list[tuple[int, int]]:
    return sorted((move.anchor_row + y, move.anchor_col + x) for x, y in piece.cells)


def piece_to_text(cells: Sequence[tuple[int, int]]) -> str:
    if not cells:
        return "(empty)"
    width = max(x for x, _ in cells) + 1
    height = max(y for _, y in cells) + 1
    cell_set = set(cells)
    lines = []
    for row in range(height):
        tokens = []
        for col in range(width):
            tokens.append("#" if (col, row) in cell_set else ".")
        lines.append(" ".join(tokens))
    return "\n".join(lines)


def board_to_text_with_overlay(
    board: Sequence[Sequence[bool]],
    overlay_cells: dict[tuple[int, int], str] | None = None,
) -> str:
    overlay_cells = overlay_cells or {}
    lines = []
    for row in range(BOARD_SIZE):
        tokens = []
        for col in range(BOARD_SIZE):
            label = overlay_cells.get((row, col))
            if label is not None:
                tokens.append(f"{label}{label}")
            elif board[row][col]:
                tokens.append("[]")
            else:
                tokens.append("..")
        lines.append("".join(tokens))
    return "\n".join(lines)


def placement_footprint_text(move: Move, piece: Piece) -> str:
    width = piece.width
    height = piece.height
    cell_set = set(piece.cells)
    lines = []
    for row in range(height):
        tokens = []
        for col in range(width):
            if (col, row) not in cell_set:
                tokens.append(".....")
                continue
            board_row = move.anchor_row + row + 1
            board_col = move.anchor_col + col + 1
            tokens.append(f"R{board_row}C{board_col}")
        lines.append(" ".join(tokens))
    return "\n".join(lines)


def format_move_summary(move: Move, piece: Piece, *, step_index: int | None = None) -> str:
    cells = ", ".join(f"R{row + 1}C{col + 1}" for row, col in move_cells(move, piece))
    prefix = f"{step_index}. " if step_index is not None else ""
    return (
        f"{prefix}Slot {move.slot_index + 1} -> R{move.anchor_row + 1}C{move.anchor_col + 1} "
        f"| clears {move.cleared_lines} | cells: {cells}"
    )


def assist_text(
    board: Sequence[Sequence[bool]],
    pieces: Sequence[Piece],
    result: SearchResult,
    config: dict | None = None,
) -> str:
    lines = ["Assist mode"]
    if config is not None:
        lines.append(f"Source: {describe_capture_source(config)}")
        if not config.get("auto_window"):
            lines.append("Note: this is using the saved capture region, not a live iPhone Mirroring window.")
    lines.append(f"Visible tray pieces: {len(pieces)}")
    if result.moves:
        first_move = result.moves[0]
        first_piece = pieces[first_move.piece_index]
        overlay = {cell: "A" for cell in move_cells(first_move, first_piece)}
        lines.extend(
            [
                "",
                "Play now:",
                format_move_summary(first_move, first_piece),
                "Piece:",
                piece_to_text(first_piece.cells),
                "Exact footprint:",
                placement_footprint_text(first_move, first_piece),
                "Board guide (# filled, . empty, A place now):",
                board_to_coordinate_text(board, overlay),
            ]
        )
    else:
        lines.extend(["", "Current board:", board_to_coordinate_text(board)])

    if not pieces:
        lines.append("No visible tray pieces detected.")
        lines.append("This usually means the bottom tray is hidden, mid-animation, or the wrong capture is being read.")
        return "\n".join(lines)

    lines.extend(["", "Tray pieces:"])
    for piece in sorted(pieces, key=lambda item: item.slot_index):
        lines.append(f"Slot {piece.slot_index + 1} ({piece.size} cells): {piece.cells}")
        lines.append(piece_to_text(piece.cells))

    if not result.moves:
        lines.append("")
        lines.append("No legal placements found for the detected pieces.")
        return "\n".join(lines)

    lines.extend(["", "Sequence:"])
    for step_index, move in enumerate(result.moves, start=1):
        piece = pieces[move.piece_index]
        lines.append(format_move_summary(move, piece, step_index=step_index))
    return "\n".join(lines)


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")


def save_slot_crops(image: Image.Image, config: dict, output_dir: Path, stem_prefix: str) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for slot_index, (left, top, right, bottom) in enumerate(slot_crop_boxes(image, config)):
        crop = image.crop((left, top, right, bottom))
        path = output_dir / f"{stem_prefix}_slot_{slot_index + 1}.png"
        crop.save(path)
        paths.append(path)
    return paths


def persist_drop_behavior(config_path: Path, offset: Point, strategy: str) -> None:
    if not config_path.exists():
        return
    payload = load_config(config_path)
    tuning = dict(payload.get("tuning", {}))
    tuning["drop_offset_x"] = round(offset.x, 2)
    tuning["drop_offset_y"] = round(offset.y, 2)
    tuning["drag_strategy"] = strategy
    payload["tuning"] = tuning
    save_config(config_path, payload)


def print_saved_assist_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(
            f"No saved assist guide found at {path}.\n"
            "Run this first:\n"
            "  ./.venv/bin/python scripts/block_blast_bot.py --assist"
        )
    print(path.read_text(encoding="utf-8"), end="")


def describe_moves(result: SearchResult, pieces: Sequence[Piece]) -> str:
    if not result.moves:
        if not pieces:
            return "No visible pieces detected in the tray."
        return "No legal placements found for the detected pieces."

    lines = []
    for index, move in enumerate(result.moves, start=1):
        piece = pieces[move.piece_index]
        lines.append(
            f"{index}. Use slot {move.slot_index + 1} piece {piece.cells} at "
            f"row {move.anchor_row + 1}, col {move.anchor_col + 1}"
            f" (clears {move.cleared_lines} lines)"
        )
    return "\n".join(lines)


def analyze(
    image: Image.Image,
    config: dict,
    *,
    fast_search: bool = False,
) -> tuple[list[list[bool]], list[Piece], SearchResult]:
    capture_region = rect_from_dict(config["capture_region"])
    board_rect = rect_from_dict(config["board_rect"])
    empty_threshold = float(config.get("tuning", {}).get("empty_cell_threshold", 28.0))

    board = detect_board(image, board_rect, capture_region, empty_threshold)
    pieces = detect_pieces(image, config)
    if fast_search:
        result = search_best_live_move(board, pieces, board_rect)
    else:
        result = search_best_sequence(board, pieces, board_rect)
    return board, pieces, result


def countdown(seconds: int) -> None:
    for value in range(seconds, 0, -1):
        print(f"Starting in {value}...")
        time.sleep(1)


def add_points(a: Point, b: Point) -> Point:
    return Point(a.x + b.x, a.y + b.y)


def subtract_points(a: Point, b: Point) -> Point:
    return Point(a.x - b.x, a.y - b.y)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def clamp_drop_target(point: Point, board_rect: Rect, cell_w: float, cell_h: float) -> Point:
    margin_x = cell_w * 0.34
    margin_y = cell_h * 0.34
    return Point(
        x=clamp(point.x, board_rect.left + margin_x, board_rect.right - margin_x),
        y=clamp(point.y, board_rect.top + margin_y, board_rect.bottom - margin_y),
    )


def unique_points(points: Iterable[Point], tolerance: float = 1.0) -> list[Point]:
    unique: list[Point] = []
    for point in points:
        if any(abs(point.x - item.x) <= tolerance and abs(point.y - item.y) <= tolerance for item in unique):
            continue
        unique.append(point)
    return unique


def candidate_drop_offsets(current_offset: Point, cell_w: float, cell_h: float) -> list[Point]:
    has_learned_offset = abs(current_offset.x) > 0.5 or abs(current_offset.y) > 0.5
    fractions = (0.0, 0.18, 0.35, 0.55, 0.8, 1.05) if has_learned_offset else (0.0, 0.18, 0.35, 0.55, 0.8, 1.05, 1.3, 1.55)
    scale_pairs: list[tuple[float, float]] = [
        (0.0, 0.0),
        (0.0, 0.18),
        (0.0, 0.35),
        (0.0, 0.55),
        (0.0, 0.8),
        (0.0, 1.05),
        (0.12, 0.35),
        (-0.12, 0.35),
        (0.18, 0.55),
        (-0.18, 0.55),
        (0.0, -0.18),
        (0.0, -0.35),
    ]
    for radius in fractions[1:]:
        ring: list[tuple[float, float]] = []
        for dx in (-radius, 0.0, radius):
            for dy in (-radius, 0.0, radius):
                if dx == 0.0 and dy == 0.0:
                    continue
                ring.append((dx, dy))
        for dx in (-radius, radius):
            for dy in (-0.18, 0.18, -0.35, 0.35, -0.55, 0.55):
                ring.append((dx, dy))
                ring.append((dy, dx))
        ring = sorted(
            ring,
            key=lambda item: (
                item[1] < 0.0,
                abs(item[0]) + abs(item[1]),
                abs(item[0]),
                abs(item[1]),
            ),
        )
        scale_pairs.extend(ring)
    return unique_points(
        Point(current_offset.x + (dx * cell_w), current_offset.y + (dy * cell_h))
        for dx, dy in scale_pairs
    )[:57]


def drag_plan_points(piece: Piece, move: Move, slot_center: Point, strategy: str) -> tuple[Point, Point]:
    if strategy == "centroid":
        return piece.source_centroid, move.target_centroid
    if strategy == "slot_centroid":
        return slot_center, move.target_centroid
    if strategy == "slot_grab":
        return slot_center, move.target_grab_point
    return piece.source_grab_point, move.target_grab_point


def board_matches(expected: Sequence[Sequence[bool]], actual: Sequence[Sequence[bool]]) -> bool:
    return all(expected[row][col] == actual[row][col] for row in range(BOARD_SIZE) for col in range(BOARD_SIZE))


def board_to_tuple(board: Sequence[Sequence[bool]]) -> tuple[tuple[bool, ...], ...]:
    return tuple(tuple(row) for row in board)


def infer_actual_placement(
    current_board: Sequence[Sequence[bool]],
    piece: Piece,
    observed_board: Sequence[Sequence[bool]],
    intended_anchor_col: int,
    intended_anchor_row: int,
) -> InferredPlacement | None:
    target_board = board_to_tuple(observed_board)
    matches: list[tuple[int, int, int, tuple[tuple[bool, ...], ...]]] = []
    for anchor_row in range(BOARD_SIZE - piece.height + 1):
        for anchor_col in range(BOARD_SIZE - piece.width + 1):
            if not all(not current_board[anchor_row + y][anchor_col + x] for x, y in piece.cells):
                continue
            candidate_board, _ = apply_piece(current_board, piece, anchor_col, anchor_row)
            candidate_tuple = board_to_tuple(candidate_board)
            if candidate_tuple != target_board:
                continue
            distance = abs(anchor_col - intended_anchor_col) + abs(anchor_row - intended_anchor_row)
            matches.append((distance, anchor_row, anchor_col, candidate_tuple))

    if not matches:
        return None

    _, anchor_row, anchor_col, candidate_board = min(matches, key=lambda item: (item[0], item[1], item[2]))
    return InferredPlacement(anchor_col=anchor_col, anchor_row=anchor_row, board=candidate_board)


def build_live_auto_config(
    window: WindowInfo,
    image: Image.Image,
    base_tuning: dict | None = None,
    saved_slot_ratios: Sequence[tuple[float, float]] | None = None,
) -> dict:
    tuning = dict(DEFAULT_TUNING)
    if base_tuning:
        tuning.update(base_tuning)
    tuning["piece_block_scale"] = max(0.48, float(tuning.get("piece_block_scale", DEFAULT_TUNING["piece_block_scale"])))

    capture_region = window.rect
    board_local_rect = detect_board_rect_from_capture_image(image)
    board_rect = local_rect_to_global(board_local_rect, image, capture_region)
    tray_local_rect = detect_tray_rect_from_capture_image(image, board_local_rect)
    tray_rect = local_rect_to_global(tray_local_rect, image, capture_region) if tray_local_rect is not None else None

    slot_ratio_source = "tray_thirds"
    if tray_rect is not None:
        slot_centers = tray_slot_centers_from_rect(tray_rect)
    else:
        slot_ratio_source = "saved_slot_ratios" if saved_slot_ratios else "default_slot_ratios"
        source_ratios = tuple(saved_slot_ratios) if saved_slot_ratios else AUTO_SLOT_RATIOS
        slot_centers = [
            Point(
                capture_region.left + (capture_region.width * ratio_x),
                capture_region.top + (capture_region.height * ratio_y),
            )
            for ratio_x, ratio_y in source_ratios
        ]

    payload = {
        "capture_region": rect_to_dict(capture_region),
        "board_rect": rect_to_dict(board_rect),
        "piece_slot_centers": [point_to_dict(point) for point in slot_centers],
        "tuning": tuning,
        "auto_window": {
            "owner_name": window.owner_name,
            "window_name": window.window_name,
            "bounds": rect_to_dict(capture_region),
            "source": "image_detected",
            "slot_source": slot_ratio_source,
        },
    }
    if tray_rect is not None:
        payload["tray_rect"] = rect_to_dict(tray_rect)
    return payload


def build_image_runtime_config(
    image: Image.Image,
    base_tuning: dict | None = None,
    saved_slot_ratios: Sequence[tuple[float, float]] | None = None,
) -> dict:
    tuning = dict(DEFAULT_TUNING)
    if base_tuning:
        tuning.update(base_tuning)
    tuning["piece_block_scale"] = max(0.48, float(tuning.get("piece_block_scale", DEFAULT_TUNING["piece_block_scale"])))

    full_region = Rect(0.0, 0.0, float(image.width), float(image.height))
    phone_rect = detect_phone_rect_from_image(image)
    phone_region = phone_rect if phone_rect is not None else full_region
    scale_x, scale_y = capture_scale(image, full_region)
    crop_box = (
        int(round(phone_region.left * scale_x)),
        int(round(phone_region.top * scale_y)),
        int(round(phone_region.right * scale_x)),
        int(round(phone_region.bottom * scale_y)),
    )
    phone_image = image.crop(crop_box).convert("RGB")
    board_local_rect = detect_board_rect_from_capture_image(phone_image)
    board_rect = local_rect_to_global(board_local_rect, phone_image, phone_region)
    tray_local_rect = detect_tray_rect_from_capture_image(phone_image, board_local_rect)
    tray_rect = local_rect_to_global(tray_local_rect, phone_image, phone_region) if tray_local_rect is not None else None

    if tray_rect is not None:
        slot_centers = tray_slot_centers_from_rect(tray_rect)
        slot_source = "tray_thirds"
    else:
        tray_width = board_rect.width * 1.02
        tray_left = board_rect.left - (board_rect.width * 0.01)
        tray_y = board_rect.bottom + (board_rect.height * 0.26)
        slot_x_ratios = (0.19, 0.5, 0.81)
        slot_centers = [
            Point(
                x=tray_left + (tray_width * ratio_x),
                y=tray_y,
            )
            for ratio_x in slot_x_ratios
        ]
        slot_source = "ratio_fallback"

    payload = {
        "capture_region": rect_to_dict(full_region),
        "board_rect": rect_to_dict(board_rect),
        "piece_slot_centers": [point_to_dict(point) for point in slot_centers],
        "tuning": tuning,
        "auto_window": {
            "owner_name": "image",
            "window_name": "analyze-image",
            "bounds": rect_to_dict(phone_region),
            "source": "image_detected",
            "slot_source": slot_source,
        },
    }
    if tray_rect is not None:
        payload["tray_rect"] = rect_to_dict(tray_rect)
    return payload


def execute_verified_moves(
    initial_image: Image.Image,
    initial_board: Sequence[Sequence[bool]],
    moves: Sequence[Move],
    pieces: Sequence[Piece],
    config: dict,
    move_duration_ms: int,
    move_delay: float,
) -> tuple[Point, str]:
    capture_region = rect_from_dict(config["capture_region"])
    board_rect = rect_from_dict(config["board_rect"])
    slot_centers = [point_from_dict(item) for item in config["piece_slot_centers"]]
    tuning = config.get("tuning", {})
    empty_threshold = float(tuning.get("empty_cell_threshold", 28.0))
    current_drop_offset = Point(
        float(tuning.get("drop_offset_x", 0.0)),
        float(tuning.get("drop_offset_y", 0.0)),
    )
    current_drag_strategy = str(tuning.get("drag_strategy", "grab"))
    cell_w = board_rect.width / BOARD_SIZE
    cell_h = board_rect.height / BOARD_SIZE

    current_image = initial_image
    current_board = clone_board(initial_board)

    for move in moves:
        piece = pieces[move.piece_index]
        expected_board, _ = apply_piece(current_board, piece, move.anchor_col, move.anchor_row)
        mismatch_image: Image.Image | None = None
        observed_board = clone_board(current_board)
        matched = False

        slot_center = slot_centers[piece.slot_index]
        ordered_strategies = [current_drag_strategy] + [
            strategy for strategy in ("grab", "centroid", "slot_grab", "slot_centroid")
            if strategy != current_drag_strategy
        ]
        attempt = 0
        for candidate_offset in candidate_drop_offsets(current_drop_offset, cell_w, cell_h):
            for strategy in ordered_strategies:
                start_point, base_target = drag_plan_points(piece, move, slot_center, strategy)
                attempt += 1
                offset_distance = abs(candidate_offset.x - current_drop_offset.x) + abs(candidate_offset.y - current_drop_offset.y)
                drag_duration = move_duration_ms + int(min(220.0, offset_distance * 1.8))
                post_delay = move_delay + min(0.45, offset_distance / max(cell_w + cell_h, 1.0))
                adjusted_target = clamp_drop_target(add_points(base_target, candidate_offset), board_rect, cell_w, cell_h)
                effective_offset = subtract_points(adjusted_target, base_target)
                if attempt > 1:
                    print(
                        "Retrying drop with "
                        f"{strategy} strategy and target offset ({effective_offset.x:.1f}, {effective_offset.y:.1f}) px...",
                        flush=True,
                    )
                final_release_point = adjusted_target
                released = False
                helper_mouse_down(start_point)
                try:
                    time.sleep(0.06)
                    helper_drag_to(adjusted_target, drag_duration)
                    time.sleep(min(0.16, post_delay))

                    try:
                        hover_image = helper_capture_image(capture_region)
                        preview_anchor, preview_score = detect_preview_anchor(
                            current_image,
                            hover_image,
                            board_rect,
                            capture_region,
                            current_board,
                            piece,
                        )
                        if preview_anchor is not None and preview_score >= 18.0:
                            for _ in range(2):
                                delta_cols = move.anchor_col - preview_anchor[0]
                                delta_rows = move.anchor_row - preview_anchor[1]
                                if delta_cols == 0 and delta_rows == 0:
                                    break
                                final_release_point = clamp_drop_target(
                                    Point(
                                        final_release_point.x + (delta_cols * cell_w),
                                        final_release_point.y + (delta_rows * cell_h),
                                    ),
                                    board_rect,
                                    cell_w,
                                    cell_h,
                                )
                                print(
                                    "Preview adjusted target by "
                                    f"{delta_cols} cols, {delta_rows} rows before release.",
                                    flush=True,
                                )
                                helper_drag_to(final_release_point, max(110, drag_duration // 2))
                                time.sleep(0.08)
                                hover_image = helper_capture_image(capture_region)
                                preview_anchor, preview_score = detect_preview_anchor(
                                    current_image,
                                    hover_image,
                                    board_rect,
                                    capture_region,
                                    current_board,
                                    piece,
                                )
                                if preview_anchor is None or preview_score < 18.0:
                                    break
                    except Exception:
                        pass

                    helper_mouse_up(final_release_point)
                    released = True
                finally:
                    if not released:
                        try:
                            helper_mouse_up()
                        except Exception:
                            pass
                time.sleep(post_delay)

                matched = False
                for _ in range(4):
                    current_image = capture_image(capture_region)
                    mismatch_image = current_image
                    observed_board = detect_board(current_image, board_rect, capture_region, empty_threshold)
                    if board_matches(expected_board, observed_board):
                        current_board = expected_board
                        current_drop_offset = effective_offset
                        current_drag_strategy = strategy
                        matched = True
                        break
                    time.sleep(0.12)

                if matched:
                    break

                # If nothing changed at all, the drop likely failed to register.
                if not board_matches(current_board, observed_board):
                    inferred = infer_actual_placement(
                        current_board,
                        piece,
                        observed_board,
                        move.anchor_col,
                        move.anchor_row,
                    )
                    if inferred is not None:
                        delta_cols = inferred.anchor_col - move.anchor_col
                        delta_rows = inferred.anchor_row - move.anchor_row
                        new_offset = effective_offset
                        if delta_cols != 0 or delta_rows != 0:
                            new_offset = Point(
                                effective_offset.x - (delta_cols * cell_w),
                                effective_offset.y - (delta_rows * cell_h),
                            )
                            print(
                                "Adjusted learned drop offset to "
                                f"({new_offset.x:.1f}, {new_offset.y:.1f}) px "
                                f"after slot {move.slot_index + 1} landed at row {inferred.anchor_row + 1}, "
                                f"col {inferred.anchor_col + 1}."
                            )
                        current_drop_offset = new_offset
                        current_drag_strategy = strategy
                        current_board = [list(row) for row in inferred.board]
                        matched = True
                        break
                    continue

            if matched:
                break

        if matched:
            time.sleep(move_delay)
            continue

        if mismatch_image is not None:
            inferred = infer_actual_placement(
                current_board,
                piece,
                observed_board,
                move.anchor_col,
                move.anchor_row,
            )
            if inferred is not None:
                delta_cols = inferred.anchor_col - move.anchor_col
                delta_rows = inferred.anchor_row - move.anchor_row
                if delta_cols != 0 or delta_rows != 0:
                    current_drop_offset = Point(
                        current_drop_offset.x - (delta_cols * cell_w),
                        current_drop_offset.y - (delta_rows * cell_h),
                    )
                    print(
                        "Adjusted learned drop offset to "
                        f"({current_drop_offset.x:.1f}, {current_drop_offset.y:.1f}) px "
                        f"after slot {move.slot_index + 1} landed at row {inferred.anchor_row + 1}, "
                        f"col {inferred.anchor_col + 1}."
                    )
                current_drag_strategy = ordered_strategies[0]
                current_board = [list(row) for row in inferred.board]
                time.sleep(move_delay)
                continue

        failure_path = ROOT / "output" / "block_blast_post_drop_mismatch.png"
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        if mismatch_image is not None:
            mismatch_image.save(failure_path)
        raise RuntimeError(
            f"Board state after dropping slot {move.slot_index + 1} did not match the expected placement.\n"
            f"Saved the post-drop capture to {failure_path}"
        )

    return current_drop_offset, current_drag_strategy


def default_capture_region_from_points(config: dict) -> Rect:
    return rect_from_dict(config["capture_region"])


def interactive_calibration(config_path: Path) -> None:
    print("Block Blast calibration")
    print("Keep the iPhone Mirroring window on the main display during calibration and play.")
    ensure_mouse_helper()

    capture_top_left = prompt_point("Move the cursor to the top-left corner of the mirrored iPhone screen content.")
    capture_bottom_right = prompt_point("Move the cursor to the bottom-right corner of the mirrored iPhone screen content.")
    board_top_left = prompt_point("Move the cursor to the top-left corner of the 8x8 board interior.")
    board_bottom_right = prompt_point("Move the cursor to the bottom-right corner of the 8x8 board interior.")

    print("Next: click the three playable block pieces in the bottom tray below the board.")
    slot_points = [
        prompt_point("Move the cursor to the center of the left playable block piece in the bottom tray."),
        prompt_point("Move the cursor to the center of the middle playable block piece in the bottom tray."),
        prompt_point("Move the cursor to the center of the right playable block piece in the bottom tray."),
    ]

    payload = {
        "capture_region": rect_to_dict(rect_from_points(capture_top_left, capture_bottom_right)),
        "board_rect": rect_to_dict(rect_from_points(board_top_left, board_bottom_right)),
        "piece_slot_centers": [point_to_dict(point) for point in slot_points],
        "tuning": {
            "empty_cell_threshold": 28.0,
            "piece_block_scale": 0.35,
            "slot_crop_width_scale": 8.0,
            "slot_crop_height_scale": 5.5,
        },
    }
    save_config(config_path, payload)
    print(f"Saved calibration to {config_path}")


def point_to_dict(point: Point) -> dict:
    return {"x": round(point.x, 2), "y": round(point.y, 2)}


def rect_to_dict(rect: Rect) -> dict:
    return {
        "left": round(rect.left, 2),
        "top": round(rect.top, 2),
        "right": round(rect.right, 2),
        "bottom": round(rect.bottom, 2),
    }


def maybe_loop(args: argparse.Namespace, config: dict, config_path: Path) -> None:
    move_duration_ms = int(args.move_duration_ms)
    move_delay = float(args.move_delay)
    loop_delay = float(args.loop_delay)
    initial_tuning = config.get("tuning", {})
    fast_search = bool(args.assist_live or args.loop or args.play_once)
    learned_drop_offset = Point(
        float(initial_tuning.get("drop_offset_x", 0.0)),
        float(initial_tuning.get("drop_offset_y", 0.0)),
    )
    learned_drag_strategy = str(initial_tuning.get("drag_strategy", "grab"))
    last_assist_output: str | None = None
    consumed_slots: set[int] = set()
    try:
        _, saved_slot_ratios = ratios_from_config(config)
    except Exception:
        saved_slot_ratios = None

    if args.countdown:
        countdown(args.countdown)

    if args.assist_live:
        print(
            "Watching iPhone Mirroring and refreshing the assist guide. "
            "Press Ctrl+C to stop.",
            flush=True,
        )

    while True:
        if args.assist_live:
            print("Refreshing live guide...", flush=True)
        else:
            print("Capturing current game state...", flush=True)
        runtime_config = config
        image: Image.Image | None = None
        if not args.no_auto_window:
            try:
                window = find_mirroring_window()
                if window is not None:
                    image = capture_image(window.rect)
                    runtime_config = build_live_auto_config(
                        window,
                        image,
                        config.get("tuning", {}),
                        saved_slot_ratios,
                    )
                else:
                    runtime_config = config
            except Exception:
                runtime_config = config
                image = None
        runtime_config = dict(runtime_config)
        if args.assist_live and not args.no_auto_window and not runtime_config.get("auto_window"):
            raise RuntimeError(
                "No live iPhone Mirroring window was found. "
                "Open iPhone Mirroring with Block Blast visible, then run --assist-live again."
            )
        runtime_tuning = dict(runtime_config.get("tuning", {}))
        runtime_tuning["drop_offset_x"] = learned_drop_offset.x
        runtime_tuning["drop_offset_y"] = learned_drop_offset.y
        runtime_tuning["drag_strategy"] = learned_drag_strategy
        runtime_config["tuning"] = runtime_tuning
        capture_region = default_capture_region_from_points(runtime_config)
        if image is None:
            image = capture_image(capture_region)
        ensure_block_blast_visible(image, runtime_config)
        try:
            print("Analyzing board and tray pieces...", flush=True)
            board, pieces, result = analyze(image, runtime_config, fast_search=fast_search)
        except Exception as exc:
            failure_path = ROOT / "output" / "block_blast_failure_capture.png"
            failure_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(failure_path)
            raise RuntimeError(
                f"{exc}\nSaved the last captured image to {failure_path}"
            ) from exc

        if args.loop:
            board_rect = rect_from_dict(runtime_config["board_rect"])
            visible_slot_indices = {piece.slot_index for piece in pieces}
            if consumed_slots == {0, 1, 2} and visible_slot_indices == {0, 1, 2}:
                consumed_slots.clear()
                print("Detected a fresh 3-piece tray. Resetting used-slot tracking.", flush=True)

            if consumed_slots:
                filtered_pieces = [piece for piece in pieces if piece.slot_index not in consumed_slots]
                if len(filtered_pieces) != len(pieces):
                    ignored_labels = ", ".join(f"slot {slot + 1}" for slot in sorted(consumed_slots & visible_slot_indices))
                    if ignored_labels:
                        print(
                            f"Ignoring already-used {ignored_labels} until the tray fully refills.",
                            flush=True,
                        )
                    pieces = filtered_pieces
                    result = search_best_live_move(board, pieces, board_rect)

        assist_output = None
        if args.assist or args.assist_live:
            assist_output = assist_text(board, pieces, result, runtime_config)
            if args.assist_live:
                if assist_output != last_assist_output:
                    if sys.stdout.isatty():
                        print("\033[2J\033[H", end="")
                    print(assist_output, flush=True)
                    last_assist_output = assist_output
            else:
                print(assist_output)
        else:
            print(board_to_text(board))
            print(f"Visible tray pieces: {len(pieces)}")
            print(describe_moves(result, pieces))

        debug_image_path = args.debug_image
        if args.assist and not args.assist_live and not debug_image_path:
            debug_image_path = str(ROOT / "output" / "block_blast_assist.png")

        if debug_image_path:
            render_debug(
                image=image.copy(),
                capture_region=capture_region,
                board_rect=rect_from_dict(runtime_config["board_rect"]),
                board=board,
                pieces=pieces,
                result=result,
                output_path=Path(debug_image_path),
            )
            if args.assist or args.assist_live:
                print(f"\nSaved annotated assist image to {Path(debug_image_path).resolve()}")
                raw_assist_path = ROOT / "output" / "block_blast_assist_raw.png"
                raw_assist_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(raw_assist_path)
                print(f"Saved raw assist capture to {raw_assist_path.resolve()}")
                slot_crop_paths = save_slot_crops(image, runtime_config, ROOT / "output", "block_blast_assist")
                print("Saved assist slot crops:")
                for path in slot_crop_paths:
                    print(path.resolve())

        if args.assist and assist_output is not None:
            assist_text_path = DEFAULT_ASSIST_TEXT_PATH
            write_text_file(assist_text_path, assist_output)
            print(f"Saved assist text guide to {assist_text_path.resolve()}")

        if args.dry_run or args.assist:
            break
        if args.assist_live:
            time.sleep(loop_delay)
            continue

        if not pieces:
            if args.loop:
                print("Tray is temporarily empty. Waiting for the next visible state...")
                time.sleep(loop_delay)
                continue
            print("No visible pieces detected. Stopping.")
            break

        if not result.moves:
            print("No legal sequence detected. Stopping.")
            break

        moves_to_apply = result.moves[:1] if args.loop else result.moves
        print("Executing move...", flush=True)
        previous_offset = learned_drop_offset
        previous_strategy = learned_drag_strategy
        learned_drop_offset, learned_drag_strategy = execute_verified_moves(
            image,
            board,
            moves_to_apply,
            pieces,
            runtime_config,
            move_duration_ms,
            move_delay,
        )
        if (
            abs(learned_drop_offset.x - previous_offset.x) > 0.5
            or abs(learned_drop_offset.y - previous_offset.y) > 0.5
            or learned_drag_strategy != previous_strategy
        ):
            persist_drop_behavior(config_path, learned_drop_offset, learned_drag_strategy)
            print(
                "Saved learned drop behavior to config: "
                f"strategy={learned_drag_strategy}, "
                f"offset=({learned_drop_offset.x:.1f}, {learned_drop_offset.y:.1f}) px",
                flush=True,
            )

        if args.loop:
            consumed_slots.update(move.slot_index for move in moves_to_apply)
            print(
                "Marked used slots this turn: "
                + ", ".join(f"slot {slot + 1}" for slot in sorted(consumed_slots)),
                flush=True,
            )

        if not args.loop:
            break
        time.sleep(loop_delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Best-effort Block Blast solver and Mac drag bot.")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to the calibration JSON file.")
    parser.add_argument("--calibrate", action="store_true", help="Run the interactive calibration flow.")
    parser.add_argument("--analyze-image", help="Analyze a saved screenshot instead of grabbing the screen.")
    parser.add_argument("--play-once", action="store_true", help="Capture the board and play one visible three-piece turn.")
    parser.add_argument("--loop", action="store_true", help="Keep capturing and playing until no move is found.")
    parser.add_argument("--dry-run", action="store_true", help="Print moves without moving the mouse.")
    parser.add_argument("--assist", action="store_true", help="Analyze the current turn and print a human-readable placement guide without moving the mouse.")
    parser.add_argument("--assist-live", action="store_true", help="Continuously refresh the assist guide without moving the mouse.")
    parser.add_argument("--print-assist-file", action="store_true", help="Print the last saved assist text guide directly in the terminal.")
    parser.add_argument("--no-auto-window", action="store_true", help="Disable automatic window-based calibration and use the saved JSON instead.")
    parser.add_argument("--print-window-config", action="store_true", help="Print the currently detected auto-window calibration JSON and exit.")
    parser.add_argument("--debug-image", help="Save an annotated screenshot for debugging.")
    parser.add_argument("--countdown", type=int, default=0, help="Countdown in seconds before the first live move.")
    parser.add_argument("--move-duration-ms", type=int, default=220, help="How long each drag should take.")
    parser.add_argument("--move-delay", type=float, default=0.35, help="Pause between live drags.")
    parser.add_argument("--loop-delay", type=float, default=0.9, help="Pause between loop iterations.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()

    if args.calibrate:
        interactive_calibration(config_path)
        return

    if args.print_assist_file:
        print_saved_assist_file(DEFAULT_ASSIST_TEXT_PATH)
        return

    if args.print_window_config:
        window = find_mirroring_window()
        if window is None:
            raise SystemExit("Could not find an iPhone Mirroring-style window on screen.")
        image = capture_image(window.rect)
        ensure_block_blast_visible(image, {"capture_region": rect_to_dict(window.rect), "board_rect": rect_to_dict(window.rect)})
        base_tuning = load_config(config_path).get("tuning", {}) if config_path.exists() else {}
        saved_slot_ratios = None
        if config_path.exists():
            try:
                _, saved_slot_ratios = ratios_from_config(load_config(config_path))
            except Exception:
                saved_slot_ratios = None
        print(json.dumps(build_live_auto_config(window, image, base_tuning, saved_slot_ratios), indent=2))
        return

    config = resolve_runtime_config(config_path, allow_auto_window=not args.no_auto_window)
    validate_config(config)

    if args.analyze_image:
        if args.assist_live:
            raise SystemExit("--assist-live requires a live iPhone Mirroring window and cannot be combined with --analyze-image.")
        image = Image.open(Path(args.analyze_image).expanduser()).convert("RGB")
        base_tuning = load_config(config_path).get("tuning", {}) if config_path.exists() else {}
        saved_slot_ratios = None
        if config_path.exists():
            try:
                _, saved_slot_ratios = ratios_from_config(load_config(config_path))
            except Exception:
                saved_slot_ratios = None
        config = build_image_runtime_config(image, base_tuning, saved_slot_ratios)
        board, pieces, result = analyze(image, config)
        if args.assist:
            assist_output = assist_text(board, pieces, result, config)
            print(assist_output)
            write_text_file(DEFAULT_ASSIST_TEXT_PATH, assist_output)
        else:
            print(board_to_text(board))
            print(describe_moves(result, pieces))
        if args.debug_image:
            render_debug(
                image=image.copy(),
                capture_region=rect_from_dict(config["capture_region"]),
                board_rect=rect_from_dict(config["board_rect"]),
                board=board,
                pieces=pieces,
                result=result,
                output_path=Path(args.debug_image),
            )
        return

    if not args.play_once and not args.loop and not args.dry_run and not args.assist and not args.assist_live:
        raise SystemExit("Choose one of --play-once, --loop, --dry-run, --assist, --assist-live, --print-assist-file, or --analyze-image.")

    maybe_loop(args, config, config_path)


if __name__ == "__main__":
    main()
