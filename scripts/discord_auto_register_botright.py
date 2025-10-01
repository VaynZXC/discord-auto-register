#!/usr/bin/env python3
"""Discord Auto Register - Botright Edition with Custom AI Captcha Solver."""

from __future__ import annotations

import argparse
import asyncio
import random
import string
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Tuple


@dataclass
class RegistrationData:
    email: str
    display_name: str
    username: str
    password: str
    birth_day: int
    birth_month: int
    birth_year: int
    phone: str = None


EMAIL_DOMAINS = [
    "gmail.com", "hotmail.com", "yahoo.com", "outlook.com", 
    "yandex.ru", "mail.ru",
]

DISPLAY_FIRST_NAMES = [
    "Alex", "Maria", "John", "Anna", "Mike", "Elena", "David", 
    "Kate", "Ivan", "Olga", "Victor", "Irina", "Sergey", "Nina", "Tim",
]

DISPLAY_LAST_NAMES = [
    "Smith", "Johnson", "Brown", "Wilson", "Davis", "Miller", 
    "Anderson", "Taylor", "Petrov", "Sidorov", "Kuznetsov",
]

USERNAME_WORDS = [
    "alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "gopher",
    "honey", "island", "jungle", "koala", "lemur", "meteor", "nebula",
    "onyx", "panda", "quartz", "rookie", "sierra", "tango", "umber",
    "velvet", "whale", "xenon", "yonder", "zephyr",
]

MONTH_NAMES_EN = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def load_emails_from_file() -> list[str]:
    """Загружает почты из файла mails.txt"""
    mail_file = Path("mails.txt")
    if mail_file.exists():
        with open(mail_file, "r", encoding="utf-8") as f:
            emails = [line.strip() for line in f if line.strip()]
        return emails
    return []


def generate_email(used_emails: set[str] = None) -> str:
    """Генерирует или берет email из файла"""
    if used_emails is None:
        used_emails = set()
    
    available_emails = load_emails_from_file()
    if available_emails:
        unused = [e for e in available_emails if e not in used_emails]
        if unused:
            email = random.choice(unused)
            print(f"Email from file: {email}")
            return email
        else:
            print("All emails used, generating random")
    
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


def generate_birth_date() -> Tuple[int, int, int]:
    current_year = datetime.now().year
    year = random.randint(current_year - 40, current_year - 18)
    month = random.randint(1, 12)
    day_limit = [31, 29 if _is_leap_year(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    day = random.randint(1, day_limit)
    return day, month, year


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def build_registration_data(used_emails: set[str] = None) -> RegistrationData:
    day, month, year = generate_birth_date()
    return RegistrationData(
        email=generate_email(used_emails),
        display_name=generate_display_name(),
        username=generate_username(),
        password=generate_password(),
        birth_day=day,
        birth_month=month,
        birth_year=year,
    )


async def select_dropdown_option(page, label: str, option_text: str) -> None:
    """Выбор опции из dropdown - оптимизированные задержки."""
    print(f"    {label} = {option_text}")
    
    # Открываем dropdown
    trigger = page.get_by_text(label, exact=True).first
    await trigger.click()
    
    # Пауза для открытия меню
    await asyncio.sleep(1.0)
    
    # Проверяем открылось ли меню
    popout_count = await page.locator('div.popout__3f413:visible').count()
    
    if popout_count == 0:
        # Retry если не открылось
        await trigger.click(force=True)
        await asyncio.sleep(1.0)
    
    # Ищем нужную опцию по ТОЧНОМУ тексту
    options = page.locator('div.popout__3f413:visible div[role="option"]')
    options_count = await options.count()
    
    target_option = None
    for i in range(options_count):
        opt = options.nth(i)
        text = await opt.inner_text()
        if text.strip() == str(option_text):
            target_option = opt
            break
    
    if not target_option:
        print(f"    [FAIL] '{option_text}' not found")
        return
    
    # Скроллим к элементу
    await target_option.scroll_into_view_if_needed()
    
    # КРИТИЧЕСКАЯ ПАУЗА перед кликом (чтобы скролл завершился)
    await asyncio.sleep(1.0)
    
    # Кликаем
    try:
        await target_option.click(force=True)
    except:
        await target_option.evaluate("el => el.click()")
    
    print(f"    [OK] {label} selected")


async def fill_registration_form(page, data: RegistrationData) -> bool:
    """Заполняет форму регистрации (async) - English version."""
    try:
        print("Starting form fill...")
        
        # Ждем полной загрузки формы
        print("  Waiting for email field...")
        await page.wait_for_selector('input[name="email"]', state="visible")
        print("  [OK] Form loaded")
        
        # Fields - English labels
        print("  Filling Email...")
        await page.get_by_label("Email").fill(data.email)
        
        print("  Filling Display Name...")
        await page.get_by_label("Display Name").fill(data.display_name)
        
        print("  Filling Username...")
        await page.get_by_label("Username").fill(data.username)
        
        print("  Filling Password...")
        await page.get_by_label("Password").fill(data.password)
        
        print("  [OK] All fields filled")

        # Birthday - порядок: MONTH -> DAY -> YEAR
        print("  Selecting birthday...")
        print("    Step 1: Month")
        await select_dropdown_option(page, "Month", MONTH_NAMES_EN[data.birth_month - 1])
        
        print("    Step 2: Day")
        await select_dropdown_option(page, "Day", str(data.birth_day))
        
        print("    Step 3: Year")
        await select_dropdown_option(page, "Year", str(data.birth_year))
        
        print("  [OK] Birthday selected")

        # Checkbox logic
        print("  Looking for checkboxes...")
        checkboxes = page.locator('input[type="checkbox"]')
        count = await checkboxes.count()
        print(f"  Found {count} checkboxes")
        
        if count == 0:
            print("  [FAIL] No checkboxes found")
            return False
        
        # 1 checkbox -> index 0, 2+ -> index 1
        index = 0 if count == 1 else 1
        print(f"  Checking checkbox at index {index}...")
        checkbox = checkboxes.nth(index)
        await checkbox.wait_for(state="visible")
        await checkbox.check(force=True)
        print("  [OK] Checkbox checked")
        
        print("[OK] Form filled successfully")
        return True
        
    except Exception as exc:
        print(f"[FAIL] Form error: {exc}")
        import traceback
        traceback.print_exc()
        return False


async def submit_form(page) -> bool:
    """Отправка формы (async) - только по тексту."""
    try:
        print("Looking for submit button...")
        # Ищем ТОЛЬКО по тексту "Create Account"
        submit_button = page.get_by_text("Create Account", exact=True).first
        await submit_button.wait_for(state="visible")
        print("Submit button found, clicking...")
        await submit_button.click()
        print("[OK] Form submitted")
        return True
    except Exception as exc:
        print(f"Submit error: {exc}")
        return False


async def solve_captcha_with_custom_ai(page, worker_id: int = 0, skip_checkbox: bool = False) -> bool:
    """
    Решает капчу используя вашу AI модель (GPT + Vision).
    Копия логики из оригинального скрипта с поддержкой чекбокса.
    
    Args:
        page: Page объект
        worker_id: ID воркера
        skip_checkbox: Пропустить проверку чекбокса (для следующих уровней)
    
    Returns:
        True если капча решена
    """
    try:
        from pathlib import Path as P
        from PIL import Image
        import sys
        
        project_root = P(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from src.vision import detect_structure, render_structure_overlay
        from src.gpt import GPTAnalyzer
        
        print()
        print("=" * 70)
        print("SOLVING WITH CUSTOM AI (GPT + Vision)")
        print("=" * 70)
        
        # Ждем появления капчи
        await asyncio.sleep(2.0)
        
        # ОБРАБОТКА ЧЕКБОКСА (если не пропускаем)
        if not skip_checkbox:
            print("Checking for hCaptcha checkbox...")
            
            max_checkbox_attempts = 5
            for checkbox_attempt in range(max_checkbox_attempts):
                # Проверяем есть ли уже видимое задание
                challenge_iframe = page.locator('iframe[src*="frame=challenge"]')
                challenge_visible = False
                
                if await challenge_iframe.count() > 0:
                    try:
                        challenge_visible = await challenge_iframe.first.is_visible()
                    except:
                        pass
                
                if challenge_visible:
                    print("[OK] Challenge already visible - skipping checkbox")
                    break
                
                # Проверяем чекбокс
                checkbox_iframe = page.locator('iframe[src*="frame=checkbox"]')
                has_checkbox = await checkbox_iframe.count() > 0
                
                if has_checkbox:
                    print(f"[OK] Checkbox found - clicking (attempt {checkbox_attempt + 1})")
                    try:
                        # Получаем frame и кликаем на чекбокс
                        checkbox_frame = page.frame_locator('iframe[src*="frame=checkbox"]').first
                        
                        # Пробуем разные селекторы
                        checkbox_selectors = [
                            '#checkbox',
                            '.check',
                            '[role="checkbox"]',
                            'div[class*="check"]',
                        ]
                        
                        clicked = False
                        for selector in checkbox_selectors:
                            if await checkbox_frame.locator(selector).count() > 0:
                                await checkbox_frame.locator(selector).click(timeout=5000)
                                clicked = True
                                break
                        
                        if not clicked:
                            # Кликаем по центру iframe
                            print("   Clicking center of checkbox iframe")
                            await checkbox_frame.locator('body').click(timeout=5000)
                        
                        print("[OK] Checkbox clicked, waiting for result...")
                        await asyncio.sleep(4.0)
                        
                        # Проверяем - появилось ли задание или капча прошла
                        challenge_iframe_visible = page.locator('iframe[src*="frame=challenge"]')
                        
                        if await challenge_iframe_visible.count() > 0:
                            try:
                                is_visible = await challenge_iframe_visible.first.is_visible()
                                if is_visible:
                                    print("[OK] Challenge appeared - proceeding to solve")
                                    break
                            except:
                                pass
                        
                        # Проверяем - исчез ли чекбокс (капча прошла автоматически)
                        checkbox_still_there = await page.locator('iframe[src*="frame=checkbox"]').count() > 0
                        
                        if not checkbox_still_there:
                            print("[OK] Checkbox disappeared - captcha passed automatically!")
                            return True
                        
                        # Чекбокс все еще на месте - пробуем еще раз
                        print("   Checkbox still visible, retrying...")
                        await asyncio.sleep(5.0)
                        continue
                        
                    except Exception as checkbox_err:
                        print(f"[WARN] Checkbox click error: {checkbox_err}")
                        await asyncio.sleep(1.0)
                        
                        # Проверяем появилось ли задание
                        if await page.locator('iframe[src*="frame=challenge"]').count() > 0:
                            try:
                                if await page.locator('iframe[src*="frame=challenge"]').first.is_visible():
                                    print("   Challenge already appeared - continuing")
                                    break
                            except:
                                pass
                        await asyncio.sleep(1.0)
                        continue
                else:
                    # Нет чекбокса - проверяем задание
                    challenge_iframe = page.locator('iframe[src*="frame=challenge"]')
                    if await challenge_iframe.count() > 0:
                        print("[OK] Challenge detected without checkbox - proceeding")
                        break
                    else:
                        print("   Neither checkbox nor challenge found")
                        if checkbox_attempt < max_checkbox_attempts - 1:
                            await asyncio.sleep(2.0)
                            continue
                        else:
                            break
            
            # Финальная проверка - прошла ли капча автоматически
            final_check_challenge = page.locator('iframe[src*="frame=challenge"]')
            final_check_checkbox = page.locator('iframe[src*="frame=checkbox"]')
            
            if await final_check_challenge.count() == 0 and await final_check_checkbox.count() == 0:
                print("[OK] Captcha passed automatically!")
                return True
            
            if await final_check_challenge.count() == 0:
                print("   No challenge found - moving on")
                return True
            
            await asyncio.sleep(1.0)
        else:
            print("   Skipping checkbox check (next level)")
        
        # Создаем директорию для анализа
        analysis_dir = P("analysis") / f"worker_{worker_id}"
        analysis_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = analysis_dir / "discord_captcha.png"
        
        # Делаем скриншот challenge
        try:
            # Пробуем найти challenge frame
            try:
                await page.wait_for_selector('iframe[src*="frame=challenge"]', timeout=10000)
                challenge_frame = page.frame_locator('iframe[src*="frame=challenge"]').first
            except:
                challenge_frame = page.frame_locator('iframe[src*="hcaptcha.com"]').first
            
            await asyncio.sleep(2.0)
            
            try:
                await challenge_frame.locator('.challenge-container').screenshot(path=str(screenshot_path))
            except:
                await challenge_frame.locator('body').screenshot(path=str(screenshot_path))
            
            print(f"Screenshot saved: {screenshot_path}")
        except Exception as e:
            print(f"Screenshot error: {e}")
            return False
        
        # Детектим структуру
        structure = detect_structure(str(screenshot_path))
        
        overlay_path = analysis_dir / "discord_captcha_structure_overlay.png"
        render_structure_overlay(screenshot_path, structure, overlay_path)
        print(f"Overlay saved: {overlay_path}")
        
        # Выводим что модель нашла
        print()
        print("Model detection results:")
        print(f"  - Bears: {len(structure.bears) if structure.bears else 0}")
        print(f"  - Fried chickens: {len(structure.fried_chickens) if structure.fried_chickens else 0}")
        print(f"  - Balls: {len(structure.balls) if structure.balls else 0}")
        print(f"  - Target balls: {len(structure.target_balls) if structure.target_balls else 0}")
        print(f"  - Letters: {len(structure.letters) if structure.letters else 0}")
        print(f"  - Target letters: {len(structure.target_letters) if structure.target_letters else 0}")
        print(f"  - Main letters: {len(structure.main_letters) if structure.main_letters else 0}")
        print(f"  - Tiles: {len(structure.regions[0].cells) if structure.regions and structure.regions[0].cells else 0}")
        print()
        
        # Определяем что кликать
        cells_to_click = None
        perform_drag = False
        drag_from = None
        drag_to = None
        
        # 1. Drag задание: медведь + курица
        if structure.bears and structure.fried_chickens:
            print("Bears + Chickens detected - DRAG task")
            drag_from = structure.fried_chickens[0]
            drag_to = structure.bears[0]
            perform_drag = True
            print(f"Will drag chicken #{drag_from.id} to bear #{drag_to.id}")
        
        # 2. Drag задание: буквы (main_letter -> target_letter)
        elif structure.main_letters and structure.target_letters:
            print("Main_letter + Target_letter detected - DRAG task")
            drag_from = structure.main_letters[0]
            drag_to = structure.target_letters[0]
            perform_drag = True
            print(f"Will drag main_letter #{drag_from.id} to target_letter #{drag_to.id}")
        
        # 3. Задание с шариками
        elif structure.balls and structure.target_balls:
            cells_to_click = structure.target_balls
            print(f"Clicking target_balls: {[c.id for c in cells_to_click]}")
        
        # 4. Только медведи
        elif structure.bears:
            cells_to_click = structure.bears
            print(f"Clicking bears: {[c.id for c in cells_to_click]}")
        
        # 5. Только курица
        elif structure.fried_chickens:
            cells_to_click = structure.fried_chickens
            print(f"Clicking fried_chickens: {[c.id for c in cells_to_click]}")
        
        # 6. Только целевые буквы
        elif structure.target_letters:
            cells_to_click = structure.target_letters
            print(f"Clicking target_letters: {[c.id for c in cells_to_click]}")
        
        # 7. Обычные буквы
        elif structure.letters:
            cells_to_click = structure.letters
            print(f"Clicking letters: {[c.id for c in cells_to_click]}")
        
        # 8. Main letters без target (одиночные буквы для клика)
        elif structure.main_letters:
            cells_to_click = structure.main_letters
            print(f"Clicking main_letters: {[c.id for c in cells_to_click]}")
        
        # 9. Используем GPT для сложных случаев (только если НЕТ букв)
        else:
            print("Using GPT analyzer...")
            analyzer = GPTAnalyzer()
            gpt_result = analyzer.analyze_captcha(str(screenshot_path))
            
            if not gpt_result or "error" in gpt_result:
                print("GPT analysis failed - using fallback tiles")
                # Fallback: кликаем первые 3 тайла
                if structure.regions and structure.regions[0].cells:
                    cells_to_click = structure.regions[0].cells[:3]
                else:
                    print("[WARN] No tiles found")
                    return False
            else:
                action = gpt_result.get("recommendation", {}).get("action", "interact")
                target_ids_raw = gpt_result.get("recommendation", {}).get("target_ids", [])
                target_ids = [tid + 1 for tid in target_ids_raw]
                
                print(f"GPT action: {action}, target_ids: {target_ids}")
                
                # SKIP логику убрали - всегда пытаемся решать
                # GPT результаты: выбираем что кликать
                if structure.target_balls:
                    cells_to_click = structure.target_balls
                    print(f"Using target_balls from structure")
                elif structure.balls:
                    if target_ids:
                        cells_to_click = [b for b in structure.balls if b.id in target_ids]
                    else:
                        cells_to_click = structure.balls[:1]
                    print(f"Using balls: {[c.id for c in cells_to_click]}")
                else:
                    if structure.regions and structure.regions[0].cells:
                        tiles = structure.regions[0].cells
                        if target_ids:
                            cells_to_click = [t for t in tiles if t.id in target_ids]
                        else:
                            cells_to_click = tiles[:min(3, len(tiles))]
                        print(f"Using tiles: {[c.id for c in cells_to_click]}")
        
        # Выполняем действие
        if perform_drag:
            # Drag and drop
            img = Image.open(screenshot_path)
            img_width, img_height = img.size
            canvas_box = await challenge_frame.locator('canvas').bounding_box()
            scale_x = canvas_box['width'] / img_width
            scale_y = canvas_box['height'] / img_height
            
            # Координаты from
            if hasattr(drag_from, 'center') and drag_from.center:
                from_x, from_y = drag_from.center
            else:
                x, y, w, h = drag_from.bbox
                from_x = x + w / 2
                from_y = y + h / 2
            
            # Координаты to
            if hasattr(drag_to, 'center') and drag_to.center:
                to_x, to_y = drag_to.center
            else:
                x, y, w, h = drag_to.bbox
                to_x = x + w / 2
                to_y = y + h / 2
            
            abs_from_x = canvas_box['x'] + from_x * scale_x
            abs_from_y = canvas_box['y'] + from_y * scale_y
            abs_to_x = canvas_box['x'] + to_x * scale_x
            abs_to_y = canvas_box['y'] + to_y * scale_y
            
            print(f"Dragging: ({abs_from_x:.1f}, {abs_from_y:.1f}) -> ({abs_to_x:.1f}, {abs_to_y:.1f})")
            await page.mouse.move(abs_from_x, abs_from_y)
            await asyncio.sleep(0.2)
            await page.mouse.down()
            await asyncio.sleep(0.3)
            await page.mouse.move(abs_to_x, abs_to_y, steps=20)
            await asyncio.sleep(0.3)
            await page.mouse.up()
            print("[OK] Drag completed")
            await asyncio.sleep(0.5)
            
        elif cells_to_click:
            # Кликаем по объектам
            img = Image.open(screenshot_path)
            img_width, img_height = img.size
            
            # Получаем canvas
            canvas_box = await challenge_frame.locator('canvas').bounding_box()
            scale_x = canvas_box['width'] / img_width
            scale_y = canvas_box['height'] / img_height
            
            for cell in cells_to_click:
                if hasattr(cell, 'center') and cell.center:
                    center_x, center_y = cell.center
                else:
                    x, y, w, h = cell.bbox
                    center_x = x + w / 2
                    center_y = y + h / 2
                
                abs_x = canvas_box['x'] + center_x * scale_x
                abs_y = canvas_box['y'] + center_y * scale_y
                
                print(f"Clicking cell #{cell.id} at ({abs_x:.1f}, {abs_y:.1f})")
                await page.mouse.click(abs_x, abs_y, delay=100)
                await asyncio.sleep(0.3)
        
        # Нажимаем кнопку Submit/Дальше
        await asyncio.sleep(1.0)
        try:
            continue_btn = challenge_frame.locator('.button-submit, button:has-text("Дальше"), button:has-text("Submit")').first
            await continue_btn.click()
            print("Clicked submit button")
        except:
            print("[WARN] Submit button not found")
        
        await asyncio.sleep(2.0)
        
        # Проверяем остался ли challenge (следующий уровень)
        challenge_still_present = await page.locator('iframe[src*="frame=challenge"]').count() > 0
        
        if challenge_still_present:
            try:
                is_visible = await page.locator('iframe[src*="frame=challenge"]').first.is_visible()
                if is_visible:
                    print("Challenge still present - next level detected")
                    await asyncio.sleep(1.0)
                    # Рекурсивно решаем следующий уровень БЕЗ проверки чекбокса
                    return await solve_captcha_with_custom_ai(page, worker_id, skip_checkbox=True)
            except:
                pass
        
        print("[OK] Captcha solved successfully!")
        return True
        
    except Exception as e:
        print(f"Custom AI error: {e}")
        import traceback
        traceback.print_exc()
        return False


# async def solve_captcha_with_botright(page, worker_id: int = 0) -> bool:
#     """DISABLED - using custom AI model instead"""
#     pass


async def verify_phone_with_sms(page, account_data: RegistrationData = None, country_code: int = 16) -> bool:
    """
    Верификация телефона через SMS-Activate (async).
    
    Args:
        page: Botright Page
        account_data: Данные аккаунта
        country_code: Код страны
    
    Returns:
        True если успешно
    """
    try:
        from src.sms import SMSActivateClient
        
        print()
        print("=" * 70)
        print("PHONE VERIFICATION VIA SMS-ACTIVATE")
        print("=" * 70)
        
        sms_client = SMSActivateClient()
        balance = sms_client.get_balance()
        print(f"Balance: ${balance:.2f}")
        
        if balance < 0.20:
            print("[FAIL] Insufficient balance (min $0.20)")
            return False
        
        print(f"Renting number (country: {country_code})...")
        activation_id, phone_number = sms_client.get_number(
            service=SMSActivateClient.SERVICE_DISCORD,
            country=country_code
        )
        
        print(f"[OK] Number: +{phone_number}")
        print(f"Activation ID: {activation_id}")
        
        if account_data:
            account_data.phone = f"+{phone_number}"
        
        # Ищем селектор страны
        print("Finding country selector...")
        await asyncio.sleep(2.0)
        
        country_selector = None
        country_selectors = [
            '.select__3f413.searchable__3f413',
            'div[class*="select"][class*="searchable"]',
            '.searchInput__3f413',
        ]
        
        for selector in country_selectors:
            if await page.locator(selector).count() > 0:
                country_selector = page.locator(selector).first
                break
        
        if country_selector:
            print("Selecting country...")
            try:
                await country_selector.click()
                await asyncio.sleep(1.5)
                
                country_name_ru = "Великобритания"
                if country_code == 0:
                    country_name_ru = "Россия"
                elif country_code == 43:
                    country_name_ru = "Германия"
                elif country_code == 16:
                    country_name_ru = "Великобритания"
                elif country_code == 83:
                    country_name_ru = "Болгария"
                elif country_code == 78:
                    country_name_ru = "Франция"
                elif country_code == 187:
                    country_name_ru = "США"
                
                popout = page.locator('.popout__3f413.searchableSelect__3f413')
                if await popout.count() > 0:
                    country_option = page.locator(f'.option__3f413:has-text("{country_name_ru}")').first
                    
                    if await country_option.count() > 0:
                        await country_option.click()
                        print(f"[OK] Country: {country_name_ru}")
                        await asyncio.sleep(1.0)
                    else:
                        # Fallback: search
                        search_input = page.locator('.searchInput__3f413, input[role="combobox"]').first
                        if await search_input.count() > 0:
                            await search_input.fill(country_name_ru)
                            await asyncio.sleep(0.5)
                            await search_input.press("Enter")
                            print(f"[OK] Country via search: {country_name_ru}")
                            await asyncio.sleep(1.0)
            except Exception as country_err:
                print(f"Country selection error: {country_err}")
        
        # Вводим номер телефона
        print("Finding phone input...")
        await asyncio.sleep(1.0)
        
        phone_input = None
        selectors = [
            'input[type="tel"]',
            'input[name="phone"]',
            'input[placeholder*="телефон" i]',
            'input[placeholder*="phone" i]',
        ]
        
        for selector in selectors:
            if await page.locator(selector).count() > 0:
                phone_input = page.locator(selector).first
                break
        
        if not phone_input:
            print("[FAIL] Phone input not found")
            sms_client.cancel_activation(activation_id)
            return False
        
        # Убираем код страны
        clean_phone = phone_number
        if phone_number.startswith('49'):
            clean_phone = phone_number[2:]
        elif phone_number.startswith('7'):
            clean_phone = phone_number[1:]
        elif phone_number.startswith('1'):
            clean_phone = phone_number[1:]
        elif phone_number.startswith('44'):
            clean_phone = phone_number[2:]
        elif phone_number.startswith('359'):
            clean_phone = phone_number[3:]
        
        print(f"Entering phone: {clean_phone}")
        await phone_input.fill(clean_phone)
        await asyncio.sleep(1.0)
        
        # Ищем кнопку отправки
        print("Finding send button...")
        await asyncio.sleep(1.0)
        
        send_button_selectors = [
            'button.primary_a22cb0:has-text("Отправить")',
            'button.primary_a22cb0.fullWidth_a22cb0',
            '.actionBarTrailing__53cea button:has-text("Отправить")',
            'button[type="button"]:has-text("Отправить")',
            'button:has-text("Send")',
        ]
        
        send_button = None
        for selector in send_button_selectors:
            if await page.locator(selector).count() > 0:
                send_button = page.locator(selector).first
                print(f"   Found button: {selector}")
                break
        
        if send_button:
            try:
                print("   Waiting for button to be enabled...")
                await send_button.wait_for(state="visible", timeout=10000)
                
                # Ждем пока кнопка станет активной
                for wait_attempt in range(10):
                    is_disabled = await send_button.get_attribute("disabled")
                    if is_disabled is None:
                        break
                    print(f"   Button still disabled, waiting... ({wait_attempt + 1}/10)")
                    await asyncio.sleep(1.0)
                
                await send_button.click(timeout=5000)
                print("[OK] Send button clicked")
                await asyncio.sleep(5.0)
            except Exception as btn_err:
                print(f"Click error: {btn_err}")
                try:
                    print("   Trying force click...")
                    await send_button.click(force=True, timeout=3000)
                    print("[OK] Force clicked")
                    await asyncio.sleep(5.0)
                except:
                    pass
        
        # Проверяем капчу после отправки номера
        print("Checking for captcha after phone submit...")
        captcha_iframe = page.locator('iframe[src*="hcaptcha.com"]')
        
        if await captcha_iframe.count() > 0:
            print("Captcha detected after phone - solving with custom AI...")
            captcha_solved = await solve_captcha_with_custom_ai(page, 0)
            
            if not captcha_solved:
                print("[FAIL] Phone verification captcha failed")
                sms_client.cancel_activation(activation_id)
                return False
            
            print("[OK] Captcha solved")
            await asyncio.sleep(2.0)
        
        # Ждем SMS код
        print("Waiting for SMS code (up to 5 minutes)...")
        sms_code = sms_client.wait_for_code(activation_id, timeout=300)
        
        if not sms_code:
            print("[FAIL] SMS code not received")
            return False
        
        print(f"[OK] Code received: {sms_code}")
        
        # Вводим код
        await asyncio.sleep(2.0)
        
        code_inputs = page.locator('input[type="text"][maxlength="1"]')
        
        if await code_inputs.count() > 0:
            print(f"Entering code by digits: {sms_code}")
            for i, digit in enumerate(sms_code):
                if i < await code_inputs.count():
                    await code_inputs.nth(i).fill(digit)
                    await asyncio.sleep(0.1)
        else:
            code_input = page.locator('input[type="text"], input[name="code"]').first
            if await code_input.count() > 0:
                print(f"Entering code: {sms_code}")
                await code_input.fill(sms_code)
        
        await asyncio.sleep(1.0)
        
        # Проверяем успешность
        error_locator = page.locator('text=/неверный|incorrect|invalid/i')
        
        if await error_locator.count() > 0:
            print("[FAIL] Invalid verification code")
            sms_client.cancel_activation(activation_id)
            return False
        
        print("[OK] Completing activation...")
        sms_client.complete_activation(activation_id)
        
        print("=" * 70)
        print()
        
        return True
        
    except Exception as e:
        print(f"Phone verification error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def register_account_botright(
    headless: bool = False,
    wait_after_submit: float = 5.0,
    worker_id: int = 0,
    used_emails: set[str] = None,
    sms_country: int = 16,
    proxy: str = None,
) -> bool:
    """
    Регистрирует аккаунт Discord используя Botright.
    
    Args:
        headless: Headless режим
        wait_after_submit: Пауза после отправки
        worker_id: ID воркера
        used_emails: Использованные email
        sms_country: Код страны для SMS
        proxy: Прокси в формате user:pass@ip:port
    
    Returns:
        True если успешно
    
    Note:
        Браузер НЕ закрывается автоматически - нажмите Ctrl+C чтобы закрыть
    """
    if used_emails is None:
        used_emails = set()
    
    import botright
    
    # Инициализация Botright
    print()
    print("=" * 70)
    print("INITIALIZING BOTRIGHT")
    print("=" * 70)
    
    botright_client = await botright.Botright(
        headless=headless,
        block_images=False,  # Нужны картинки для капчи
    )
    
    print("[OK] Botright initialized")
    
    try:
        # Создаем браузер с прокси и фиксированным viewport
        browser = await botright_client.new_browser(
            proxy=proxy,
            viewport={'width': 1280, 'height': 720},  # Компактный размер окна
        )
        
        print(f"[OK] Browser created (proxy: {'Yes' if proxy else 'No'}, viewport: 1280x720)")
        
        # Создаем страницу
        page = await browser.new_page()
        
        # Убираем дефолтные таймауты - работает сколько нужно
        page.set_default_timeout(0)  # 0 = без ограничений
        page.set_default_navigation_timeout(0)  # Для goto()
        
        print("[OK] Page ready (no timeout limits)")
        print("=" * 70)
        print()
        
        max_retries = 5
        
        for attempt in range(max_retries):
            data = build_registration_data(used_emails)
            used_emails.add(data.email)
            
            print(f"\n=== Registration attempt {attempt + 1}/{max_retries} ===")
            print(f"Email: {data.email}")
            print(f"Display name: {data.display_name}")
            print(f"Username: {data.username}")
            print(f"DOB: {data.birth_day}.{data.birth_month}.{data.birth_year}")
            print()
            
            # Переход на страницу регистрации (БЕЗ timeout - работает сколько нужно)
            print("Loading Discord registration page...")
            await page.goto("https://discord.com/register", wait_until="load")
            
            print("Waiting for page to fully load...")
            await asyncio.sleep(1.5)
            
            # Заполняем форму
            if not await fill_registration_form(page, data):
                print("Form filling failed, retrying...")
                continue
            
            # Отправляем форму
            if not await submit_form(page):
                print("Form submit failed, retrying...")
                continue
            
            # Решаем капчу с Custom AI Model
            print()
            print("Waiting for captcha...")
            await asyncio.sleep(3)
            
            captcha_solved = await solve_captcha_with_custom_ai(page, worker_id)
            
            if not captcha_solved:
                print("[FAIL] Captcha failed, retrying...")
                continue
            
            print("[OK] Captcha solved!")
            
            # Ждем и проверяем результат
            await asyncio.sleep(wait_after_submit)
            
            # Проверяем есть ли форма регистрации (признак ошибки)
            registration_form = await page.locator('input[name="email"], input[type="email"]').count() > 0
            if registration_form:
                print("Registration form still present - possible error")
                continue
            
            print("[OK] Registration successful!")
            
            # Даем время посмотреть на результат и подождать кнопку верификации
            print("Waiting 10 seconds for phone verification button to appear...")
            await asyncio.sleep(10.0)
            
            # Проверяем кнопку верификации телефона (различные варианты)
            phone_verify_selectors = [
                'button:has-text("Подтвердить по телефону")',
                'button:has-text("Verify by phone")',
                'button:has-text("Verify Phone")',
                'button:has-text("Verify")',
                'button.primaryButton',  # Основная кнопка на странице
            ]
            
            phone_verify_button = None
            for selector in phone_verify_selectors:
                if await page.locator(selector).count() > 0:
                    phone_verify_button = page.locator(selector).first
                    print(f"Found phone verification button: {selector}")
                    break
            
            if phone_verify_button:
                try:
                    await phone_verify_button.click(timeout=5000)
                    print("[OK] Phone verification clicked")
                    await asyncio.sleep(2.0)
                    
                    # Верификация телефона
                    phone_verified = await verify_phone_with_sms(page, data, sms_country)
                    
                    if phone_verified:
                        print("[OK] Phone verified successfully!")
                        
                        # Сохраняем данные
                        account_file = Path("accounts.txt")
                        with open(account_file, "a", encoding="utf-8") as f:
                            f.write(f"\n{'='*60}\n")
                            f.write(f"Email: {data.email}\n")
                            f.write(f"Display Name: {data.display_name}\n")
                            f.write(f"Username: {data.username}\n")
                            f.write(f"Password: {data.password}\n")
                            f.write(f"DOB: {data.birth_day:02d}.{data.birth_month:02d}.{data.birth_year}\n")
                            f.write(f"Phone: {data.phone if data.phone else 'N/A'}\n")
                            f.write(f"{'='*60}\n")
                        print(f"[OK] Account saved to {account_file}")
                        
                        return True
                    else:
                        print("[FAIL] Phone verification failed")
                        return False
                        
                except Exception as phone_err:
                    print(f"Phone verification error: {phone_err}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print("Phone verification button not found - checking page state...")
                
                # Показываем что видно на странице для отладки
                print("Current URL:", page.url)
                
                # Проверяем различные элементы на странице
                await asyncio.sleep(2.0)
                
                # Сохраняем данные даже без верификации
                account_file = Path("accounts.txt")
                with open(account_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"Email: {data.email}\n")
                    f.write(f"Display Name: {data.display_name}\n")
                    f.write(f"Username: {data.username}\n")
                    f.write(f"Password: {data.password}\n")
                    f.write(f"DOB: {data.birth_day:02d}.{data.birth_month:02d}.{data.birth_year}\n")
                    f.write(f"Phone: Not verified\n")
                    f.write(f"{'='*60}\n")
                print(f"[OK] Account saved to {account_file} (without phone)")
                print("[INFO] Browser will stay open - you can verify phone manually if needed")
                
                return True
        
        return False
        
    finally:
        # Всегда оставляем браузер открытым для проверки результата
        print()
        print("=" * 70)
        print("[INFO] Browser remains open - press Ctrl+C to close")
        print("=" * 70)
        try:
            # Ждем пока пользователь не закроет вручную
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[INFO] Closing browser...")
            await botright_client.close()
            print("[OK] Browser closed")


async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Discord Auto Register - Botright Edition")
    parser.add_argument("--count", type=int, default=1, help="Number of attempts")
    parser.add_argument("--delay", type=float, default=3.0, help="Delay between attempts (sec)")
    parser.add_argument("--wait-after-submit", type=float, default=5.0, help="Delay after submit (sec)")
    parser.add_argument("--headless", action="store_true", help="Headless mode (not recommended)")
    parser.add_argument("--country", type=int, default=16, help="SMS country (16=UK, 43=DE, 0=RU, 187=US)")
    parser.add_argument("--proxy", type=str, default=None, help="Proxy: user:pass@ip:port")
    parser.add_argument("--proxy-file", type=str, default=None, help="Proxy file (one per line)")
    
    args = parser.parse_args()
    
    successes = 0
    used_emails = set()
    proxy_manager = None
    
    print("=" * 70)
    print("DISCORD AUTO REGISTER - BOTRIGHT EDITION")
    print("=" * 70)
    print(f"SMS Country: code {args.country}")
    
    # Загружаем прокси
    if args.proxy_file:
        import sys
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from src.stealth import ProxyManager
        proxy_manager = ProxyManager(proxy_file=args.proxy_file)
        print(f"Loaded {proxy_manager.count_available()} proxies from file")
    
    print("=" * 70)
    print()
    
    for attempt in range(1, args.count + 1):
        # Выбираем прокси
        current_proxy = args.proxy
        if proxy_manager:
            current_proxy = proxy_manager.get_proxy()
            print(f"Using proxy: {current_proxy}")
        
        success = await register_account_botright(
            headless=args.headless,
            wait_after_submit=args.wait_after_submit,
            worker_id=attempt,
            used_emails=used_emails,
            sms_country=args.country,
            proxy=current_proxy,
        )
        
        if success:
            successes += 1
            print(f"[OK] Registration #{attempt} completed")
        else:
            print(f"[FAIL] Registration #{attempt} failed")
        
        if attempt < args.count:
            print(f"Waiting {args.delay} seconds before next attempt...")
            await asyncio.sleep(args.delay)
    
    print()
    print("=" * 70)
    print(f"[DONE] Successful: {successes}/{args.count}")
    print("=" * 70)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
