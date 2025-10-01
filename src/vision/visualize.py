#!/usr/bin/env python3
"""Утилиты визуализации структуры капчи."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from .detector import StructureInfo, Region, GridCell

COLORS = {
    "instruction": (255, 149, 0),
    "body": (90, 200, 255),
    "tile": (80, 230, 110),
    "grid": (80, 230, 110),
    "cell": (80, 230, 110),
    "ball": (80, 80, 255),
    "tile_disabled": (140, 200, 150),
    "text": (255, 255, 255),
    "target_ball": (0, 0, 255),
    "bear": (42, 82, 139),
    "fried_chicken": (0, 165, 255),
    "letter": (128, 128, 128),
    "target_letter": (255, 128, 0),
    "main_letter": (255, 0, 255),
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
    has_drag_task = bool(structure.bears and structure.fried_chickens)  # Есть задание на drag
    has_letters = bool(
        getattr(structure, "letters", None) or 
        getattr(structure, "target_letters", None) or 
        getattr(structure, "main_letters", None)
    )  # Есть задание с буквами
    
    # НЕ рисуем tiles если есть специфичные объекты
    skip_tiles = has_balls or has_drag_task or has_letters

    for region in structure.regions:
        color = COLORS.get(region.kind, COLORS["grid"])
        if region.kind != "tile":
            _draw_bbox(annotated, region.bbox, color, 2)
            label_text = region.kind
            if region.meta and "source" in region.meta:
                label_text = f"{label_text} ({region.meta['source']})"
            _put_label(annotated, label_text, (region.bbox[0] + 5, region.bbox[1] + 25), color)
        elif region.kind == "tile" and not skip_tiles:
            _draw_bbox(annotated, region.bbox, color, 2)
            tile_label = "tile"
            if region.meta and "source" in region.meta:
                tile_label = f"{tile_label} ({region.meta['source']})"
            _put_label(annotated, tile_label, (region.bbox[0] + 5, region.bbox[1] + 25), color)

        if region.cells:
            # НЕ рисуем тайлы если есть специфичные объекты
            draw_color = COLORS["tile"] if not skip_tiles else COLORS["tile_disabled"]
            for cell in region.cells:
                if region.kind == "tile" and skip_tiles:
                    # Не рисуем детали tiles если есть специфичные объекты
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
            _draw_bbox(annotated, target.bbox, COLORS["target_ball"], 3)
            target_label = f"target #{target.id}"
            _put_label(annotated, target_label, (target.bbox[0] + 4, target.bbox[1] + 18), COLORS["target_ball"])
    
    # Отрисовка новых объектов
    if getattr(structure, "bears", None):
        for obj in structure.bears:
            _draw_bbox(annotated, obj.bbox, COLORS["bear"], 2)
            _put_label(annotated, f"bear #{obj.id}", (obj.bbox[0] + 4, obj.bbox[1] + 18), COLORS["bear"])
    
    if getattr(structure, "fried_chickens", None):
        for obj in structure.fried_chickens:
            _draw_bbox(annotated, obj.bbox, COLORS["fried_chicken"], 2)
            _put_label(annotated, f"chicken #{obj.id}", (obj.bbox[0] + 4, obj.bbox[1] + 18), COLORS["fried_chicken"])
    
    if getattr(structure, "letters", None):
        for obj in structure.letters:
            _draw_bbox(annotated, obj.bbox, COLORS["letter"], 2)
            _put_label(annotated, f"L#{obj.id}", (obj.bbox[0] + 4, obj.bbox[1] + 18), COLORS["letter"])
    
    if getattr(structure, "target_letters", None):
        for obj in structure.target_letters:
            _draw_bbox(annotated, obj.bbox, COLORS["target_letter"], 3)
            _put_label(annotated, f"target_L#{obj.id}", (obj.bbox[0] + 4, obj.bbox[1] + 18), COLORS["target_letter"])
    
    if getattr(structure, "main_letters", None):
        for obj in structure.main_letters:
            _draw_bbox(annotated, obj.bbox, COLORS["main_letter"], 3)
            _put_label(annotated, f"main_L#{obj.id}", (obj.bbox[0] + 4, obj.bbox[1] + 18), COLORS["main_letter"])

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
