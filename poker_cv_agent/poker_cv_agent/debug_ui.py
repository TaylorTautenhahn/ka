from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from .config import BotConfig
from .models import Decision, GameState, ROI, VisionDebugInfo

WINDOW_NAME = "poker_cv_agent debug"


def _trim(text: str, max_len: int = 60) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_float(value: Optional[float], precision: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{precision}f}"


def _to_local(roi: ROI, monitor_bbox: dict[str, int]) -> tuple[int, int, int, int]:
    x = roi.x - monitor_bbox["left"]
    y = roi.y - monitor_bbox["top"]
    return x, y, roi.w, roi.h


def _draw_roi(frame: np.ndarray, monitor_bbox: dict[str, int], roi: ROI, label: str, color: tuple[int, int, int]) -> None:
    x, y, w, h = _to_local(roi, monitor_bbox)
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

    text_y = max(15, y - 8)
    cv2.putText(
        frame,
        _trim(label, 62),
        (x, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        color,
        1,
        cv2.LINE_AA,
    )


def render_debug_frame(
    frame: np.ndarray,
    config: BotConfig,
    monitor_bbox: dict[str, int],
    state: GameState,
    decision: Optional[Decision],
    vision_debug: VisionDebugInfo,
    dry_run: bool,
) -> np.ndarray:
    rendered = frame.copy()

    for idx, roi in enumerate(config.hero_cards, start=1):
        card = state.hero_cards[idx - 1]
        note = vision_debug.card_notes.get(f"hero_{idx}", "")
        _draw_roi(rendered, monitor_bbox, roi, f"hero_{idx}: {card} | {note}", (0, 255, 255))

    for idx, roi in enumerate(config.board_cards, start=1):
        card = state.board_cards[idx - 1] if idx <= len(state.board_cards) else "--"
        note = vision_debug.card_notes.get(f"board_{idx}", "")
        _draw_roi(rendered, monitor_bbox, roi, f"board_{idx}: {card} | {note}", (0, 220, 120))

    for name, roi in config.buttons.items():
        obs = state.buttons.get(name)
        if obs is None:
            label = f"{name}: missing"
            color = (180, 180, 180)
        else:
            shown_text = vision_debug.button_texts.get(name, obs.text)
            label = f"{name}: vis={int(obs.visible)} txt='{shown_text}'"
            color = (255, 160, 40) if obs.visible else (90, 90, 90)
        _draw_roi(rendered, monitor_bbox, roi, label, color)

    if config.pot_roi:
        pot_text = vision_debug.pot_text or ""
        _draw_roi(
            rendered,
            monitor_bbox,
            config.pot_roi,
            f"pot: {_format_float(state.pot)} ocr='{pot_text}'",
            (200, 90, 255),
        )

    hero = " ".join(state.hero_cards)
    board = " ".join(state.board_cards) if state.board_cards else "(none)"
    actions = ", ".join(sorted(state.available_actions)) or "none"

    decision_text = "none"
    reason_text = ""
    if decision:
        eq = "n/a" if decision.equity is None else f"{decision.equity:.3f}"
        decision_text = f"{decision.action.upper()} (equity={eq})"
        reason_text = decision.reason

    lines = [
        f"mode={'DRY-RUN' if dry_run else 'LIVE'}",
        f"hero={hero}",
        f"board={board}",
        f"pot={_format_float(state.pot)} call={state.call_amount:.2f}",
        f"available={actions}",
        f"decision={decision_text}",
        f"reason={_trim(reason_text, 82)}",
        "keys: q=quit debug window",
    ]

    panel_x, panel_y = 12, 12
    line_h = 20
    panel_w = min(max(430, int(rendered.shape[1] * 0.65)), rendered.shape[1] - 24)
    panel_h = line_h * len(lines) + 14

    cv2.rectangle(rendered, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (15, 15, 15), -1)
    cv2.rectangle(rendered, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (85, 85, 85), 1)

    for i, line in enumerate(lines):
        cv2.putText(
            rendered,
            _trim(line, 96),
            (panel_x + 10, panel_y + 22 + (i * line_h)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (230, 230, 230),
            1,
            cv2.LINE_AA,
        )

    return rendered
