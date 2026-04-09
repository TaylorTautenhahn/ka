#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import block_blast_bot as bot


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "output" / "block_blast_verify"


def save_slot_masks(image: Image.Image, config: dict, output_dir: Path) -> list[Path]:
    paths: list[Path] = []
    for slot_index, box in enumerate(bot.slot_crop_boxes(image, config), start=1):
        crop = image.crop(box).convert("RGB")
        mask = bot.piece_foreground_mask(np.array(crop))
        mask_image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
        path = output_dir / f"slot_{slot_index}_mask.png"
        mask_image.save(path)
        paths.append(path)
    return paths


def render_board_overlay(image: Image.Image, config: dict, board: list[list[bool]], output_path: Path) -> None:
    capture_region = bot.rect_from_dict(config["capture_region"])
    board_rect = bot.rect_from_dict(config["board_rect"])
    draw = ImageDraw.Draw(image)
    scale_x, scale_y = bot.capture_scale(image, capture_region)
    board_rel = bot.Rect(
        left=(board_rect.left - capture_region.left) * scale_x,
        top=(board_rect.top - capture_region.top) * scale_y,
        right=(board_rect.right - capture_region.left) * scale_x,
        bottom=(board_rect.bottom - capture_region.top) * scale_y,
    )
    draw.rectangle([board_rel.left, board_rel.top, board_rel.right, board_rel.bottom], outline="cyan", width=3)
    cell_w = board_rel.width / bot.BOARD_SIZE
    cell_h = board_rel.height / bot.BOARD_SIZE
    for row in range(bot.BOARD_SIZE):
        for col in range(bot.BOARD_SIZE):
            x0 = board_rel.left + (col * cell_w)
            y0 = board_rel.top + (row * cell_h)
            x1 = x0 + cell_w
            y1 = y0 + cell_h
            draw.rectangle([x0, y0, x1, y1], outline=(80, 180, 255), width=1)
            if board[row][col]:
                draw.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], outline="red", width=2)
            draw.text((x0 + 3, y0 + 2), f"{row + 1},{col + 1}", fill="white")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def report_payload(config: dict, board_debug: bot.BoardDetectionDebug, pieces: list[bot.Piece], result: bot.SearchResult) -> dict:
    return {
        "source": bot.describe_capture_source(config),
        "board": [list(row) for row in board_debug.board],
        "board_text": bot.board_to_coordinate_text(bot.board_from_signature(board_debug.board)),
        "thresholds": board_debug.thresholds,
        "occupied_scores": [list(row) for row in board_debug.occupied_scores],
        "pieces": [
            {
                "slot_index": piece.slot_index,
                "cells": [list(cell) for cell in piece.cells],
                "size": piece.size,
                "width": piece.width,
                "height": piece.height,
            }
            for piece in pieces
        ],
        "moves": [
            {
                "slot_index": move.slot_index,
                "anchor_row": move.anchor_row,
                "anchor_col": move.anchor_col,
                "cleared_lines": move.cleared_lines,
                "cells": [[row, col] for row, col in bot.move_cells(move, pieces[move.piece_index])],
            }
            for move in result.moves
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Block Blast board and tray-piece detection on a live capture or screenshot.")
    parser.add_argument("--config", default=str(bot.DEFAULT_CONFIG_PATH), help="Path to the calibration JSON file.")
    parser.add_argument("--image", help="Analyze a saved screenshot instead of capturing live.")
    parser.add_argument("--no-auto-window", action="store_true", help="Disable automatic window-based calibration and use the saved JSON only.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory to write verification artifacts into.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.image:
        image = Image.open(Path(args.image).expanduser()).convert("RGB")
        base_tuning = bot.load_config(config_path).get("tuning", {}) if config_path.exists() else {}
        saved_slot_ratios = None
        if config_path.exists():
            try:
                _, saved_slot_ratios = bot.ratios_from_config(bot.load_config(config_path))
            except Exception:
                saved_slot_ratios = None
        config = bot.build_image_runtime_config(image, base_tuning, saved_slot_ratios)
    else:
        config = bot.resolve_runtime_config(config_path, allow_auto_window=not args.no_auto_window)
        capture_region = bot.rect_from_dict(config["capture_region"])
        image = bot.capture_image(capture_region)
        bot.ensure_block_blast_visible(image, config)

    raw_path = output_dir / "raw_capture.png"
    image.save(raw_path)

    board_rect = bot.rect_from_dict(config["board_rect"])
    capture_region = bot.rect_from_dict(config["capture_region"])
    empty_threshold = float(config.get("tuning", {}).get("empty_cell_threshold", 28.0))
    board_debug = bot.detect_board_debug(image, board_rect, capture_region, empty_threshold)
    board = bot.board_from_signature(board_debug.board)
    pieces = bot.detect_pieces(image, config)
    result = bot.search_best_sequence(board, pieces, board_rect)

    overlay_path = output_dir / "detection_overlay.png"
    bot.render_debug(image.copy(), capture_region, board_rect, board, pieces, result, overlay_path)

    board_overlay_path = output_dir / "board_overlay.png"
    render_board_overlay(image.copy(), config, board, board_overlay_path)

    slot_crop_paths = bot.save_slot_crops(image, config, output_dir, "slot")
    slot_mask_paths = save_slot_masks(image, config, output_dir)

    assist_text = bot.assist_text(board, pieces, result, config)
    assist_path = output_dir / "assist.txt"
    bot.write_text_file(assist_path, assist_text)

    report = report_payload(config, board_debug, pieces, result)
    report_path = output_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(assist_text)
    print("\nArtifacts:")
    print(raw_path)
    print(overlay_path)
    print(board_overlay_path)
    for path in slot_crop_paths:
        print(path)
    for path in slot_mask_paths:
        print(path)
    print(assist_path)
    print(report_path)


if __name__ == "__main__":
    main()
