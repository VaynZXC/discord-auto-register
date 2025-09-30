#!/usr/bin/env python3
"""Решение hCaptcha на лету через классификацию тайлов GPT-мини."""

from __future__ import annotations

import sys
from pathlib import Path as _Path

ROOT = _Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import cv2
from openai import OpenAI
from playwright.sync_api import Playwright, sync_playwright, TimeoutError

from src.gpt import GPTAnalyzer
from src.tools.manual_model import ask_model_for_tiles
from src.vision import detect_structure, render_structure_overlay, Region


@dataclass
class Tile:
    id: int
    bbox: Tuple[int, int, int, int]


def build_tiles_from_structure(structure) -> List[Tile]:
    for region in structure.regions:
        if getattr(region, "kind", None) in {"grid", "tile"} and region.cells:
            return [Tile(id=cell.id, bbox=tuple(map(int, cell.bbox))) for cell in region.cells]
    # fallback: равномерно делим body 3x3
    body = structure.body_area
    x, y, width, height = body
    cell_w = width / 3
    cell_h = height / 3
    tiles: List[Tile] = []
    idx = 0
    for row in range(3):
        for col in range(3):
            cx = int(x + col * cell_w)
            cy = int(y + row * cell_h)
            tiles.append(Tile(id=idx, bbox=(cx, cy, int(cell_w), int(cell_h))))
            idx += 1
    return tiles


def click_tiles(page, challenge_frame, tiles: List[Tile], matches: Dict[int, bool], screenshot_path: Path) -> None:
    from PIL import Image

    try:
        canvas_info = challenge_frame.locator('canvas').bounding_box()
    except Exception as e:
        print(f"⚠️ Не удалось получить bounding box canvas: {e}")
        return

    try:
        container_info = challenge_frame.locator('.challenge-container').bounding_box()
    except Exception as e:
        print(f"⚠️ Не удалось получить bounding box контейнера: {e}")
        return

    img = Image.open(screenshot_path)
    img_width, img_height = img.size

    scale_x = canvas_info['width'] / img_width
    scale_y = canvas_info['height'] / img_height
    container_x = container_info['x']
    container_y = container_info['y']
    offset_x = canvas_info['x'] - container_x
    offset_y = canvas_info['y'] - container_y

    seen_centers: set[Tuple[int, int]] = set()
    clicks_performed = 0

    for tile in tiles:
        if not matches.get(tile.id):
            continue
        x, y, w, h = tile.bbox
        center_x = x + w / 2
        center_y = y + h / 2
        center_key = (int(center_x), int(center_y))
        if center_key in seen_centers:
            continue
        seen_centers.add(center_key)

        if clicks_performed >= 9:
            break

        rel_x = center_x * scale_x + offset_x
        rel_y = center_y * scale_y + offset_y
        abs_x = container_x + rel_x
        abs_y = container_y + rel_y

        try:
            print(f"🖱️ Кликаем tile #{tile.id} -> ({abs_x:.1f}, {abs_y:.1f})")
            page.mouse.move(abs_x - 10, abs_y - 10, steps=8)
            page.mouse.move(abs_x, abs_y, steps=4)
            page.mouse.click(abs_x, abs_y, delay=120)
            time.sleep(0.3)
            clicks_performed += 1
        except Exception as click_err:
            print(f"⚠️ Ошибка клика по плитке #{tile.id}: {click_err}")


def solve_once(playwright: Playwright, dataset_dir: Path | None = None) -> None:
    browser = playwright.chromium.launch(headless=False, slow_mo=800)
    page = browser.new_page()

    try:
        page.goto("http://127.0.0.1:5000", wait_until="load")
        page.wait_for_selector('iframe[title*="флажком"]', timeout=10000)
        checkbox_frame = page.frame_locator('iframe[title*="флажком"]')
        checkbox_frame.locator('#checkbox').click()

        page.wait_for_selector('iframe[title*="содержание испытания"]', timeout=20000)
        challenge_frame = page.frame_locator('iframe[title*="содержание испытания"]')

        time.sleep(3)

        analysis_dir = Path("analysis/manual_live")
        analysis_dir.mkdir(parents=True, exist_ok=True)

        max_attempts = 5
        attempt = 1
        solved = False
        last_screenshot: Optional[Path] = None

        while attempt <= max_attempts:
            print(f"\n=== Попытка {attempt}/{max_attempts} ===")
            screenshot_path = analysis_dir / "captcha.png"
            challenge_frame.locator('.challenge-container').screenshot(path=str(screenshot_path))
            print(f"📸 Сохранен скриншот: {screenshot_path}")

            structure = detect_structure(str(screenshot_path))

            structure_overlay = analysis_dir / "structure_overlay.png"
            try:
                render_structure_overlay(
                    screenshot_path,
                    structure,
                    structure_overlay,
                )
                print(f"🖼️ Структура сохранена: {structure_overlay}")
            except Exception as overlay_err:
                print(f"⚠️ Не удалось визуализировать структуру: {overlay_err}")

            if not structure.body_area:
                raise RuntimeError("Не удалось определить область с тайлами")
            tiles = build_tiles_from_structure(structure)

            analyzer = GPTAnalyzer()
            gpt_result = analyzer.analyze_captcha(str(screenshot_path))
            if not gpt_result or "error" in gpt_result:
                raise RuntimeError("GPT-4 не вернул инструкцию")
            instruction = gpt_result.get("instruction", "")
            print(f"📝 Инструкция: {instruction}")

            client = OpenAI(api_key=analyzer.api_key)
            summary = ask_model_for_tiles(
                client,
                instruction,
                structure_overlay,
                max_tiles=3,
            )
            print(f"🤖 Ответ модели: {summary}")

            selected = {int(i) for i in summary.get("selected_ids", [])}
            matches: Dict[int, bool] = {tile.id: (tile.id in selected) for tile in tiles}

            click_tiles(page, challenge_frame, tiles, matches, screenshot_path)

            try:
                print("⏳ Ждём 5 секунд перед нажатием Continue...")
                time.sleep(5)
                continue_selector = ', '.join([
                    'button:has-text("Continue")',
                    'button:has-text("Далее")',
                    'button:has-text("Продолжить")',
                    'button.button-submit',
                    '.button-submit',
                    '[data-hcaptcha-submit-button]'
                ])
                continue_button = challenge_frame.locator(continue_selector).first
                if continue_button.count() == 0:
                    raise RuntimeError("Continue button not found")
                continue_button.click(force=True)
                print("➡️ Нажали Continue")
            except Exception as cont_err:
                print(f"⚠️ Не удалось нажать Continue: {cont_err}")

            output_json = analysis_dir / "manual_live_result.json"
            output = {
                "attempt": attempt,
                "instruction": instruction,
                "model_response": summary,
                "tiles": [
                    {
                        "id": tile.id,
                        "bbox": tile.bbox,
                        "match": matches.get(tile.id, False),
                    }
                    for tile in tiles
                ],
            }
            output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"💾 Результаты сохранены: {output_json}")

            if dataset_dir:
                dataset_dir.mkdir(parents=True, exist_ok=True)
                copy_path = dataset_dir / f"{int(time.time())}_captcha.png"
                copy_path.write_bytes(screenshot_path.read_bytes())
                print(f"📦 Сохранен снимок в датасет: {copy_path}")

            last_screenshot = screenshot_path

            try:
                challenge_frame.locator('.challenge-view').first.wait_for(state='hidden', timeout=6000)
                print("✅ Капча завершена")
                solved = True
                break
            except TimeoutError:
                print("🔁 Похоже, появился следующий уровень. Продолжаем...")
                attempt += 1
                time.sleep(2)
                continue

        if not solved:
            print("❌ Не удалось завершить капчу за отведённые попытки")

    finally:
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Решение капчи через GPT-классификацию тайлов")
    parser.add_argument("--dataset", help="Необязательная папка для сохранения скринов")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset) if args.dataset else None

    with sync_playwright() as playwright:
        solve_once(playwright, dataset_dir)


if __name__ == "__main__":
    main()
