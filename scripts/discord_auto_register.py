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


def verify_phone_with_sms(page: Page, account_data: RegistrationData = None, country_code: int = 16) -> bool:
    """
    Арендует номер в SMS-Activate и проходит верификацию в Discord.
    
    Args:
        page: Playwright Page объект
        account_data: Данные регистрации (для сохранения номера)
        country_code: Код страны в SMS-Activate (43 = Германия)
    
    Returns:
        True если верификация успешна
    """
    try:
        from src.sms import SMSActivateClient
        
        print()
        print("=" * 70)
        print("📱 ВЕРИФИКАЦИЯ ТЕЛЕФОНА ЧЕРЕЗ SMS-ACTIVATE")
        print("=" * 70)
        
        # Инициализируем клиент SMS-Activate
        sms_client = SMSActivateClient()
        
        # Проверяем баланс
        balance = sms_client.get_balance()
        print(f"💰 Баланс SMS-Activate: ${balance:.2f}")
        
        if balance < 0.20:
            print("❌ Недостаточно средств на балансе SMS-Activate (мин. $0.20)")
            return False
        
        # Получаем номер
        print(f"📞 Аренда номера (страна: код {country_code})...")
        activation_id, phone_number = sms_client.get_number(
            service=SMSActivateClient.SERVICE_DISCORD,
            country=country_code
        )
        
        print(f"✅ Номер получен: +{phone_number}")
        print(f"🔑 ID активации: {activation_id}")
        
        # Сохраняем номер в данные аккаунта
        if account_data:
            account_data.phone = f"+{phone_number}"
        
        # Ищем селектор выбора страны
        print("🔍 Поиск селектора страны...")
        time.sleep(2.0)
        
        # Ищем селектор страны
        country_selector = None
        country_selectors = [
            '.select__3f413.searchable__3f413',
            'div[class*="select"][class*="searchable"]',
            '.searchInput__3f413',
        ]
        
        for selector in country_selectors:
            if page.locator(selector).count() > 0:
                country_selector = page.locator(selector).first
                break
        
        if country_selector:
            print("🌍 Выбираем страну...")
            try:
                # Кликаем на селектор чтобы открыть список
                country_selector.click()
                time.sleep(1.5)
                
                # Определяем название страны по коду (на русском, как в Discord)
                country_name_ru = "Великобритания"  # По умолчанию
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
                
                # Ищем попап со списком стран
                popout = page.locator('.popout__3f413.searchableSelect__3f413')
                if popout.count() > 0:
                    # Ищем опцию с нужной страной
                    country_option = page.locator(f'.option__3f413:has-text("{country_name_ru}")').first
                    
                    if country_option.count() > 0:
                        country_option.click()
                        print(f"✅ Выбрана страна: {country_name_ru}")
                        time.sleep(1.0)
                    else:
                        # Fallback: используем поиск
                        print(f"⚠️ Опция '{country_name_ru}' не найдена, используем поиск...")
                        search_input = page.locator('.searchInput__3f413, input[role="combobox"]').first
                        if search_input.count() > 0:
                            search_input.fill(country_name_ru)
                            time.sleep(0.5)
                            search_input.press("Enter")
                            print(f"✅ Выбрана страна через поиск: {country_name_ru}")
                            time.sleep(1.0)
                else:
                    print("⚠️ Попап выбора страны не найден")
            except Exception as country_err:
                print(f"⚠️ Ошибка выбора страны: {country_err}")
                import traceback
                traceback.print_exc()
        else:
            print("ℹ️ Селектор страны не найден, используем страну по умолчанию")
        
        # Ищем поле ввода телефона
        print("🔍 Поиск поля ввода телефона...")
        time.sleep(1.0)
        
        # Пробуем разные селекторы для поля телефона
        phone_input = None
        selectors = [
            'input[type="tel"]',
            'input[name="phone"]',
            'input[placeholder*="телефон" i]',
            'input[placeholder*="phone" i]',
        ]
        
        for selector in selectors:
            if page.locator(selector).count() > 0:
                phone_input = page.locator(selector).first
                break
        
        if not phone_input:
            print("❌ Не найдено поле ввода телефона")
            sms_client.cancel_activation(activation_id)
            return False
        
        # Убираем код страны из номера (например, +4915511286750 -> 15511286750)
        # Номер приходит в формате "4915511286750", убираем первые 2-3 цифры (код страны)
        clean_phone = phone_number
        if phone_number.startswith('49'):  # Германия
            clean_phone = phone_number[2:]  # Убираем 49
        elif phone_number.startswith('7'):  # Россия
            clean_phone = phone_number[1:]  # Убираем 7
        elif phone_number.startswith('1'):  # США/Канада
            clean_phone = phone_number[1:]  # Убираем 1
        elif phone_number.startswith('44'):  # Англия
            clean_phone = phone_number[2:]  # Убираем 44
        elif phone_number.startswith('359'):  # Болгария
            clean_phone = phone_number[3:]  # Убираем 359
        
        # Вводим номер БЕЗ кода страны
        print(f"⌨️  Ввод номера: {clean_phone} (без кода страны)")
        phone_input.fill(clean_phone)
        time.sleep(1.0)
        
        # Ищем и нажимаем кнопку "Отправить"
        print("🔍 Поиск кнопки отправки...")
        time.sleep(1.0)
        
        send_button_selectors = [
            'button.primary_a22cb0:has-text("Отправить")',
            'button.primary_a22cb0.fullWidth_a22cb0',
            '.actionBarTrailing__53cea button:has-text("Отправить")',
            'button[type="button"]:has-text("Отправить")',
            'button:has-text("Send")',
            'button:has-text("Далее")',
        ]
        
        send_button = None
        for selector in send_button_selectors:
            btn_count = page.locator(selector).count()
            if btn_count > 0:
                send_button = page.locator(selector).first
                print(f"   Найдена кнопка по селектору: {selector}")
                break
        
        if send_button:
            try:
                # Ждем пока кнопка станет активной (enabled)
                print("   Ожидание активации кнопки...")
                send_button.wait_for(state="visible", timeout=10000)
                
                # Проверяем что кнопка не disabled
                max_wait_enabled = 10
                for wait_attempt in range(max_wait_enabled):
                    is_disabled = send_button.get_attribute("disabled")
                    if is_disabled is None:
                        # Кнопка активна
                        break
                    print(f"   Кнопка еще disabled, ждем... ({wait_attempt + 1}/{max_wait_enabled})")
                    time.sleep(1.0)
                
                send_button.click(timeout=5000)
                print("✅ Нажали кнопку отправки")
                time.sleep(5.0)  # Увеличиваем до 5 секунд для капчи
            except Exception as btn_err:
                print(f"⚠️ Ошибка клика на кнопку: {btn_err}")
                # Пробуем force click
                try:
                    print("   Пробуем force click...")
                    send_button.click(force=True, timeout=3000)
                    print("✅ Нажали кнопку (force)")
                    time.sleep(5.0)
                except Exception as force_err:
                    print(f"⚠️ Force click тоже не сработал: {force_err}")
        else:
            print("⚠️ Кнопка отправки не найдена - список селекторов:")
            for sel in send_button_selectors:
                count = page.locator(sel).count()
                print(f"   {sel}: {count}")
        
        # ВАЖНО: Проверяем, не появилась ли капча после отправки номера
        print("🔍 Проверка наличия капчи после отправки номера...")
        captcha_iframe = page.locator('iframe[src*="hcaptcha.com"], iframe[src*="recaptcha"]')
        
        if captcha_iframe.count() > 0:
            print("⚠️ Обнаружена капча после ввода номера - решаем...")
            # Решаем капчу рекурсивно
            captcha_result = capture_and_analyze_captcha(page, 0, 15.0, account_data, country_code)
            
            if captcha_result == "DRAG_DETECTED":
                print("❌ Drag-задание при верификации телефона")
                sms_client.cancel_activation(activation_id)
                return False
            elif not captcha_result:
                print("❌ Не удалось решить капчу при верификации телефона")
                sms_client.cancel_activation(activation_id)
                return False
            
            print("✅ Капча решена, продолжаем верификацию")
            time.sleep(2.0)
        else:
            print("✅ Капча не обнаружена, продолжаем")
        
        # Ожидаем SMS код (до 5 минут)
        print("⏳ Ожидание SMS кода (до 5 минут)...")
        sms_code = sms_client.wait_for_code(activation_id, timeout=300)
        
        if not sms_code:
            print("❌ SMS код не получен")
            return False
        
        print(f"✅ Получен код: {sms_code}")
        
        # Вводим код
        time.sleep(2.0)
        
        # Ищем поля для ввода кода (может быть несколько полей для отдельных цифр)
        code_inputs = page.locator('input[type="text"][maxlength="1"]')
        
        if code_inputs.count() > 0:
            # Отдельные поля для каждой цифры
            print(f"⌨️  Ввод кода по цифрам: {sms_code}")
            for i, digit in enumerate(sms_code):
                if i < code_inputs.count():
                    code_inputs.nth(i).fill(digit)
                    time.sleep(0.1)
        else:
            # Одно поле для всего кода
            code_input = page.locator('input[type="text"], input[name="code"]').first
            if code_input.count() > 0:
                print(f"⌨️  Ввод кода: {sms_code}")
                code_input.fill(sms_code)
        
        time.sleep(1.0)
        
        # Проверяем успешность верификации
        # Если появилась ошибка или поле кода все еще видно - верификация не прошла
        error_locator = page.locator('text=/неверный|incorrect|invalid/i')
        
        if error_locator.count() > 0:
            print("❌ Неверный код верификации")
            sms_client.cancel_activation(activation_id)
            return False
        
        # Завершаем активацию
        print("✅ Завершение активации...")
        sms_client.complete_activation(activation_id)
        
        print("=" * 70)
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка верификации телефона: {e}")
        import traceback
        traceback.print_exc()
        return False


@dataclass
class RegistrationData:
    email: str
    display_name: str
    username: str
    password: str
    birth_day: int
    birth_month: int
    birth_year: int
    phone: str = None  # Добавляем поле для номера телефона


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
    
    # Пытаемся взять из файла
    available_emails = load_emails_from_file()
    if available_emails:
        # Фильтруем уже использованные
        unused = [e for e in available_emails if e not in used_emails]
        if unused:
            email = random.choice(unused)
            print(f"📧 Используем почту из файла: {email}")
            return email
        else:
            print("⚠️ Все почты из файла использованы, генерируем случайную")
    
    # Fallback: генерируем случайную
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
        

def drag_object_on_canvas(page: Page, challenge_frame, from_cell, to_cell, screenshot_path: Path) -> None:
    """Перетаскивает объект на canvas (например, курицу на медведя)."""
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

    # Координаты начала (from)
    if hasattr(from_cell, 'center') and from_cell.center:
        from_x, from_y = from_cell.center
    else:
        x, y, w, h = from_cell.bbox
        from_x = x + w / 2
        from_y = y + h / 2

    # Координаты конца (to)
    if hasattr(to_cell, 'center') and to_cell.center:
        to_x, to_y = to_cell.center
    else:
        x, y, w, h = to_cell.bbox
        to_x = x + w / 2
        to_y = y + h / 2

    # Масштабируем координаты
    abs_from_x = canvas_info['x'] + from_x * scale_x
    abs_from_y = canvas_info['y'] + from_y * scale_y
    abs_to_x = canvas_info['x'] + to_x * scale_x
    abs_to_y = canvas_info['y'] + to_y * scale_y

    try:
        print(f"Перетаскиваем: ({abs_from_x:.1f}, {abs_from_y:.1f}) → ({abs_to_x:.1f}, {abs_to_y:.1f})")
        # Выполняем drag
        page.mouse.move(abs_from_x, abs_from_y)
        time.sleep(0.2)
        page.mouse.down()
        time.sleep(0.3)
        page.mouse.move(abs_to_x, abs_to_y, steps=20)  # Плавное перемещение
        time.sleep(0.3)
        page.mouse.up()
        print("✅ Перетаскивание выполнено")
        time.sleep(0.5)
    except Exception as drag_err:
        print(f"Ошибка перетаскивания: {drag_err}")


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


def capture_and_analyze_captcha(page: Page, worker_id: int = 0, timeout: float = 15.0, account_data: RegistrationData = None, sms_country: int = 16, skip_checkbox: bool = False):
    try:
        captcha_locator = page.locator('iframe[src*="hcaptcha.com"], iframe[src*="recaptcha"]')
        captcha_locator.first.wait_for(state="attached", timeout=timeout * 1000)
        time.sleep(2.0)
        
        # Проверяем наличие чекбокса "Я человек" (checkbox iframe)
        # ПРОПУСКАЕМ проверку чекбокса если это следующий уровень капчи
        if not skip_checkbox:
            print("🔍 Проверка hCaptcha...")
            
            # НОВАЯ СТРАТЕГИЯ: Сначала проверяем задание, потом чекбокс
            # Чекбокс может автоматически нажаться и сразу появится задание
            max_checkbox_attempts = 5
            
            for checkbox_attempt in range(max_checkbox_attempts):
                # СНАЧАЛА проверяем есть ли уже видимое задание
                challenge_iframe = page.locator('iframe[src*="frame=challenge"]')
                challenge_visible = False
                
                if challenge_iframe.count() > 0:
                    try:
                        challenge_visible = challenge_iframe.first.is_visible()
                    except:
                        pass
                
                if challenge_visible:
                    # Задание уже есть - сразу переходим к решению
                    print("✅ Задание уже видимо - пропускаем чекбокс")
                    break
                
                # ТЕПЕРЬ проверяем чекбокс
                checkbox_iframe = page.locator('iframe[src*="frame=checkbox"]')
                has_checkbox = checkbox_iframe.count() > 0
                
                if has_checkbox:
                    # Есть чекбокс - кликаем на него
                    print(f"✅ Найден чекбокс - кликаем")
                    try:
                        # Получаем frame и кликаем на чекбокс внутри
                        checkbox_frame = page.frame_locator('iframe[src*="frame=checkbox"]').first
                        
                        # Чекбокс обычно находится в центре iframe
                        # Пробуем разные селекторы
                        checkbox_selectors = [
                            '#checkbox',
                            '.check',
                            '[role="checkbox"]',
                            'div[class*="check"]',
                        ]
                        
                        clicked = False
                        for selector in checkbox_selectors:
                            if checkbox_frame.locator(selector).count() > 0:
                                checkbox_frame.locator(selector).click(timeout=5000)
                                clicked = True
                                break
                        
                        if not clicked:
                            # Если селекторы не сработали, кликаем по центру iframe
                            print("   Кликаем по центру iframe чекбокса")
                            checkbox_frame.locator('body').click(timeout=5000)
                        
                        print("✅ Чекбокс нажат, ждем результата...")
                        time.sleep(4.0)
                        
                        # ПОСЛЕ клика проверяем - появилось ли задание или капча прошла
                        challenge_iframe_visible = page.locator('iframe[src*="frame=challenge"]')
                        
                        # Проверяем видимость задания
                        if challenge_iframe_visible.count() > 0:
                            # Проверяем что iframe видимый (не скрытый)
                            try:
                                is_visible = challenge_iframe_visible.first.is_visible()
                                if is_visible:
                                    print("⚠️ Появилось видимое задание - переходим к решению")
                                    break  # Выходим и решаем задание
                            except:
                                pass
                        
                        # Проверяем - исчез ли чекбокс (значит капча прошла)
                        checkbox_still_there = page.locator('iframe[src*="frame=checkbox"]').count() > 0
                        
                        if not checkbox_still_there:
                            print("🎉 Чекбокс исчез - капча прошла автоматически!")
                            return True
                        
                        # Чекбокс все еще на месте - пробуем еще раз
                        print("   Чекбокс все еще виден, пробуем еще раз...")
                        time.sleep(5.0)
                        continue
                        
                    except Exception as checkbox_err:
                        print(f"⚠️ Ошибка клика на чекбокс: {checkbox_err}")
                        # Не критично - возможно задание уже появилось
                        time.sleep(1.0)
                        # Проверяем появилось ли задание
                        if page.locator('iframe[src*="frame=challenge"]').count() > 0:
                            try:
                                if page.locator('iframe[src*="frame=challenge"]').first.is_visible():
                                    print("   Задание уже появилось - продолжаем")
                                    break
                            except:
                                pass
                        time.sleep(1.0)
                        continue
                else:
                    # Нет чекбокса - проверяем задание
                    challenge_iframe = page.locator('iframe[src*="frame=challenge"]')
                    if challenge_iframe.count() > 0:
                        print("⚠️ Задание обнаружено без чекбокса - переходим к решению")
                        break
                    else:
                        print("ℹ️ Ни чекбокса, ни задания не найдено")
                        if checkbox_attempt < max_checkbox_attempts - 1:
                            time.sleep(2.0)
                            continue
                        else:
                            break
            
            # Финальная проверка - прошла ли капча автоматически
            final_check_challenge = page.locator('iframe[src*="frame=challenge"]')
            final_check_checkbox = page.locator('iframe[src*="frame=checkbox"]')
            
            if final_check_challenge.count() == 0 and final_check_checkbox.count() == 0:
                print("🎉 Капча прошла автоматически!")
                return True
            
            if final_check_challenge.count() == 0:
                print("ℹ️ Нет задания капчи - переходим к следующему шагу")
                return True
            
            time.sleep(1.0)
        else:
            print("ℹ️ Пропускаем проверку чекбокса (следующий уровень капчи)")
        
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
            
            # Проверяем различные типы заданий и решаем без GPT если возможно
            cells_to_click = None
            perform_drag = False
            drag_from = None
            drag_to = None
            
            # 1. Задание с медведем и курицей - DRAG AND DROP
            if structure.bears and structure.fried_chickens:
                print("🐻🍗 Обнаружены медведь и курица - выполняем перетаскивание")
                drag_from = structure.fried_chickens[0]  # Курицу
                drag_to = structure.bears[0]  # На медведя
                perform_drag = True
                print(f"Перетаскиваем курицу #{drag_from.id} на медведя #{drag_to.id}")
            
            # 2. Задание с шариками и целями
            elif structure.balls and structure.target_balls:
                print("Обнаружены шарики и цели - решаем без GPT")
                cells_to_click = structure.target_balls
                print(f"Кликаем target_balls: {[c.id for c in cells_to_click]}")
            
            # 3. Только медведи (без курицы)
            elif structure.bears:
                print("Обнаружены медведи - решаем без GPT")
                cells_to_click = structure.bears
                print(f"Кликаем bears: {[c.id for c in cells_to_click]}")
            
            # 4. Только курица (без медведя)
            elif structure.fried_chickens:
                print("Обнаружена жареная курица - решаем без GPT")
                cells_to_click = structure.fried_chickens
                print(f"Кликаем fried_chickens: {[c.id for c in cells_to_click]}")
            
            # 5. Задание с буквами (используем GPT для определения правильных)
            elif structure.letters or structure.target_letters or structure.main_letters:
                print(f"Обнаружены буквы (letters: {len(structure.letters or [])}, target: {len(structure.target_letters or [])}, main: {len(structure.main_letters or [])})")
                # Для букв все равно используем GPT для определения правильных
                cells_to_click = None  # Переходим к GPT анализу
            
            # 6. Выполняем действие
            if perform_drag:
                # Выполняем drag-and-drop
                drag_object_on_canvas(page, challenge_frame, drag_from, drag_to, screenshot_path)
                # НЕ кликаем ничего больше - только drag
            elif cells_to_click:
                # Кликаем по найденным объектам
                click_cells_on_canvas(page, challenge_frame, cells_to_click, screenshot_path)
                # НЕ идем в GPT
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
                    print("🔄 Задание на перетаскивание - нажимаем 'Пропустить'")
                    try:
                        # Ищем кнопку "Пропустить" в разных вариантах
                        skip_selectors = [
                            '[aria-label="Пропустить задачу"]',
                            'button[title="Пропустить задачу"]',
                            '.button-submit:has-text("Пропустить")',
                            'div[role="button"]:has-text("Пропустить")',
                        ]
                        
                        skip_button = None
                        for selector in skip_selectors:
                            if challenge_frame.locator(selector).count() > 0:
                                skip_button = challenge_frame.locator(selector).first
                                break
                        
                        if skip_button:
                            skip_button.click()
                            print("✅ Нажали 'Пропустить', ждем новую капчу...")
                            time.sleep(3.0)
                            # Рекурсивно решаем следующую капчу БЕЗ проверки чекбокса
                            return capture_and_analyze_captcha(page, worker_id, timeout, account_data, sms_country, skip_checkbox=True)
                        else:
                            print("⚠️ Кнопка 'Пропустить' не найдена, обновляем страницу")
                            return "DRAG_DETECTED"
                    except Exception as skip_err:
                        print(f"⚠️ Ошибка при нажатии 'Пропустить': {skip_err}")
                        return "DRAG_DETECTED"
                
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
                
                # Выполняем клики (только для GPT пути)
                if cells_to_click:
                    click_cells_on_canvas(page, challenge_frame, cells_to_click, screenshot_path)
                else:
                    print("⚠️ Нет объектов для клика")
            
            time.sleep(1.0)
            try:
                continue_button = challenge_frame.locator('.button-submit, button:has-text("Дальше")').first
                continue_button.click()
                print("Нажали 'Дальше'")
            except Exception as cont_err:
                print(f"Не удалось нажать 'Дальше': {cont_err}")
            
            # Ждем и проверяем результат
            time.sleep(2.0)
            
            # Проверяем остался ли iframe с ЗАДАНИЕМ (не чекбокс!)
            challenge_still_present = page.locator('iframe[src*="frame=challenge"]').count() > 0
            
            if challenge_still_present:
                # Проверяем что задание видимое
                try:
                    is_visible = page.locator('iframe[src*="frame=challenge"]').first.is_visible()
                    if is_visible:
                        print("Капча еще присутствует - следующий уровень")
                        # НЕ проходим через чекбокс заново - сразу решаем задание
                        # Пропускаем проверку чекбокса для следующего уровня
                        time.sleep(1.0)
                        
                        # Делаем скриншот следующего уровня и решаем
                        analysis_dir = Path("analysis") / f"worker_{worker_id}"
                        screenshot_path = analysis_dir / "discord_captcha.png"
                        
                        try:
                            challenge_frame = page.frame_locator('iframe[src*="frame=challenge"]').first
                            time.sleep(2.0)
                            
                            try:
                                challenge_frame.locator('.challenge-container').screenshot(path=str(screenshot_path))
                            except Exception:
                                challenge_frame.locator('body').screenshot(path=str(screenshot_path))
                            print(f"Скриншот следующего уровня сохранен: {screenshot_path}")
                        except Exception as screenshot_err:
                            print(f"Ошибка создания скриншота: {screenshot_err}")
                            return False
                        
                        # Продолжаем решение с текущего момента (не вызываем функцию заново)
                        # Анализируем и кликаем как обычно
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
                            print(f"Разметка следующего уровня: {overlay_path}")
                            
                            # Решаем рекурсивно но БЕЗ повторной проверки чекбокса
                            # Для этого временно выставляем флаг
                        except Exception as e:
                            print(f"Ошибка анализа следующего уровня: {e}")
                        
                        # Рекурсивно решаем следующий уровень БЕЗ проверки чекбокса
                        return capture_and_analyze_captcha(page, worker_id, timeout, account_data, sms_country, skip_checkbox=True)
                except Exception:
                    pass
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
                        print("📱 Найдена кнопка верификации телефона - запускаем аренду номера")
                        
                        try:
                            phone_verify_button.click(timeout=5000)
                            print("✅ Кнопка верификации нажата")
                            time.sleep(2.0)
                            
                            # Арендуем номер и проходим верификацию
                            phone_verified = verify_phone_with_sms(page, account_data, sms_country)
                            
                            if phone_verified:
                                print("✅ Номер телефона успешно подтвержден!")
                                
                                # Сохраняем данные аккаунта только после успешной верификации
                                if account_data:
                                    account_file = Path("accounts.txt")
                                    with open(account_file, "a", encoding="utf-8") as f:
                                        f.write(f"\n{'='*60}\n")
                                        f.write(f"Email: {account_data.email}\n")
                                        f.write(f"Display Name: {account_data.display_name}\n")
                                        f.write(f"Username: {account_data.username}\n")
                                        f.write(f"Password: {account_data.password}\n")
                                        f.write(f"DOB: {account_data.birth_day:02d}.{account_data.birth_month:02d}.{account_data.birth_year}\n")
                                        f.write(f"Phone: {account_data.phone if hasattr(account_data, 'phone') else 'N/A'}\n")
                                        f.write(f"{'='*60}\n")
                                    print(f"💾 Данные аккаунта сохранены в {account_file}")
                            else:
                                print("⚠️ Не удалось подтвердить номер телефона")
                                return False
                                
                        except Exception as btn_err:
                            print(f"⚠️ Ошибка верификации телефона: {btn_err}")
                            return False
                    else:
                        print("ℹ️ Кнопка верификации телефона не найдена")
                        
                        # Сохраняем данные даже без верификации
                        if account_data:
                            account_file = Path("accounts.txt")
                            with open(account_file, "a", encoding="utf-8") as f:
                                f.write(f"\n{'='*60}\n")
                                f.write(f"Email: {account_data.email}\n")
                                f.write(f"Display Name: {account_data.display_name}\n")
                                f.write(f"Username: {account_data.username}\n")
                                f.write(f"Password: {account_data.password}\n")
                                f.write(f"DOB: {account_data.birth_day:02d}.{account_data.birth_month:02d}.{account_data.birth_year}\n")
                                f.write(f"{'='*60}\n")
                            print(f"💾 Данные аккаунта сохранены в {account_file}")
                    
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


def register_account(
    headless: bool, 
    wait_after_submit: float, 
    worker_id: int = 0, 
    used_emails: set[str] = None, 
    sms_country: int = 16,
    proxy: str = None,
    profile_dir: str = None
) -> bool:
    if used_emails is None:
        used_emails = set()
    
    # Импортируем stealth модули
    try:
        import sys
        from pathlib import Path as P
        project_root = P(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        from src.stealth import (
            get_stealth_browser_config,
            get_stealth_context_options,
            get_stealth_js,
        )
        from src.stealth.browser_config import get_locale_for_country, get_timezone_for_country
        
        # Определяем страну для locale/timezone
        country_code = "GB"  # По умолчанию UK
        if sms_country == 0:
            country_code = "RU"
        elif sms_country == 43:
            country_code = "DE"
        elif sms_country == 16:
            country_code = "GB"
        elif sms_country == 83:
            country_code = "BG"
        elif sms_country == 78:
            country_code = "FR"
        elif sms_country == 187:
            country_code = "US"
        
        locale = get_locale_for_country(country_code)
        timezone = get_timezone_for_country(country_code)
        
        print(f"🔧 Stealth config: locale={locale}, timezone={timezone}, proxy={'Yes' if proxy else 'No'}")
        
    except Exception as e:
        print(f"⚠️ Не удалось загрузить stealth модули: {e}")
        print("   Продолжаем без stealth...")
        get_stealth_browser_config = None
    
    with sync_playwright() as playwright:
        # Используем stealth конфигурацию если доступна
        if get_stealth_browser_config:
            browser_config = get_stealth_browser_config(
                headless=headless,
                proxy=proxy,
                user_data_dir=profile_dir,
            )
            browser = playwright.chromium.launch(**browser_config)
            
            # Context с stealth опциями
            context_options = get_stealth_context_options(
                proxy=proxy,
                locale=locale,
                timezone_id=timezone,
            )
            context = browser.new_context(**context_options)
            page = context.new_page()
            
            # Инъекция stealth JS
            stealth_js = get_stealth_js()
            page.add_init_script(stealth_js)
            print("✅ Stealth режим активирован")
        else:
            # Fallback: стандартный запуск
            browser = playwright.chromium.launch(headless=headless)
            page = browser.new_page()
        try:
            # Пытаемся зарегистрироваться, при drag-задании начинаем заново
            max_retries = 5  # Увеличиваем количество попыток
            
            for attempt in range(max_retries):
                data = build_registration_data(used_emails)
                used_emails.add(data.email)
                print(f"\n=== Registration attempt {attempt + 1}/{max_retries} ===")
                print(f"Email: {data.email}")
                print(f"Display name: {data.display_name}")
                print(f"Username: {data.username}")
                print(f"Dob: {data.birth_day}.{data.birth_month}.{data.birth_year}")

                # Переходим на страницу регистрации
                page.goto("https://discord.com/register", wait_until="load")
                time.sleep(1.5)

                if not fill_registration_form(page, data):
                    continue  # Пробуем снова

                if not submit_form(page):
                    continue  # Пробуем снова

                # Решаем капчу
                captcha_result = capture_and_analyze_captcha(page, worker_id, account_data=data, sms_country=sms_country)
                
                if captcha_result == "DRAG_DETECTED":
                    # Обнаружено drag-задание - обновляем страницу и пробуем снова
                    if attempt < max_retries - 1:
                        print(f"🔄 Обновляем страницу и пробуем снова (попытка {attempt + 2}/{max_retries})")
                        time.sleep(2.0)
                        continue
                    else:
                        print("❌ Достигнут лимит попыток из-за drag-заданий")
                        return False
                
                elif captcha_result is False:
                    # Ошибка при решении капчи
                    return False
                
                else:
                    # Успех!
                    time.sleep(wait_after_submit)
                    return True
            
            return False
        finally:
            browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Автозаполнение формы регистрации Discord с поддержкой stealth")
    parser.add_argument("--count", type=int, default=1, help="Количество попыток регистрации")
    parser.add_argument("--delay", type=float, default=3.0, help="Пауза между попытками (сек)")
    parser.add_argument("--wait-after-submit", type=float, default=5.0, help="Пауза после отправки формы (сек)")
    parser.add_argument("--headless", action="store_true", help="Запуск браузера в режиме headless")
    parser.add_argument("--country", type=int, default=16, help="Код страны для SMS-Activate (16=UK, 43=Германия, 0=Россия)")
    
    # Stealth опции
    parser.add_argument("--proxy", type=str, default=None, help="Прокси в формате user:pass@ip:port или ip:port")
    parser.add_argument("--proxy-file", type=str, default=None, help="Файл с прокси (один на строку)")
    parser.add_argument("--profile-dir", type=str, default=None, help="Директория для сохранения профиля браузера")
    
    args = parser.parse_args()

    successes = 0
    used_emails = set()
    proxy_manager = None
    
    print("=" * 70)
    print("🤖 Discord Auto Register - Stealth Edition")
    print("=" * 70)
    print(f"🌍 Страна SMS: код {args.country}")
    
    # Загружаем прокси если указаны
    if args.proxy_file:
        try:
            import sys
            from pathlib import Path as P
            project_root = P(__file__).parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from src.stealth import ProxyManager
            proxy_manager = ProxyManager(proxy_file=args.proxy_file)
            print(f"🔄 Загружено {proxy_manager.count_available()} прокси из файла")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки прокси: {e}")
    
    print("=" * 70)
    print()
    
    for attempt in range(1, args.count + 1):
        # Выбираем прокси
        current_proxy = args.proxy
        if proxy_manager:
            current_proxy = proxy_manager.get_proxy()
            print(f"🔌 Используем прокси: {current_proxy}")
        
        # Генерируем уникальную директорию профиля если нужно
        current_profile_dir = None
        if args.profile_dir:
            current_profile_dir = f"{args.profile_dir}/account_{attempt}"
        
        success = register_account(
            headless=args.headless,
            wait_after_submit=args.wait_after_submit,
            worker_id=attempt,
            used_emails=used_emails,
            sms_country=args.country,
            proxy=current_proxy,
            profile_dir=current_profile_dir,
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