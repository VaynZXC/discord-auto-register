#!/usr/bin/env python3
"""Прогоняет manual_solver по всем размеченным скринам датасета."""

from __future__ import annotations

import sys
from pathlib import Path as _Path

ROOT = _Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
from pathlib import Path
from typing import Iterable

from manual_solver import solve_image


def iter_pairs(dataset_dir: Path) -> Iterable[tuple[Path, Path]]:
    for json_path in sorted(dataset_dir.glob("*_structure.json")):
        image_path = json_path.with_name(json_path.stem.replace("_structure", "") + ".png")
        if image_path.exists():
            yield image_path, json_path


def main() -> None:
    dataset_dir = Path("dataset/screens")
    output_dir = Path("analysis/manual_solver_batch")
    output_dir.mkdir(parents=True, exist_ok=True)

    summary = []
    for image_path, structure_path in iter_pairs(dataset_dir):
        name = image_path.stem
        print(f"\n=== {name} ===")
        try:
            result = solve_image(
                image_path,
                structure_path,
                output_path=output_dir / f"{name}.json",
                overlay_path=output_dir / f"{name}_overlay.png",
            )
            summary.append({
                "image": str(image_path),
                "structure": str(structure_path),
                "matches": sum(1 for tile in result["tiles"] if tile["match"]),
                "tiles": len(result["tiles"]),
                "instruction": result.get("instruction"),
            })
        except Exception as err:
            print(f"❌ Ошибка: {err}")
            summary.append({
                "image": str(image_path),
                "structure": str(structure_path),
                "error": str(err),
            })

    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📄 Итоги сохранены: {output_dir / 'summary.json'}")


if __name__ == "__main__":
    main()

