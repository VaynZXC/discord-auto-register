#!/usr/bin/env python3
"""Готовит данные для обучения детектора (instruction/body/tile/...)."""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional


TRAIN_DIR_NAME = "train"
VAL_DIR_NAME = "val"


def load_annotations(json_path: Path) -> List[Dict]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    anns = data.get("annotations", [])
    result = []
    ball_count_before = 0
    target_count_before = 0
    ball_count_after = 0
    target_count_after = 0
    
    for ann in anns:
        bbox = ann.get("bbox")
        label = ann.get("label")
        
        if label == "ball":
            ball_count_before += 1
        elif label == "target_ball":
            target_count_before += 1
            
        if not bbox or label is None:
            continue
        if label not in {"instruction", "body", "tile", "ball", "target_ball", 
                         "bear", "fried_chicken", "letter", "target_letter", "main_letter"}:
            continue
            
        result.append({
            "bbox": [int(v) for v in bbox],
            "category": label,
            "origin": ann.get("origin", "manual"),
        })
        
        if label == "ball":
            ball_count_after += 1
        elif label == "target_ball":
            target_count_after += 1
    
    # Отладка для ball файлов
    if ball_count_before > 0 or target_count_before > 0:
        print(
            f"  DEBUG {json_path.name}: balls {ball_count_before}->{ball_count_after}, "
            f"target_balls {target_count_before}->{target_count_after}"
        )
    
    return result


def build_dataset(dataset_dir: Path, output_path: Path, val_split: float = 0.0) -> None:
    train_records: List[Dict] = []
    val_records: List[Dict] = []

    json_files = sorted(dataset_dir.rglob("*_structure.json"))
    print(f"Найдено {len(json_files)} JSON файлов")
    
    for json_path in json_files:
        base_name = json_path.stem.replace("_structure", "")
        image_path = json_path.with_name(base_name + ".png")
        if not image_path.exists():
            print(f"Пропуск: нет изображения для {json_path.name}")
            continue
        annotations = load_annotations(json_path)
        if not annotations:
            print(f"Пропуск: нет аннотаций в {json_path.name}")
            continue
        
        # Отладка: показываем что нашли
        ball_count = sum(1 for ann in annotations if ann.get("category") == "ball")
        target_count = sum(1 for ann in annotations if ann.get("category") == "target_ball")
        if ball_count > 0 or target_count > 0:
            print(
                f"OK {json_path.name}: {len(annotations)} annotations, "
                f"balls={ball_count}, target_balls={target_count}"
            )

        record = {
            "image": str(image_path.resolve()),  # Используем абсолютный путь
            "annotations": annotations,
        }

        split = _infer_split(dataset_dir, json_path)
        if split == VAL_DIR_NAME:
            val_records.append(record)
        else:
            train_records.append(record)

    if not val_records and val_split and 0.0 < val_split < 1.0 and len(train_records) > 1:
        split_idx = int(len(train_records) * (1.0 - val_split))
        auto_val = train_records[split_idx:]
        train_records = train_records[:split_idx]
        val_records.extend(auto_val)

    output = {"train": train_records}
    if val_records:
        output["val"] = val_records

    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved dataset: {output_path} (train={len(train_records)}, val={len(val_records)})")


def _infer_split(dataset_root: Path, json_path: Path) -> Optional[str]:
    try:
        rel = json_path.relative_to(dataset_root)
    except ValueError:
        return None
    parts = rel.parts
    if not parts:
        return None
    if parts[0] == TRAIN_DIR_NAME:
        return TRAIN_DIR_NAME
    if parts[0] == VAL_DIR_NAME:
        return VAL_DIR_NAME
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Собрать JSON для обучения структуры")
    parser.add_argument("--dataset", default="dataset/screens", help="Папка со скринами и *_structure.json")
    parser.add_argument("--output", default="training/structure_dataset.json", help="Куда сохранить итоговый json")
    parser.add_argument("--val-split", type=float, default=0.1, help="Доля валидации (0..1)")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    output_path = Path(args.output)
    build_dataset(dataset_dir, output_path, val_split=args.val_split)


if __name__ == "__main__":
    main()

