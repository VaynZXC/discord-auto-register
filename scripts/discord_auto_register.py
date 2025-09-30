#!/usr/bin/env python3
"""Автоматическое заполнение формы регистрации Discord."""

from __future__ import annotations

import argparse
import os
import random
import string
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple

from playwright.sync_api import Page, TimeoutError, sync_playwright
from PIL import Image


@dataclass
class RegistrationData:
    email: str
    display_name: str
    username: str
    password: str
    birth_day: int
    birth_month: int
    birth_year: int


EMAIL_DOMAINS = [
    "gmail.com",
    "hotmail.com",
    "yahoo.com",
    "outlook.com",
    "yandex.ru",
    "mail.ru",
]

DISPLAY_FIRST_NAMES = [
    "Alex",
    "Maria",
    "John",
    "Anna",
    "Mike",
    "Elena",
    "David",
    "Kate",
    "Ivan",
    "Olga",
    "Victor",
    "Irina",
    "Sergey",
    "Nina",
    "Tim",
]

DISPLAY_LAST_NAMES = [
    "Smith",
    "Johnson",
    "Brown",
    "Wilson",
    "Davis",
    "Miller",
    "Anderson",
    "Taylor",
    "Petrov",
    "Sidorov",
    "Kuznetsov",
]

USERNAME_WORDS = [
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "gopher",
    "honey",
    "island",
    "jungle",
    "koala",
    "lemur",
    "meteor",
    "nebula",
    "onyx",
    "panda",
    "quartz",
    "rookie",
    "sierra",
    "tango",
    "umber",
    "velvet",
    "whale",
    "xenon",
    "yonder",
    "zephyr",
]


def generate_email() -> str:
    local_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8, 12)))
    domain = random.choice(EMAIL_DOMAINS)
    return f"{local_part}@{domain}"


def generate_display_name() -> str:
    first = random.choice(DISPLAY_FIRST_NAMES)
    if random.random() < 0.4:
        last = random.choice(DISPLAY_LAST_NAMES)
        return f"{first} {last}"
    if random.random() < 0.5:
        return f"{first}{random.randint(10, 999)}"
    return first
    

def generate_username() -> str:
    left = ''.join(random.choices(string.digits, k=4))
    word1 = random.choice(USERNAME_WORDS)
    word2 = random.choice([w for w in USERNAME_WORDS if w != word1])
    right = ''.join(random.choices(string.digits, k=4))
    return f"{left}_{word1}_{word2}_{right}"


def generate_password() -> str:
    word = random.choice(USERNAME_WORDS).capitalize()
    digits = ''.join(random.choices(string.digits, k=6))
    return f"{word}{digits}@"


MONTH_NAMES_RU = [
    "январь",
    "февраль",
    "март",
    "апрель",
    "май",
    "июнь",
    "июль",
    "август",
    "сентябрь",
    "октябрь",
    "ноябрь",
    "декабрь",
]


def generate_birth_date() -> Tuple[int, int, int]:
    current_year = datetime.now().year
    year = random.randint(current_year - 40, current_year - 18)
    month = random.randint(1, 12)
    day_limit = [31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    day = random.randint(1, day_limit)
    return day, month, year


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def build_registration_data() -> RegistrationData:
    day, month, year = generate_birth_date()
    return RegistrationData(
        email=generate_email(),
        display_name=generate_display_name(),
        username=generate_username(),
        password=generate_password(),
        birth_day=day,
        birth_month=month,
        birth_year=year,
    )


def select_dropdown_option(page: Page, label: str, option_text: str) -> None:
    trigger = page.get_by_role("button", name=label)
    trigger.wait_for(state="visible", timeout=5000)
    trigger.click()

    option = page.get_by_role("option", name=option_text)
    if option.count() == 0:
        fallback_text = option_text.capitalize()
        option = page.get_by_role("option", name=fallback_text)
    option.first.wait_for(state="visible", timeout=5000)
    option.first.click()


def fill_registration_form(page: Page, data: RegistrationData) -> bool:
    try:
        page.get_by_label("E-mail").fill(data.email)
        page.get_by_label("Отображаемое имя").fill(data.display_name)
        page.get_by_label("Имя пользователя").fill(data.username)
        page.get_by_label("Пароль").fill(data.password)

        select_dropdown_option(page, "День", str(data.birth_day))
        select_dropdown_option(page, "Месяц", MONTH_NAMES_RU[data.birth_month - 1])
        select_dropdown_option(page, "Год", str(data.birth_year))

        checkboxes = page.locator('input[type="checkbox"]')
        count = checkboxes.count()
        if count == 0:
            print("Чекбоксы не найдены")
            return False
        index = 1 if count >= 2 else 0
        checkbox = checkboxes.nth(index)
        checkbox.wait_for(state="visible", timeout=5000)
        checkbox.check(force=True)
        return True
    except Exception as exc:
        print(f"Ошибка заполнения формы: {exc}")
        return False


def submit_form(page: Page) -> bool:
    try:
        submit_button = page.get_by_role("button", name="Создать учётную запись")
        submit_button.wait_for(state="visible", timeout=5000)
        try:
            submit_button.click(timeout=10000)
        except TimeoutError:
            print("Кнопка отправки не стала активной вовремя")
            return False
        return True
    except Exception as exc:
        print(f"Ошибка отправки формы: {exc}")
        return False
        

def click_cells_on_canvas(page: Page, challenge_frame, cells, screenshot_path: Path) -> None:
    try:
        canvas_info = challenge_frame.locator('canvas').bounding_box()
    except Exception as e:
        print(f"Не удалось получить canvas: {e}")
        return

    img = Image.open(screenshot_path)
    img_width, img_height = img.size

    # Масштаб: скриншот -> canvas на странице
    scale_x = canvas_info['width'] / img_width
    scale_y = canvas_info['height'] / img_height

    for cell in cells:
        # Используем готовый центр из структуры
        if hasattr(cell, 'center') and cell.center:
            center_x, center_y = cell.center
        else:
            # Fallback: bbox формата [x, y, width, height]
            x, y, w, h = cell.bbox
            center_x = x + w / 2
            center_y = y + h / 2

        # Масштабируем и переводим в абсолютные координаты canvas
        abs_x = canvas_info['x'] + center_x * scale_x
        abs_y = canvas_info['y'] + center_y * scale_y

        try:
            print(f"Клик по #{cell.id} центр=({center_x:.1f}, {center_y:.1f}) -> страница=({abs_x:.1f}, {abs_y:.1f})")
            page.mouse.click(abs_x, abs_y, delay=100)
            time.sleep(0.3)
        except Exception as click_err:
            print(f"Ошибка клика: {click_err}")


def capture_and_analyze_captcha(page: Page, worker_id: int = 0, timeout: float = 15.0) -> bool:
    try:
        captcha_locator = page.locator('iframe[src*="hcaptcha.com"], iframe[src*="recaptcha"]')
        captcha_locator.first.wait_for(state="attached", timeout=timeout * 1000)
        time.sleep(3.0)
        
        analysis_dir = Path("analysis") / f"worker_{worker_id}"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        screenshot_path = analysis_dir / "discord_captcha.png"
        
        try:
            try:
                page.wait_for_selector('iframe[title*="содержание испытания"]', timeout=10000)
                challenge_frame = page.frame_locator('iframe[title*="содержание испытания"]')
            except Exception:
                page.wait_for_selector('iframe[src*="hcaptcha.com"]', timeout=10000)
                challenge_frame = page.frame_locator('iframe[src*="hcaptcha.com"]').first
            
            time.sleep(2.0)
            
            try:
                challenge_frame.locator('.challenge-container').screenshot(path=str(screenshot_path))
            except Exception:
                challenge_frame.locator('body').screenshot(path=str(screenshot_path))
            print(f"Скриншот капчи сохранен: {screenshot_path}")
        except Exception as screenshot_err:
            print(f"Ошибка создания скриншота: {screenshot_err}")
            return False
        
        try:
            import sys
            from pathlib import Path as P
            project_root = P(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from src.vision import detect_structure, render_structure_overlay
            from src.gpt import GPTAnalyzer
            
            structure = detect_structure(str(screenshot_path))
            
            overlay_path = analysis_dir / "discord_captcha_structure_overlay.png"
            render_structure_overlay(
                screenshot_path,
                structure,
                overlay_path,
            )
            print(f"Разметка модели сохранена: {overlay_path}")
            
            # Если обнаружены шарики и цели - решаем без GPT
            if structure.balls and structure.target_balls:
                print("Обнаружены шарики и цели - решаем без GPT")
                cells_to_click = structure.target_balls
                print(f"Кликаем target_balls: {[c.id for c in cells_to_click]}")
            else:
                # Для остальных случаев используем GPT анализатор
                analyzer = GPTAnalyzer()
                gpt_result = analyzer.analyze_captcha(str(screenshot_path))
                if not gpt_result or "error" in gpt_result:
                    print("GPT не смог проанализировать капчу")
                    return False

                instruction = gpt_result.get("instruction", "")
                action = gpt_result.get("recommendation", {}).get("action", "interact")
                target_ids_raw = gpt_result.get("recommendation", {}).get("target_ids", [])
                
                # GPT использует индексы с 0, наши ID начинаются с 1 - добавляем +1
                target_ids = [tid + 1 for tid in target_ids_raw]
                
                print(f"Инструкция: {instruction}")
                print(f"Действие: {action}")
                print(f"GPT ID (0-based): {target_ids_raw} -> Наши ID (1-based): {target_ids}")
                
                if action == "skip":
                    print("Задание на перетаскивание - пропускаем")
                    try:
                        skip_button = challenge_frame.locator('button:has-text("Пропустить"), .refresh-button').first
                        skip_button.click()
                        print("Нажали 'Пропустить'")
                    except Exception as skip_err:
                        print(f"Не удалось нажать 'Пропустить': {skip_err}")
                    return True
                
                # GPT результаты: выбираем что кликать
                if structure.target_balls:
                    cells_to_click = structure.target_balls
                    print(f"Кликаем target_balls: {[c.id for c in cells_to_click]}")
                elif structure.balls:
                    if target_ids:
                        cells_to_click = [b for b in structure.balls if b.id in target_ids]
                    else:
                        cells_to_click = structure.balls[:1]
                    print(f"Кликаем balls: {[c.id for c in cells_to_click]}")
                else:
                    if not structure.regions or not structure.regions[0].cells:
                        print("Нет тайлов для клика")
                        return False
                    tiles = structure.regions[0].cells
                    if target_ids:
                        cells_to_click = [t for t in tiles if t.id in target_ids]
                    else:
                        cells_to_click = tiles[:min(3, len(tiles))]
                    print(f"Кликаем tiles: {[c.id for c in cells_to_click]}")
            
            click_cells_on_canvas(page, challenge_frame, cells_to_click, screenshot_path)
            
            time.sleep(1.0)
            try:
                continue_button = challenge_frame.locator('.button-submit, button:has-text("Дальше")').first
                continue_button.click()
                print("Нажали 'Дальше'")
            except Exception as cont_err:
                print(f"Не удалось нажать 'Дальше': {cont_err}")
            
            # Ждем и проверяем результат
            time.sleep(2.0)
            
            # Проверяем остался ли iframe с капчей
            captcha_still_present = page.locator('iframe[src*="hcaptcha.com"], iframe[src*="recaptcha"]').count() > 0
            
            if captcha_still_present:
                print("Капча еще присутствует - следующий уровень")
                # Рекурсивно решаем следующий уровень
                return capture_and_analyze_captcha(page, worker_id, timeout)
            else:
                print("Капча исчезла - ждем 10 секунд перед проверкой")
                time.sleep(10.0)
                
                # Проверяем есть ли форма регистрации (признак ошибки)
                registration_form = page.locator('input[name="email"], input[type="email"]').count() > 0
                if registration_form:
                    print("⚠️ Форма регистрации все еще на странице - возможно ошибка")
                    return False
                else:
                    print("✅ Капча успешно пройдена!")
                    
                    # Проверяем кнопку верификации телефона
                    phone_verify_button = page.locator('button:has-text("Подтвердить по телефону")')
                    if phone_verify_button.count() > 0:
                        print("📱 Найдена кнопка верификации телефона - нажимаем")
                        try:
                            phone_verify_button.click(timeout=5000)
                            print("✅ Кнопка верификации нажата")
                        except Exception as btn_err:
                            print(f"⚠️ Не удалось нажать кнопку верификации: {btn_err}")
                    else:
                        print("ℹ️ Кнопка верификации телефона не найдена")
                    
                    return True
            
        except Exception as model_err:
            print(f"Ошибка обработки моделью: {model_err}")
            import traceback
            traceback.print_exc()
            return False
    except TimeoutError:
        print("Капча не появилась в пределах ожидания")
        return False
    except Exception as exc:
        print(f"Ошибка ожидания капчи: {exc}")
        return False


def register_account(headless: bool, wait_after_submit: float, worker_id: int = 0) -> bool:
    data = build_registration_data()
    print("\n=== New registration attempt ===")
    print(f"Email: {data.email}")
    print(f"Display name: {data.display_name}")
    print(f"Username: {data.username}")
    print(f"Dob: {data.birth_day}.{data.birth_month}.{data.birth_year}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()
        try:
            page.goto("https://discord.com/register", wait_until="load")
            time.sleep(1.5)

            if not fill_registration_form(page, data):
                return False

            if not submit_form(page):
                return False

            if not capture_and_analyze_captcha(page, worker_id):
                return False

            time.sleep(wait_after_submit)
            return True
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Автозаполнение формы регистрации Discord")
    parser.add_argument("--count", type=int, default=1, help="Количество попыток регистрации")
    parser.add_argument("--delay", type=float, default=3.0, help="Пауза между попытками (сек)")
    parser.add_argument("--wait-after-submit", type=float, default=5.0, help="Пауза после отправки формы (сек)")
    parser.add_argument("--headless", action="store_true", help="Запуск браузера в режиме headless")
    args = parser.parse_args()

    successes = 0
    for attempt in range(1, args.count + 1):
        success = register_account(
            headless=args.headless,
            wait_after_submit=args.wait_after_submit,
            worker_id=attempt
        )
        if success:
            successes += 1
            print(f"Регистрация #{attempt} завершена")
        else:
            print(f"Регистрация #{attempt} завершилась с ошибкой")

        if attempt < args.count:
            time.sleep(args.delay)

    print(f"\nГотово. Успешных регистраций: {successes} из {args.count}")


if __name__ == "__main__":
    main()