# Poker CV Agent (Standalone)

This is a separate project folder for a **simulated poker app you own/control**.

It captures your mirrored phone screen, reads cards/buttons with computer vision, picks an action using Monte Carlo equity, and optionally clicks the mapped button.

## What it does
- Screen capture (`mss`)
- OCR for cards/buttons/pot (`pytesseract`)
- Suit inference from card color theme in your UI
- Decision engine (`treys` equity simulation)
- Auto-click control (`pyautogui`)
- Dry-run mode by default

## Limits
- No-limit poker has no guaranteed “perfect strategy” in this setup.
- This bot is a best-effort strategy approximation and depends on OCR quality.
- You must calibrate ROIs for your screen layout.

## Setup
```bash
cd /Users/taylortautenhahn/Development/Codex/poker_cv_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install tesseract
```

## Calibrate
1. Put your mirrored phone window in its normal position.
2. Run:
```bash
python -m poker_cv_agent calibrate --monitor 1 --output config.yaml
```
3. Draw boxes for each prompt and confirm with Enter/Space.

## Run (safe dry-run first)
```bash
python -m poker_cv_agent run --config config.yaml
```

This prints chosen actions and click coordinates without clicking.

## Run with real clicks
```bash
python -m poker_cv_agent run --config config.yaml --live
```

## Run with live debug overlay
```bash
python -m poker_cv_agent run --config config.yaml --debug-ui
```

The debug window shows:
- ROI boxes for hero cards, board cards, buttons, and pot
- OCR text per button and pot
- Parsed card values and card-read notes
- Available actions
- Decision + equity + reason

Press `q` (or `Esc`) in the debug window to stop.

## Quick tuning
Edit `config.yaml`:
- `opponents`: estimated active opponents
- `monte_carlo_iterations`: higher = slower but more stable equity
- `loop_interval_seconds`: reaction speed
- `action_cooldown_seconds`: anti-double-click safety
- `click_jitter_pixels`: naturalized click offset

## Project structure
- `poker_cv_agent/cli.py`: command entrypoint
- `poker_cv_agent/calibrate.py`: ROI calibration UI
- `poker_cv_agent/vision.py`: OCR + parsing
- `poker_cv_agent/strategy.py`: equity + action policy
- `poker_cv_agent/runner.py`: event loop
- `poker_cv_agent/controller.py`: mouse automation
