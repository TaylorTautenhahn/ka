# Block Blast Bot

This is a best-effort local solver for the visible three-piece Block Blast turn. It reads the board from the screen, searches all legal placement orders for the current three pieces, and can drag the mouse through the iPhone Mirroring window to place them.

It does not guarantee a win every game. The script only sees the current board and the three visible pieces, so future randomness is still unknown.

## Requirements

- Run the mirrored iPhone on the main display.
- Grant Screen Recording permission to the terminal app you use to launch the script.
- Grant Accessibility permission so macOS allows the drag helper to move the mouse.
- Use the repo virtualenv because it already has `pillow` and `numpy`.

## Calibrate

```bash
./.venv/bin/python scripts/block_blast_bot.py --calibrate
```

The calibration flow captures:

- the mirrored iPhone screen content bounds
- the 8x8 board interior bounds
- the center of the left, middle, and right piece slots

It saves the result to `output/block_blast_calibration.json`.

## Dry Run

Start here so you can confirm the detected moves before any drag happens:

```bash
./.venv/bin/python scripts/block_blast_bot.py --dry-run --debug-image output/block_blast_debug.png
```

## Assist Mode

Use this when you want the engine to recommend the best sequence but you want to place the pieces yourself:

```bash
./.venv/bin/python scripts/block_blast_bot.py --assist
```

It will:

- print the detected tray pieces
- print the recommended order and covered cells
- show a step-by-step terminal board preview
- save an annotated image to `output/block_blast_assist.png` unless you pass `--debug-image`

## Play One Turn

```bash
./.venv/bin/python scripts/block_blast_bot.py --play-once --countdown 3
```

## Loop Mode

```bash
./.venv/bin/python scripts/block_blast_bot.py --loop --countdown 3
```

## Notes

- If piece detection is slightly off, open `output/block_blast_calibration.json` and tweak the `tuning` values.
- The Swift helper is compiled automatically to `tmp/block_blast_mouse`.
- If the Mirroring window moves or changes scale a lot, run calibration again.
