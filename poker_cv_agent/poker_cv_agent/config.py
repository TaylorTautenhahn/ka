from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

from .models import ROI


@dataclass(frozen=True)
class BotConfig:
    monitor_index: int
    loop_interval_seconds: float
    action_cooldown_seconds: float
    opponents: int
    monte_carlo_iterations: int
    click_jitter_pixels: int
    hero_cards: tuple[ROI, ROI]
    board_cards: tuple[ROI, ROI, ROI, ROI, ROI]
    buttons: dict[str, ROI]
    pot_roi: Optional[ROI]


def _parse_roi(raw: dict[str, Any]) -> ROI:
    return ROI(
        x=int(raw["x"]),
        y=int(raw["y"]),
        w=int(raw["w"]),
        h=int(raw["h"]),
    )


def _roi_to_dict(roi: ROI) -> dict[str, int]:
    return {"x": roi.x, "y": roi.y, "w": roi.w, "h": roi.h}


def load_config(path: str | Path) -> BotConfig:
    raw = yaml.safe_load(Path(path).read_text())

    hero = raw.get("hero_cards") or []
    if len(hero) != 2:
        raise ValueError("Config must define exactly 2 hero_cards ROIs")

    board = raw.get("board_cards") or []
    if len(board) != 5:
        raise ValueError("Config must define exactly 5 board_cards ROIs")

    buttons = raw.get("buttons") or {}
    required_buttons = {"fold", "call", "raise"}
    missing = required_buttons - set(buttons)
    if missing:
        raise ValueError(f"Config missing button ROIs: {', '.join(sorted(missing))}")

    pot_roi = raw.get("pot_roi")
    return BotConfig(
        monitor_index=int(raw.get("monitor_index", 1)),
        loop_interval_seconds=float(raw.get("loop_interval_seconds", 0.8)),
        action_cooldown_seconds=float(raw.get("action_cooldown_seconds", 2.0)),
        opponents=max(1, int(raw.get("opponents", 5))),
        monte_carlo_iterations=max(100, int(raw.get("monte_carlo_iterations", 800))),
        click_jitter_pixels=max(0, int(raw.get("click_jitter_pixels", 8))),
        hero_cards=tuple(_parse_roi(r) for r in hero),
        board_cards=tuple(_parse_roi(r) for r in board),
        buttons={name: _parse_roi(r) for name, r in buttons.items()},
        pot_roi=_parse_roi(pot_roi) if pot_roi else None,
    )


def save_config(path: str | Path, config: BotConfig) -> None:
    payload: dict[str, Any] = {
        "monitor_index": config.monitor_index,
        "loop_interval_seconds": config.loop_interval_seconds,
        "action_cooldown_seconds": config.action_cooldown_seconds,
        "opponents": config.opponents,
        "monte_carlo_iterations": config.monte_carlo_iterations,
        "click_jitter_pixels": config.click_jitter_pixels,
        "hero_cards": [_roi_to_dict(roi) for roi in config.hero_cards],
        "board_cards": [_roi_to_dict(roi) for roi in config.board_cards],
        "buttons": {name: _roi_to_dict(roi) for name, roi in config.buttons.items()},
    }
    if config.pot_roi:
        payload["pot_roi"] = _roi_to_dict(config.pot_roi)

    Path(path).write_text(yaml.safe_dump(payload, sort_keys=False))
