from __future__ import annotations

import re
from typing import Optional

import cv2
import numpy as np
import pytesseract

from .config import BotConfig
from .capture import ScreenCapture
from .models import ButtonObservation, GameState, ROI, VisionDebugInfo

_RANK_MAP = {
    "10": "T",
    "0": "T",
    "O": "T",
    "A": "A",
    "K": "K",
    "Q": "Q",
    "J": "J",
    "T": "T",
    "9": "9",
    "8": "8",
    "7": "7",
    "6": "6",
    "5": "5",
    "4": "4",
    "3": "3",
    "2": "2",
}


class VisionEngine:
    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def capture_state(self, capture: ScreenCapture) -> GameState:
        state, _ = self.capture_state_with_debug(capture)
        return state

    def capture_state_with_debug(self, capture: ScreenCapture) -> tuple[GameState, VisionDebugInfo]:
        hero_cards: list[str] = []
        card_notes: dict[str, str] = {}

        for idx, roi in enumerate(self.config.hero_cards, start=1):
            card, note = self.read_card_with_debug(capture.grab_roi(roi))
            hero_cards.append(card or "??")
            card_notes[f"hero_{idx}"] = note

        board_cards: list[str] = []
        for idx, roi in enumerate(self.config.board_cards, start=1):
            card, note = self.read_card_with_debug(capture.grab_roi(roi))
            if card:
                board_cards.append(card)
            card_notes[f"board_{idx}"] = note

        buttons: dict[str, ButtonObservation] = {}
        button_texts: dict[str, str] = {}
        for name, roi in self.config.buttons.items():
            button = self.read_button(name=name, image=capture.grab_roi(roi))
            buttons[name] = button
            button_texts[name] = button.text

        pot_value: Optional[float] = None
        pot_text = ""
        if self.config.pot_roi:
            pot_value, pot_text = self.read_float_with_text(capture.grab_roi(self.config.pot_roi))

        call_amount = buttons.get("call", ButtonObservation("call", "", False, 0.0)).amount

        state = GameState(
            hero_cards=(hero_cards[0], hero_cards[1]),
            board_cards=tuple(board_cards),
            pot=pot_value,
            call_amount=call_amount,
            buttons=buttons,
        )
        debug = VisionDebugInfo(card_notes=card_notes, button_texts=button_texts, pot_text=pot_text)
        return state, debug

    def read_button(self, name: str, image: np.ndarray) -> ButtonObservation:
        text = self.read_text(
            image,
            psm=7,
            whitelist="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789. ",
        )
        normalized = re.sub(r"\s+", " ", text.strip().lower())
        visible = self._button_visible(name, normalized)

        amount = 0.0
        if name == "call" and visible:
            parsed = self._extract_amount(normalized)
            amount = parsed if parsed is not None else 0.0

        return ButtonObservation(name=name, text=normalized, visible=visible, amount=amount)

    def read_card(self, image: np.ndarray) -> Optional[str]:
        parsed, _ = self.read_card_with_debug(image)
        return parsed

    def read_card_with_debug(self, image: np.ndarray) -> tuple[Optional[str], str]:
        if not self._card_present(image):
            return None, "no-card"

        rank, rank_raw = self._read_rank_details(image)
        suit, suit_note = self._read_suit_details(image)

        if rank is None or suit is None:
            return None, f"rank_raw='{rank_raw}' suit={suit_note}"

        return f"{rank}{suit}", f"rank_raw='{rank_raw}' suit={suit_note}"

    def read_float(self, image: np.ndarray) -> Optional[float]:
        value, _ = self.read_float_with_text(image)
        return value

    def read_float_with_text(self, image: np.ndarray) -> tuple[Optional[float], str]:
        text = self.read_text(image, psm=7, whitelist="0123456789.")
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        if not match:
            return None, text.strip().lower()
        return float(match.group(1)), text.strip().lower()

    def read_text(self, image: np.ndarray, psm: int, whitelist: str) -> str:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        enlarged = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        bw = cv2.adaptiveThreshold(
            enlarged,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            9,
        )

        ocr_config = f"--oem 3 --psm {psm} -c tessedit_char_whitelist={whitelist}"
        text = pytesseract.image_to_string(bw, config=ocr_config)
        return text.strip()

    @staticmethod
    def _button_visible(name: str, text: str) -> bool:
        if not text:
            return False

        if name == "fold":
            return "fold" in text
        if name == "call":
            return ("call" in text) or ("check" in text) or ("straddle" in text)
        if name == "raise":
            return ("raise" in text) or ("bet" in text)
        return False

    @staticmethod
    def _extract_amount(text: str) -> Optional[float]:
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        if not match:
            return None
        return float(match.group(1))

    @staticmethod
    def _card_present(image: np.ndarray) -> bool:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        edge_density = cv2.Canny(gray, 60, 120).mean()
        return laplacian_var > 35.0 and edge_density > 6.0

    def _read_rank_details(self, image: np.ndarray) -> tuple[Optional[str], str]:
        rank_text = self.read_text(image, psm=8, whitelist="A23456789TJQK10")
        cleaned = rank_text.upper().replace(" ", "")
        if not cleaned:
            return None, ""

        if cleaned.startswith("10"):
            return "T", cleaned

        token = cleaned[0]
        return _RANK_MAP.get(token), cleaned

    @staticmethod
    def _read_suit_details(image: np.ndarray) -> tuple[Optional[str], str]:
        h, w = image.shape[:2]
        center = image[h // 3 : (2 * h) // 3, w // 4 : (3 * w) // 4]
        hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)

        hue = hsv[:, :, 0]
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]

        colorful = sat > 45
        val_mean = float(val.mean())
        if np.count_nonzero(colorful) < 20:
            if val_mean < 90:
                return "s", f"spade-mono(v={val_mean:.0f})"
            return None, f"mono-uncertain(v={val_mean:.0f})"

        hue_mean = float(hue[colorful].mean())
        if hue_mean < 10 or hue_mean > 165:
            return "h", f"heart-red(h={hue_mean:.0f})"
        if 35 <= hue_mean < 90:
            return "c", f"club-green(h={hue_mean:.0f})"
        if 90 <= hue_mean < 150:
            return "d", f"diamond-blue(h={hue_mean:.0f})"
        if val_mean < 100:
            return "s", f"spade-dark(v={val_mean:.0f})"
        return "s", f"spade-fallback(h={hue_mean:.0f},v={val_mean:.0f})"


def debug_draw_state(frame: np.ndarray, rois: list[tuple[str, ROI]]) -> np.ndarray:
    rendered = frame.copy()
    for name, roi in rois:
        cv2.rectangle(rendered, (roi.x, roi.y), (roi.x + roi.w, roi.y + roi.h), (0, 255, 255), 2)
        cv2.putText(
            rendered,
            name,
            (roi.x, max(15, roi.y - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )
    return rendered
