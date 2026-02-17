from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2

from .config import BotConfig, save_config
from .capture import ScreenCapture
from .models import ROI


def _select_roi(frame, title: str) -> Optional[tuple[int, int, int, int]]:
    preview = frame.copy()
    cv2.putText(
        preview,
        title,
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )
    rect = cv2.selectROI("poker-cv-agent calibrate", preview, showCrosshair=True, fromCenter=False)
    x, y, w, h = [int(v) for v in rect]
    if w <= 0 or h <= 0:
        return None
    return x, y, w, h


def _to_absolute(roi: tuple[int, int, int, int], monitor_bbox: dict[str, int]) -> ROI:
    x, y, w, h = roi
    return ROI(
        x=monitor_bbox["left"] + x,
        y=monitor_bbox["top"] + y,
        w=w,
        h=h,
    )


def run_calibration(output_path: str, monitor_index: int) -> None:
    capture = ScreenCapture(monitor_index=monitor_index)
    frame = capture.grab_monitor()
    monitor_bbox = capture.monitor_bbox

    print("Draw a rectangle then press SPACE/ENTER to confirm. Press c to cancel current ROI.")

    required_prompts = [
        "Select HERO card #1",
        "Select HERO card #2",
        "Select BOARD card #1 (flop left)",
        "Select BOARD card #2 (flop middle)",
        "Select BOARD card #3 (flop right)",
        "Select BOARD card #4 (turn)",
        "Select BOARD card #5 (river)",
        "Select FOLD button",
        "Select CALL/CHECK button",
        "Select RAISE/BET button",
    ]

    picked: list[ROI] = []
    for prompt in required_prompts:
        rect = _select_roi(frame, prompt)
        if rect is None:
            cv2.destroyAllWindows()
            raise RuntimeError(f"Calibration cancelled while selecting: {prompt}")
        picked.append(_to_absolute(rect, monitor_bbox))

    optional_pot_rect = _select_roi(frame, "Optional: select POT region (cancel to skip)")
    cv2.destroyAllWindows()

    pot_roi = _to_absolute(optional_pot_rect, monitor_bbox) if optional_pot_rect else None

    config = BotConfig(
        monitor_index=monitor_index,
        loop_interval_seconds=0.8,
        action_cooldown_seconds=2.0,
        opponents=5,
        monte_carlo_iterations=800,
        click_jitter_pixels=8,
        hero_cards=(picked[0], picked[1]),
        board_cards=(picked[2], picked[3], picked[4], picked[5], picked[6]),
        buttons={
            "fold": picked[7],
            "call": picked[8],
            "raise": picked[9],
        },
        pot_roi=pot_roi,
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    save_config(output, config)
    print(f"Saved calibration to {output.resolve()}")
