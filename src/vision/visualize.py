#!/usr/bin/env python3
"""Утилиты визуализации структуры капчи."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .detector import StructureInfo, Region, GridCell

COLORS = {
    "instruction": (255, 149, 0),    # как в labeler
    "body": (90, 200, 255),
    "tile": (80, 230, 110),
    "grid": (80, 230, 110),
    "cell": (80, 230, 110),
    "ball": (80, 80, 255),
    "tile_disabled": (140, 200, 150),
    "text": (255, 255, 255),
}


def _draw_bbox(image, bbox, color, thickness=2):
    x, y, w, h = [int(v) for v in bbox]
    cv2.rectangle(image, (x, y), (x + w, y + h), color, thickness)


def _put_label(image, text, origin, color):
    x, y = map(int, origin)
    cv2.putText(
        image,
        text,
        (x, max(15, y)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
        cv2.LINE_AA,
    )


def render_structure_overlay(
    image_path: str | Path,
    structure: StructureInfo,
    overlay_path: str | Path,
    combined_path: Optional[str | Path] = None,
) -> tuple[Path, Optional[Path]]:
    """Сохраняет изображение с разметкой структуры (инструкция, тело, тайлы)."""

    image_path = Path(image_path)
    overlay_path = Path(overlay_path)
    combined_path = Path(combined_path) if combined_path else None

    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)

    annotated = img.copy()

    if structure.instruction_area:
        _draw_bbox(annotated, structure.instruction_area, COLORS["instruction"], 2)
        _put_label(annotated, "instruction", (structure.instruction_area[0] + 5, structure.instruction_area[1] + 25), COLORS["instruction"])

    if structure.body_area:
        _draw_bbox(annotated, structure.body_area, COLORS["body"], 2)
        _put_label(annotated, "body", (structure.body_area[0] + 5, structure.body_area[1] + 25), COLORS["body"])

    has_balls = bool(structure.balls)

    for region in structure.regions:
        color = COLORS.get(region.kind, COLORS["grid"])
        if region.kind != "tile":
            _draw_bbox(annotated, region.bbox, color, 2)
            label_text = region.kind
            if region.meta and "source" in region.meta:
                label_text = f"{label_text} ({region.meta['source']})"
            _put_label(annotated, label_text, (region.bbox[0] + 5, region.bbox[1] + 25), color)
        elif region.kind == "tile" and not has_balls:
            _draw_bbox(annotated, region.bbox, color, 2)
            tile_label = "tile"
            if region.meta and "source" in region.meta:
                tile_label = f"{tile_label} ({region.meta['source']})"
            _put_label(annotated, tile_label, (region.bbox[0] + 5, region.bbox[1] + 25), color)

        if region.cells:
            draw_color = COLORS["tile"] if not has_balls else COLORS["tile_disabled"]
            for cell in region.cells:
                if region.kind == "tile" and has_balls:
                    # В заданиях с мячиками не рисуем тайлы, чтобы не путать с ball
                    _draw_bbox(annotated, cell.bbox, draw_color, 1)
                    continue
                _draw_bbox(annotated, cell.bbox, draw_color, 2)
                cell_label = f"tile #{cell.id}"
                _put_label(annotated, cell_label, (cell.bbox[0] + 4, cell.bbox[1] + 18), draw_color)

    if structure.balls:
        for ball in structure.balls:
            _draw_bbox(annotated, ball.bbox, COLORS["ball"], 2)
            ball_label = f"ball #{ball.id}"
            _put_label(annotated, ball_label, (ball.bbox[0] + 4, ball.bbox[1] + 18), COLORS["ball"])

    if getattr(structure, "target_balls", None):
        for target in structure.target_balls:
            _draw_bbox(annotated, target.bbox, (0, 0, 255), 3)
            target_label = f"target #{target.id}"
            _put_label(annotated, target_label, (target.bbox[0] + 4, target.bbox[1] + 18), (0, 0, 255))

    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(overlay_path), annotated)

    combined_saved: Optional[Path] = None
    if combined_path:
        h = max(img.shape[0], annotated.shape[0])
        w = img.shape[1] + annotated.shape[1] + 10
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        canvas[: img.shape[0], : img.shape[1]] = img
        canvas[: annotated.shape[0], img.shape[1] + 10 : img.shape[1] + 10 + annotated.shape[1]] = annotated
        _put_label(canvas, "ORIGINAL", (10, 30), COLORS["text"])
        _put_label(canvas, "STRUCTURE", (img.shape[1] + 20, 30), COLORS["text"])
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(combined_path), canvas)
        combined_saved = combined_path

    return overlay_path, combined_saved
