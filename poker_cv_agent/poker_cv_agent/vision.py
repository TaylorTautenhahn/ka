from __future__ import annotations

import re
from typing import Optional

import cv2
import numpy as np
import pytesseract

from .config import BotConfig
from .capture import ScreenCapture
from .models import ButtonObservation, GameState, ROI

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
        hero_cards = tuple(
            self.read_card(capture.grab_roi(roi)) or "??" for roi in self.config.hero_cards
        )

        board_cards: list[str] = []
        for roi in self.config.board_cards:
            card = self.read_card(capture.grab_roi(roi))
            if card:
                board_cards.append(card)

        buttons: dict[str, ButtonObservation] = {}
        for name, roi in self.config.buttons.items():
            buttons[name] = self.read_button(name=name, image=capture.grab_roi(roi))

        pot_value = None
        if self.config.pot_roi:
            pot_value = self.read_float(capture.grab_roi(self.config.pot_roi))

        call_amount = buttons.get("call", ButtonObservation("call", "", False, 0.0)).amount

        return GameState(
            hero_cards=hero_cards,
            board_cards=tuple(board_cards),
            pot=pot_value,
            call_amount=call_amount,
            buttons=buttons,
        )

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
        if not self._card_present(image):
            return None

        rank = self._read_rank(image)
        if rank is None:
            return None

        suit = self._read_suit(image)
        if suit is None:
            return None

        return f"{rank}{suit}"

    def read_float(self, image: np.ndarray) -> Optional[float]:
        text = self.read_text(image, psm=7, whitelist="0123456789.")
        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", text)
        if not match:
            return None
        return float(match.group(1))

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

    def _read_rank(self, image: np.ndarray) -> Optional[str]:
        rank_text = self.read_text(image, psm=8, whitelist="A23456789TJQK10")
        cleaned = rank_text.upper().replace(" ", "")
        if not cleaned:
            return None

        if cleaned.startswith("10"):
            return "T"

        token = cleaned[0]
        return _RANK_MAP.get(token)

    @staticmethod
    def _read_suit(image: np.ndarray) -> Optional[str]:
        h, w = image.shape[:2]
        center = image[h // 3 : (2 * h) // 3, w // 4 : (3 * w) // 4]
        hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)

        hue = hsv[:, :, 0]
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]

        colorful = sat > 45
        if np.count_nonzero(colorful) < 20:
            if float(val.mean()) < 90:
                return "s"
            return None

        hue_mean = float(hue[colorful].mean())
        val_mean = float(val[colorful].mean())

        if hue_mean < 10 or hue_mean > 165:
            return "h"
        if 35 <= hue_mean < 90:
            return "c"
        if 90 <= hue_mean < 150:
            return "d"
        if val_mean < 100:
            return "s"
        return "s"


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
