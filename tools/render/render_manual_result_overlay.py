#!/usr/bin/env python3
"""Визуализация результатов manual_solver/manual_live: оригинал + отмеченные тайлы."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Any

import cv2
import numpy as np


def load_result(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def draw_overlay(image, result: Dict[str, Any]) -> np.ndarray:
    annotated = image.copy()
    for tile in result.get("tiles", []):
        bbox = tile.get("bbox", [])
        if len(bbox) != 4:
            continue
        x, y, w, h = map(int, bbox)
        match = bool(tile.get("match"))
        verdict = tile.get("verdict", {})
        reason = verdict.get("reason")
        color = (0, 255, 0) if match else (0, 0, 255)
        cv2.rectangle(annotated, (x, y), (x + w, y + h), color, 3)
        label = f"#{tile.get('id') or '?'} {'OK' if match else 'NO'}"
        cv2.putText(annotated, label, (x + 5, y + h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        if reason:
            wrapped = reason[:80]
            cv2.putText(annotated, wrapped, (x + 5, max(15, y - 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
    return annotated


def build_canvas(original: np.ndarray, overlay: np.ndarray) -> np.ndarray:
    h = max(original.shape[0], overlay.shape[0])
    canvas = np.zeros((h, original.shape[1] + overlay.shape[1] + 10, 3), dtype=np.uint8)
    canvas[: original.shape[0], : original.shape[1]] = original
    canvas[: overlay.shape[0], original.shape[1] + 10 : original.shape[1] + 10 + overlay.shape[1]] = overlay
    cv2.putText(canvas, "ORIGINAL", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(canvas, "AI VIEW", (original.shape[1] + 20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    return canvas


def main() -> None:
    parser = argparse.ArgumentParser(description="Показать оригинал и разметку тайлов")
    parser.add_argument("image", help="Путь к исходному скрину капчи")
    parser.add_argument("result", help="JSON файл с результатами (manual_solver/manual_live)")
    parser.add_argument("--output", help="Если указан, сохранить изображение на диск")
    parser.add_argument("--show", action="store_true", help="Показать окно с результатом")
    args = parser.parse_args()

    image_path = Path(args.image)
    result_path = Path(args.result)

    image = cv2.imread(str(image_path))
    if image is None:
        raise FileNotFoundError(image_path)

    result = load_result(result_path)
    overlay = draw_overlay(image, result)
    canvas = build_canvas(image, overlay)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), canvas)
        print(f"✅ Overlay сохранен: {out_path}")

    if args.show or not args.output:
        cv2.imshow("manual_overlay", canvas)
        print("Нажмите любую клавишу для закрытия окна...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
