from __future__ import annotations

import numpy as np
from mss import mss

from .models import ROI


class ScreenCapture:
    def __init__(self, monitor_index: int) -> None:
        self._sct = mss()
        self._monitor_index = monitor_index
        self._monitors = self._sct.monitors
        if monitor_index < 1 or monitor_index >= len(self._monitors):
            raise ValueError(
                f"Invalid monitor index {monitor_index}. Available monitors: 1..{len(self._monitors) - 1}"
            )

    def grab_monitor(self) -> np.ndarray:
        monitor = self._monitors[self._monitor_index]
        shot = self._sct.grab(monitor)
        frame = np.array(shot, dtype=np.uint8)
        return frame[:, :, :3]

    @property
    def monitor_bbox(self) -> dict[str, int]:
        monitor = self._monitors[self._monitor_index]
        return {
            "left": int(monitor["left"]),
            "top": int(monitor["top"]),
            "width": int(monitor["width"]),
            "height": int(monitor["height"]),
        }

    def grab_roi(self, roi: ROI) -> np.ndarray:
        shot = self._sct.grab(roi.as_mss_bbox())
        frame = np.array(shot, dtype=np.uint8)
        return frame[:, :, :3]
