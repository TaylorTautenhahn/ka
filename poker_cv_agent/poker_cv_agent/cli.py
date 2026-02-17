from __future__ import annotations

import argparse
import shutil
import sys

def _assert_tesseract_available() -> None:
    try:
        import pytesseract
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing python dependency `pytesseract`. Install project deps first: `pip install -r requirements.txt`."
        ) from exc

    if shutil.which("tesseract") is None:
        raise RuntimeError(
            "tesseract binary not found. Install it first (macOS: `brew install tesseract`)."
        )
    # Raises if pytesseract cannot communicate with the binary.
    _ = pytesseract.get_tesseract_version()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="poker_cv_agent",
        description="Vision-driven poker simulator bot",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    calibrate_parser = subparsers.add_parser("calibrate", help="Select on-screen ROIs")
    calibrate_parser.add_argument("--output", default="config.yaml", help="Output config path")
    calibrate_parser.add_argument("--monitor", type=int, default=1, help="Monitor index from mss")

    run_parser = subparsers.add_parser("run", help="Run bot loop")
    run_parser.add_argument("--config", required=True, help="Config YAML path")
    run_parser.add_argument(
        "--live",
        action="store_true",
        help="Enable real clicks. Default is dry-run only.",
    )
    run_parser.add_argument(
        "--debug-ui",
        action="store_true",
        help="Show live OpenCV overlay with ROI boxes, OCR text, and decisions.",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        _assert_tesseract_available()

        if args.command == "calibrate":
            from .calibrate import run_calibration

            run_calibration(output_path=args.output, monitor_index=args.monitor)
            return

        if args.command == "run":
            from .config import load_config
            from .runner import run_bot

            config = load_config(args.config)
            run_bot(config=config, dry_run=(not args.live), debug_ui=args.debug_ui)
            return

        parser.error("Unknown command")

    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
