#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any

import cv2

from src.gpt import GPTAnalyzer


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def ensure_gpt_result(image_path: Path, gpt_json: Optional[Path]) -> Dict[str, Any]:
    if gpt_json and gpt_json.exists():
        return load_json(gpt_json)

    analyzer = GPTAnalyzer()
    result = analyzer.analyze_captcha(str(image_path))
    if not result or "error" in result:
        raise RuntimeError("GPT-4 не вернул результат")
    return result


def draw_structure(img, structure_data: Dict[str, Any]) -> None:
    h, w = img.shape[:2]
    color_instruction = (0, 165, 255)
    color_body = (255, 255, 0)

    instr = structure_data.get("instruction_area")
    if instr:
        x, y, width, height = instr
        cv2.rectangle(img, (x, y), (x + width, y + height), color_instruction, 2)
        cv2.putText(img, "instruction", (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_instruction, 2)

    body = structure_data.get("body_area")
    if body:
        x, y, width, height = body
        cv2.rectangle(img, (x, y), (x + width, y + height), color_body, 2)
        cv2.putText(img, "body", (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color_body, 2)

    for region in structure_data.get("regions", []):
        kind = region.get("kind")
        bbox = region.get("bbox")
        if bbox:
            x, y, width, height = bbox
            cv2.rectangle(img, (x, y), (x + width, y + height), (0, 255, 255), 2)
            cv2.putText(img, kind or "region", (x + 5, y + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        for cell in region.get("cells", []):
            cb = cell.get("bbox")
            if cb:
                cx, cy, cw, ch = cb
                cv2.rectangle(img, (cx, cy), (cx + cw, cy + ch), (255, 0, 255), 1)


def render_overlay(image_path: Path, gpt_result: Dict[str, Any], structure: Dict[str, Any], output_path: Path) -> None:
    img = cv2.imread(str(image_path))
    if img is None:
        raise FileNotFoundError(image_path)

    draw_structure(img, structure)

    interactive = gpt_result.get("interactive_elements", [])
    targets = set(gpt_result.get("recommendation", {}).get("target_ids", []))

    for element in interactive:
        eid = element.get("id")
        center = element.get("center") or {}
        bbox = element.get("bbox") or {}
        cx = int(center.get("x", bbox.get("x", 0) + bbox.get("width", 0) / 2))
        cy = int(center.get("y", bbox.get("y", 0) + bbox.get("height", 0) / 2))
        x = int(bbox.get("x", cx - 25))
        y = int(bbox.get("y", cy - 25))
        width = int(bbox.get("width", 50))
        height = int(bbox.get("height", 50))

        base_color = (0, 0, 255)
        if eid in targets:
            base_color = (0, 255, 0)
        cv2.rectangle(img, (x, y), (x + width, y + height), base_color, 2)
        cv2.circle(img, (cx, cy), 6, base_color, -1)
        label = f"#{eid}"
        desc = element.get("content")
        if desc:
            label += f" {desc}"
        cv2.putText(img, label, (x, max(15, y - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, base_color, 1, cv2.LINE_AA)

    cv2.putText(img, gpt_result.get("instruction", ""), (10, min(img.shape[0] - 10, 30)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), img)
    print(f"✅ Overlay сохранен: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Визуализировать, что видит GPT-4 на конкретном скрине")
    parser.add_argument("image", help="Путь к изображению")
    parser.add_argument("--gpt-json", help="Путь к JSON с ответом GPT (если не указан, будет вызван анализ)")
    parser.add_argument("--structure-json", help="JSON со структурой (instruction/body/grid)")
    parser.add_argument("--output", default="analysis/manual_overlay.png", help="Куда сохранить overlay")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    gpt_result = ensure_gpt_result(image_path, Path(args.gpt_json) if args.gpt_json else None)
    structure = load_json(Path(args.structure_json)) if args.structure_json else {}

    render_overlay(image_path, gpt_result, structure, Path(args.output))


if __name__ == "__main__":
    main()
