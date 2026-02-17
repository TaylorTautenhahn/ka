from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ROI:
    x: int
    y: int
    w: int
    h: int

    def as_mss_bbox(self) -> dict[str, int]:
        return {"left": self.x, "top": self.y, "width": self.w, "height": self.h}

    def center(self) -> tuple[int, int]:
        return (self.x + self.w // 2, self.y + self.h // 2)


@dataclass(frozen=True)
class ButtonObservation:
    name: str
    text: str
    visible: bool
    amount: float = 0.0


@dataclass(frozen=True)
class GameState:
    hero_cards: tuple[str, str]
    board_cards: tuple[str, ...]
    pot: Optional[float]
    call_amount: float
    buttons: dict[str, ButtonObservation]

    @property
    def available_actions(self) -> set[str]:
        return {name for name, b in self.buttons.items() if b.visible}

    def fingerprint(self) -> str:
        button_snapshot = ";".join(
            f"{k}:{int(v.visible)}:{v.amount:.2f}:{v.text.lower()}"
            for k, v in sorted(self.buttons.items())
        )
        board = "".join(self.board_cards)
        hero = "".join(self.hero_cards)
        pot = "none" if self.pot is None else f"{self.pot:.2f}"
        return f"hero={hero}|board={board}|pot={pot}|call={self.call_amount:.2f}|{button_snapshot}"


@dataclass(frozen=True)
class Decision:
    action: str
    equity: Optional[float]
    reason: str


@dataclass(frozen=True)
class VisionDebugInfo:
    card_notes: dict[str, str]
    button_texts: dict[str, str]
    pot_text: str
