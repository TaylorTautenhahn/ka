from __future__ import annotations

import random
import time

import pyautogui

from .models import ROI


class InputController:
    def __init__(self, dry_run: bool, click_jitter_pixels: int) -> None:
        self.dry_run = dry_run
        self.click_jitter_pixels = max(0, click_jitter_pixels)
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.08

    def click_roi(self, roi: ROI) -> None:
        x, y = roi.center()
        if self.click_jitter_pixels:
            x += random.randint(-self.click_jitter_pixels, self.click_jitter_pixels)
            y += random.randint(-self.click_jitter_pixels, self.click_jitter_pixels)

        if self.dry_run:
            print(f"[DRY-RUN] click ({x}, {y})")
            return

        pyautogui.moveTo(x, y, duration=random.uniform(0.04, 0.14))
        pyautogui.click(button="left")
        time.sleep(random.uniform(0.04, 0.12))
