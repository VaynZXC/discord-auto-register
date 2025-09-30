#!/usr/bin/env python3
"""Тестовый запуск GPT-анализа для произвольного скрина."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.gpt import GPTAnalyzer
from capture_gpt import execute_gpt_solution_smart
from src.vision import detect_structure


def main() -> None:
    parser = argparse.ArgumentParser(description="Проверка анализа конкретного скрина")
    parser.add_argument("image", help="Путь к изображению капчи")
    parser.add_argument("--output-dir", default="analysis/test", help="Куда сохранить результаты")
    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"📸 Анализируем изображение: {image_path}")

    analyzer = GPTAnalyzer()
    gpt_result = analyzer.analyze_captcha(str(image_path))
    if not gpt_result or "error" in gpt_result:
        print("❌ GPT-4 не вернул корректный ответ")
        return

    (output_dir / "gpt_result.json").write_text(json.dumps(gpt_result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ Результат сохранен: {output_dir / 'gpt_result.json'}")

    analyzer.save_gpt_analysis(gpt_result, str(image_path))
    overlay_path = Path("analysis/gpt_view_overlay.png")
    if overlay_path.exists():
        target_overlay = output_dir / overlay_path.name
        target_overlay.write_bytes(overlay_path.read_bytes())
        print(f"🖼️ Overlay сохранен: {target_overlay}")

    structure_info = detect_structure(str(image_path), debug_dir=str(output_dir))
    print(f"🧩 Структура: {structure_info}")


if __name__ == "__main__":
    main()

