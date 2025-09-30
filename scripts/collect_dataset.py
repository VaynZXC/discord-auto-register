#!/usr/bin/env python3
"""Циклический сборщик капч для датасета."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright


def save_screenshot(source: Path, dataset_root: Path, tag: str | None) -> Path:
    dataset_root.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    name_parts = [timestamp]
    if tag:
        name_parts.append(tag)
    filename = "_".join(name_parts) + ".png"
    target = dataset_root / filename
    # избегаем перезаписи
    counter = 1
    while target.exists():
        target = dataset_root / f"{'_'.join(name_parts)}_{counter:03d}.png"
        counter += 1
    target.write_bytes(source.read_bytes())
    return target


def open_challenge(page, analysis_dir: Path, wait_after_open: float) -> tuple[bool, Path | None]:
    screenshot_path = analysis_dir / "captcha.png"
    try:
        page.goto("http://127.0.0.1:5000", wait_until="load")
        page.wait_for_selector('iframe[title*="флажком"]', timeout=10000)
        checkbox_frame = page.frame_locator('iframe[title*="флажком"]')
        checkbox_frame.locator('#checkbox').click()

        try:
            page.wait_for_selector('iframe[title*="содержание испытания"]', timeout=20000)
        except Exception:
            page.wait_for_selector('iframe[src*="hcaptcha.com"]', timeout=20000)

        time.sleep(wait_after_open)

        challenge_frame = page.frame_locator('iframe[title*="содержание испытания"]')
        try:
            challenge_frame.locator('.challenge-container').screenshot(path=str(screenshot_path))
        except Exception:
            challenge_frame.locator('body').screenshot(path=str(screenshot_path))

        return True, screenshot_path
    except Exception as exc:
        print(f"❌ Не удалось открыть капчу: {exc}")
        return False, None


def collect_loop(playwright: Playwright, count: int, delay: float, wait_after_open: float, headless: bool, dataset_root: Path, tag: str | None) -> None:
    browser = playwright.chromium.launch(headless=headless, slow_mo=0)
    page = browser.new_page()

    analysis_dir = Path("analysis")
    analysis_dir.mkdir(exist_ok=True)
    solutions_dir = Path("solutions")
    solutions_dir.mkdir(exist_ok=True)

    iteration = 0
    try:
        while count <= 0 or iteration < count:
            iteration += 1
            print(f"\n=== Итерация {iteration} ===")

            ok, screenshot_path = open_challenge(page, analysis_dir, wait_after_open)
            if not ok or screenshot_path is None:
                continue

            try:
                stored_path = save_screenshot(screenshot_path, dataset_root, tag)
                print(f"✅ Скрин сохранен: {stored_path}")
            except Exception as save_error:
                print(f"⚠️ Ошибка сохранения: {save_error}")

            time.sleep(delay)
            page.reload(wait_until="load")
    finally:
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Автоматический сборщик капч для датасета")
    parser.add_argument("--count", type=int, default=0, help="Сколько примеров собрать (0 = бесконечно)")
    parser.add_argument("--delay", type=float, default=1.5, help="Пауза между итерациями (сек)")
    parser.add_argument("--wait-after-open", type=float, default=3.0, help="Ожидание после открытия задания (сек)")
    parser.add_argument("--dataset", default="dataset/screens", help="Папка для сохранения скринов")
    parser.add_argument("--tag", default=None, help="Дополнительная метка (например, тип сборщика)")
    parser.add_argument("--headless", action="store_true", help="Запуск браузера в headless режиме")
    args = parser.parse_args()

    dataset_root = Path(args.dataset)

    with sync_playwright() as playwright:
        collect_loop(
            playwright=playwright,
            count=args.count,
            delay=args.delay,
            wait_after_open=args.wait_after_open,
            headless=args.headless,
            dataset_root=dataset_root,
            tag=args.tag,
        )


if __name__ == "__main__":
    main()

