#!/usr/bin/env python3
"""Решение капчи на основе ручных аннотаций тайлов."""

from __future__ import annotations

import sys
from pathlib import Path as _Path

ROOT = _Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import cv2

from src.gpt import GPTAnalyzer
from src.tools.manual_model import ask_model_for_tiles as mm_ask_model
from openai import OpenAI


@dataclass
class TileAnnotation:
    id: int
    bbox: List[int]


def load_structure(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data


def extract_tiles(structure: Dict[str, Any]) -> List[TileAnnotation]:
    tiles = []
    counter = 0
    for ann in structure.get("annotations", []):
        if ann.get("label") == "tile":
            tiles.append(TileAnnotation(id=counter, bbox=[int(v) for v in ann.get("bbox", [])]))
            counter += 1
    return tiles


def encode_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def create_numbered_overlay(image_path: Path, tiles: List[TileAnnotation], output_path: Path) -> Path:
    return mm_create_overlay(image_path, tiles, output_path)


def ask_model_for_tiles(client: OpenAI, instruction: str, raw_image: Path, numbered_image: Path, tile_count: int) -> Dict[str, Any]:
    return mm_ask_model(client, instruction, raw_image, numbered_image, tile_count)


def save_overlay(image_path: Path, tiles: List[TileAnnotation], verdicts: Dict[int, Dict[str, Any]], output_path: Path) -> None:
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)
    for tile in tiles:
        x, y, w, h = tile.bbox
        verdict = verdicts.get(tile.id, {})
        match = verdict.get("match", False)
        color = (0, 255, 0) if match else (0, 0, 255)
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 3)
        label = f"#{tile.id} {'OK' if match else 'NO'}"
        cv2.putText(img, label, (x + 5, y + h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), img)


def solve_image(
    image_path: Path,
    structure_path: Path,
    output_path: Optional[Path] = None,
    overlay_path: Optional[Path] = None,
    *,
    verbose: bool = True,
) -> Dict[str, Any]:
    image_path = Path(image_path)
    structure_path = Path(structure_path)

    if verbose:
        print(f"📄 Используем структуру: {structure_path}")

    if not image_path.exists():
        raise FileNotFoundError(image_path)
    structure = load_structure(structure_path)
    tiles = extract_tiles(structure)
    if not tiles:
        raise RuntimeError("В структуре нет аннотаций 'tile'")

    analyzer = GPTAnalyzer()
    gpt_result = analyzer.analyze_captcha(str(image_path))
    if not gpt_result or "error" in gpt_result:
        raise RuntimeError("GPT-4 не смог прочитать инструкцию")
    instruction = gpt_result.get("instruction", "")
    if verbose:
        print(f"📝 Инструкция: {instruction}")

    client = OpenAI(api_key=analyzer.api_key)
    overlay_tmp = Path("analysis/manual_solver_overlay.png")
    save_overlay(image_path, tiles, {tile.id: False for tile in tiles}, overlay_tmp)
    summary = mm_ask_model(client, instruction, overlay_tmp, max_tiles=3)
    selected_ids = set(int(i) for i in summary.get("selected_ids", []))

    img = cv2.imread(str(image_path))
    verdicts: Dict[int, Dict[str, Any]] = {}
    matches: Dict[int, bool] = {}
    for tile in tiles:
        match = tile.id in selected_ids
        matches[tile.id] = match
        verdicts[tile.id] = {
            "match": match,
            "reason": summary.get("reason", ""),
        }
        if verbose:
            print(f"Tile #{tile.id}: {verdicts[tile.id]}")

    data = {
        "image": str(image_path),
        "structure": str(structure_path),
        "instruction": instruction,
        "model_response": summary,
        "tiles": [
            {
                "id": tile.id,
                "bbox": tile.bbox,
                "match": matches.get(tile.id, False),
                "verdict": verdicts.get(tile.id),
            }
            for tile in tiles
        ],
    }

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if verbose:
            print(f"✅ Результат сохранен: {output_path}")

    if overlay_path is not None:
        overlay_path = Path(overlay_path)
        save_overlay(image_path, tiles, verdicts, overlay_path)
        if verbose:
            print(f"🖼️ Overlay сохранен: {overlay_path}")

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Решить капчу по ручным аннотациям тайлов")
    parser.add_argument("image", help="Путь к изображению капчи")
    parser.add_argument("structure", help="JSON с ручными аннотациями (tile/instruction/body)")
    parser.add_argument("--output", default="analysis/manual_solver/result.json", help="Куда сохранить результат")
    parser.add_argument("--overlay", default="analysis/manual_solver/overlay.png", help="Куда сохранить overlay")
    parser.add_argument("--quiet", action="store_true", help="Не выводить подробные логи")
    args = parser.parse_args()

    solve_image(
        Path(args.image),
        Path(args.structure),
        output_path=Path(args.output) if args.output else None,
        overlay_path=Path(args.overlay) if args.overlay else None,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
