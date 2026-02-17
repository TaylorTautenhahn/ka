from __future__ import annotations

import time

from .capture import ScreenCapture
from .config import BotConfig
from .controller import InputController
from .strategy import StrategyConfig, StrategyEngine
from .vision import VisionEngine


def run_bot(config: BotConfig, dry_run: bool, debug_ui: bool = False) -> None:
    capture = ScreenCapture(monitor_index=config.monitor_index)
    vision = VisionEngine(config=config)
    strategy = StrategyEngine(
        StrategyConfig(
            opponents=config.opponents,
            monte_carlo_iterations=config.monte_carlo_iterations,
        )
    )
    controller = InputController(dry_run=dry_run, click_jitter_pixels=config.click_jitter_pixels)

    cv2 = None
    window_name = ""
    render_debug_frame = None
    if debug_ui:
        import cv2 as cv2_module

        from .debug_ui import WINDOW_NAME, render_debug_frame as render_debug

        cv2 = cv2_module
        window_name = WINDOW_NAME
        render_debug_frame = render_debug
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 950, 1600)

    print(
        "Starting poker_cv_agent "
        f"(dry_run={dry_run}, monitor={config.monitor_index}, opponents={config.opponents}, debug_ui={debug_ui})"
    )

    last_action_key = ""
    last_action_at = 0.0

    try:
        while True:
            started = time.time()
            vision_debug = None

            if debug_ui:
                state, vision_debug = vision.capture_state_with_debug(capture)
            else:
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

            if debug_ui and cv2 and render_debug_frame and vision_debug is not None:
                frame = capture.grab_monitor()
                debug_frame = render_debug_frame(
                    frame=frame,
                    config=config,
                    monitor_bbox=capture.monitor_bbox,
                    state=state,
                    decision=decision,
                    vision_debug=vision_debug,
                    dry_run=dry_run,
                )
                cv2.imshow(window_name, debug_frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    print("Debug window exit requested")
                    break
                if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
                    print("Debug window closed")
                    break

            loop_elapsed = time.time() - started
            sleep_for = max(0.05, config.loop_interval_seconds - loop_elapsed)
            time.sleep(sleep_for)

    except KeyboardInterrupt:
        print("Stopped by user")
    finally:
        if debug_ui and cv2:
            cv2.destroyAllWindows()
