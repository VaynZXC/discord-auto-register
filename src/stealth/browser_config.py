"""Browser configuration для антидетект."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional


def get_stealth_browser_args() -> List[str]:
    """
    Возвращает аргументы запуска браузера для максимального stealth.
    
    Returns:
        Список аргументов командной строки для Chrome/Chromium
    """
    return [
        # Главный флаг - скрывает navigator.webdriver
        '--disable-blink-features=AutomationControlled',
        
        # Отключаем детект автоматизации
        '--disable-automation',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-infobars',
        
        # WebGL & Canvas fingerprinting
        '--disable-canvas-aa',  # Отключаем anti-aliasing для canvas
        '--disable-2d-canvas-clip-aa',
        
        # Сертификаты
        '--ignore-certificate-errors',
        '--ignore-certificate-errors-spki-list',
        
        # Site isolation (может помочь с детектом)
        '--disable-features=IsolateOrigins,site-per-process',
        
        # Дополнительные флаги
        '--disable-breakpad',
        '--disable-component-extensions-with-background-pages',
        '--disable-extensions',
        '--disable-features=TranslateUI,BlinkGenPropertyTrees',
        '--disable-ipc-flooding-protection',
        '--disable-renderer-backgrounding',
        '--enable-features=NetworkService,NetworkServiceInProcess',
        '--force-color-profile=srgb',
        '--hide-scrollbars',
        '--metrics-recording-only',
        '--mute-audio',
        '--no-default-browser-check',
        '--no-first-run',
        '--password-store=basic',
        '--use-mock-keychain',
    ]


def get_random_viewport() -> Dict[str, int]:
    """
    Генерирует случайный, но реалистичный viewport.
    
    Returns:
        Dict с width и height
    """
    # Популярные разрешения экранов (компактные для комфорта)
    viewports = [
        {'width': 1366, 'height': 768},   # Laptop (популярный)
        {'width': 1280, 'height': 720},   # HD (компактный)
        {'width': 1440, 'height': 900},   # MacBook Pro
        {'width': 1536, 'height': 864},   # Laptop HD+
    ]
    
    return random.choice(viewports)


def get_random_user_agent() -> str:
    """
    Возвращает случайный realistic User-Agent.
    
    Returns:
        User-Agent string
    """
    user_agents = [
        # Windows Chrome
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        
        # Windows Edge
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        
        # macOS Chrome
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        
        # Linux Chrome
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    
    return random.choice(user_agents)


def get_stealth_browser_config(
    headless: bool = False,
    proxy: Optional[str] = None,
    user_data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Возвращает полную конфигурацию для запуска stealth браузера.
    
    Args:
        headless: Запускать в headless режиме (не рекомендуется для Discord)
        proxy: Прокси в формате "user:pass@ip:port" или "ip:port"
        user_data_dir: Путь к профилю браузера для persistence
    
    Returns:
        Dict с параметрами для browser.launch()
    """
    args = get_stealth_browser_args()
    
    # Добавляем прокси если указан
    if proxy:
        # Парсим прокси
        if '@' in proxy:
            # Формат: user:pass@ip:port
            auth, server = proxy.split('@')
            args.append(f'--proxy-server=http://{server}')
        else:
            # Формат: ip:port
            args.append(f'--proxy-server=http://{proxy}')
    
    # Headless mode (НЕ рекомендуется для Discord - легко детектится)
    # Если все же нужен, используем new headless mode (менее детектируемый)
    if headless:
        args.append('--headless=new')
    
    config = {
        'headless': False,  # Всегда False, используем --headless=new в args если нужно
        'args': args,
    }
    
    # Добавляем user data dir если указан
    if user_data_dir:
        config['user_data_dir'] = user_data_dir
    
    return config


def get_stealth_context_options(
    proxy: Optional[str] = None,
    locale: str = 'en-US',
    timezone_id: str = 'America/New_York',
) -> Dict[str, Any]:
    """
    Возвращает опции для browser.new_context() с stealth настройками.
    
    Args:
        proxy: Прокси в формате "user:pass@ip:port" (для context-level proxy)
        locale: Локаль браузера
        timezone_id: Timezone ID (должен соответствовать IP прокси)
    
    Returns:
        Dict с параметрами для browser.new_context()
    """
    viewport = get_random_viewport()
    user_agent = get_random_user_agent()
    
    context_options = {
        'viewport': viewport,
        'user_agent': user_agent,
        'locale': locale,
        'timezone_id': timezone_id,
        
        # Permissions (важно для Discord)
        'permissions': ['notifications'],
        
        # Geolocation (соответствует timezone)
        # Координаты Нью-Йорка по умолчанию
        'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},
        
        # Extra HTTP headers
        'extra_http_headers': {
            'Accept-Language': f'{locale.replace("_", "-")},en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        },
    }
    
    # Proxy auth на уровне context (если указан и содержит логин)
    if proxy and '@' in proxy:
        auth, server = proxy.split('@')
        username, password = auth.split(':')
        
        context_options['proxy'] = {
            'server': f'http://{server}',
            'username': username,
            'password': password,
        }
    elif proxy:
        # Прокси без авторизации
        context_options['proxy'] = {
            'server': f'http://{proxy}',
        }
    
    return context_options


def get_timezone_for_country(country_code: str) -> str:
    """
    Возвращает подходящий timezone для кода страны.
    
    Args:
        country_code: Код страны (RU, US, DE, GB, etc.)
    
    Returns:
        Timezone ID
    """
    timezones = {
        'RU': 'Europe/Moscow',
        'US': 'America/New_York',
        'GB': 'Europe/London',
        'DE': 'Europe/Berlin',
        'FR': 'Europe/Paris',
        'BG': 'Europe/Sofia',
        'UA': 'Europe/Kiev',
        'PL': 'Europe/Warsaw',
        'CN': 'Asia/Shanghai',
        'JP': 'Asia/Tokyo',
        'KR': 'Asia/Seoul',
        'BR': 'America/Sao_Paulo',
        'IN': 'Asia/Kolkata',
        'AU': 'Australia/Sydney',
        'CA': 'America/Toronto',
    }
    
    return timezones.get(country_code.upper(), 'America/New_York')


def get_locale_for_country(country_code: str) -> str:
    """
    Возвращает подходящую локаль для кода страны.
    
    Args:
        country_code: Код страны
    
    Returns:
        Locale string
    """
    locales = {
        'RU': 'ru-RU',
        'US': 'en-US',
        'GB': 'en-GB',
        'DE': 'de-DE',
        'FR': 'fr-FR',
        'BG': 'bg-BG',
        'UA': 'uk-UA',
        'PL': 'pl-PL',
        'CN': 'zh-CN',
        'JP': 'ja-JP',
        'KR': 'ko-KR',
        'BR': 'pt-BR',
        'IN': 'en-IN',
        'AU': 'en-AU',
        'CA': 'en-CA',
    }
    
    return locales.get(country_code.upper(), 'en-US')

