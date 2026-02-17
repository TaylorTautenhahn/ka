from __future__ import annotations

import time

from .capture import ScreenCapture
from .config import BotConfig
from .controller import InputController
from .strategy import StrategyConfig, StrategyEngine
from .vision import VisionEngine


def run_bot(config: BotConfig, dry_run: bool) -> None:
    capture = ScreenCapture(monitor_index=config.monitor_index)
    vision = VisionEngine(config=config)
    strategy = StrategyEngine(
        StrategyConfig(
            opponents=config.opponents,
            monte_carlo_iterations=config.monte_carlo_iterations,
        )
    )
    controller = InputController(dry_run=dry_run, click_jitter_pixels=config.click_jitter_pixels)

    print(
        "Starting poker_cv_agent "
        f"(dry_run={dry_run}, monitor={config.monitor_index}, opponents={config.opponents})"
    )

    last_action_key = ""
    last_action_at = 0.0

    try:
        while True:
            started = time.time()
            state = vision.capture_state(capture)
            decision = strategy.choose_action(state)

            if decision and decision.action in state.available_actions:
                action_key = f"{state.fingerprint()}|{decision.action}"
                elapsed_since_last = started - last_action_at

                if action_key != last_action_key or elapsed_since_last >= config.action_cooldown_seconds:
                    roi = config.buttons[decision.action]
                    print(
                        f"Action={decision.action.upper()} "
                        f"equity={decision.equity if decision.equity is not None else 'n/a'} "
                        f"reason={decision.reason}"
                    )
                    controller.click_roi(roi)
                    last_action_key = action_key
                    last_action_at = time.time()

            loop_elapsed = time.time() - started
            sleep_for = max(0.05, config.loop_interval_seconds - loop_elapsed)
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        print("Stopped by user")
