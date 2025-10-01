# 🥷 Stealth Module - Антидетект для Discord Auto Register

## 📋 Описание

Модуль предоставляет антидетект возможности для обхода систем обнаружения автоматизации Discord.

## 🎯 Основные возможности

### ✅ Реализовано (P0 - Критично)

- **WebDriver Masking** - Скрывает navigator.webdriver и другие automation флаги
- **Proxy Support** - HTTP/HTTPS/SOCKS5 прокси с авторизацией
- **User-Agent Rotation** - Реалистичные User-Agent для разных платформ
- **Browser Args Optimization** - Оптимизированные флаги запуска Chrome
- **Canvas Fingerprinting** - Добавление шума в canvas.toDataURL()
- **WebGL Spoofing** - Маскировка WebGL параметров
- **Audio Context Noise** - Рандомизация audio fingerprint
- **Font Fingerprinting** - Защита от font fingerprinting
- **Timezone/Locale Consistency** - Соответствие локали и timezone IP прокси

## 📦 Структура модуля

```
src/stealth/
├── __init__.py           # Экспорты модуля
├── browser_config.py     # Конфигурация браузера и контекста
├── injections.py         # JavaScript инъекции для маскировки
├── proxy_manager.py      # Управление прокси
└── README.md            # Эта документация
```

## 🚀 Использование

### Базовое использование

```python
from playwright.sync_api import sync_playwright
from src.stealth import get_stealth_browser_config, get_stealth_context_options, get_stealth_js

with sync_playwright() as p:
    # Конфигурация браузера
    browser_config = get_stealth_browser_config(
        headless=False,
        proxy="username:password@ip:port"
    )
    browser = p.chromium.launch(**browser_config)
    
    # Конфигурация контекста
    context_options = get_stealth_context_options(
        proxy="username:password@ip:port",
        locale="en-US",
        timezone_id="America/New_York"
    )
    context = browser.new_context(**context_options)
    page = context.new_page()
    
    # Инъекция stealth JS
    page.add_init_script(get_stealth_js())
    
    # Используем page как обычно
    page.goto("https://discord.com/register")
```

### Использование через discord_auto_register.py

```bash
# С одним прокси
python scripts/discord_auto_register.py --count 1 --proxy "user:pass@ip:port"

# С файлом прокси (автоматическая ротация)
python scripts/discord_auto_register.py --count 5 --proxy-file proxies.txt

# С сохранением профиля браузера
python scripts/discord_auto_register.py --count 1 --profile-dir ./profiles

# Все вместе
python scripts/discord_auto_register.py \
    --count 3 \
    --proxy-file proxies.txt \
    --profile-dir ./profiles \
    --country 16
```

## 🔧 Конфигурация

### Proxy Manager

```python
from src.stealth import ProxyManager

# Из файла
pm = ProxyManager(proxy_file="proxies.txt")
proxy = pm.get_proxy()

# Напрямую из списка
pm = ProxyManager(proxies=["ip:port", "user:pass@ip:port"])

# Валидация прокси
if pm.validate_proxy(proxy):
    print("Прокси работает!")

# Определение страны
country = pm.get_country_from_proxy(proxy)
```

### Browser Config

```python
from src.stealth.browser_config import (
    get_stealth_browser_args,
    get_random_viewport,
    get_random_user_agent,
    get_timezone_for_country,
    get_locale_for_country,
)

# Получить args для браузера
args = get_stealth_browser_args()

# Случайный viewport
viewport = get_random_viewport()  # {'width': 1920, 'height': 1080}

# Случайный User-Agent
ua = get_random_user_agent()

# Timezone по коду страны
tz = get_timezone_for_country("RU")  # "Europe/Moscow"
locale = get_locale_for_country("RU")  # "ru-RU"
```

### JavaScript Injections

```python
from src.stealth.injections import (
    get_webdriver_masking_js,
    get_canvas_fingerprint_js,
    get_webgl_fingerprint_js,
    get_audio_fingerprint_js,
    get_stealth_js,  # Все вместе
)

# Использование отдельных скриптов
page.add_init_script(get_webdriver_masking_js())
page.add_init_script(get_canvas_fingerprint_js())

# Или все сразу
page.add_init_script(get_stealth_js())
```

## 📁 Формат файла прокси (proxies.txt)

```txt
# Поддерживаемые форматы:

# IP:PORT
123.45.67.89:8080

# IP:PORT с авторизацией
username:password@123.45.67.89:8080

# С протоколом
http://123.45.67.89:8080
https://username:password@123.45.67.89:8080
socks5://123.45.67.89:1080
```

## 📈 Проверка stealth качества

### Рекомендуемые тесты

1. **Sannysoft Bot Detector** - https://bot.sannysoft.com/
2. **CreepJS** - https://abrahamjuliot.github.io/creepjs/
3. **PixelScan** - https://pixelscan.net/
4. **Fingerprint.com** - https://fingerprint.com/demo/

### Что проверять

- ✅ `navigator.webdriver` должен быть `undefined`
- ✅ `navigator.plugins` должен содержать реалистичные плагины
- ✅ Canvas fingerprint должен быть уникальным но стабильным
- ✅ WebGL vendor/renderer должны быть замаскированы
- ✅ Timezone должен соответствовать IP прокси
- ✅ User-Agent должен соответствовать platform/vendor

## ⚠️ Важные замечания

### Headless режим

**НЕ рекомендуется** использовать headless режим для Discord - он легко детектится. Если необходимо, модуль использует `--headless=new` (менее детектируемый).

### Качество прокси

- **Резидентные прокси** - лучший выбор (меньше всего детектятся)
- **Mobile прокси** - отличный вариант но дороже
- **Datacenter прокси** - дешевле но легче детектятся

### Соответствие параметров

Критично важно чтобы:
- Timezone соответствовал IP прокси
- Locale соответствовал стране
- User-Agent соответствовал platform

## 🔮 Будущие улучшения (Roadmap)

### P1 - Высокий приоритет
- [ ] Browser profiles persistence (cookies/localStorage)
- [ ] Realistic mouse movements
- [ ] Random delays между действиями

### P2 - Средний приоритет
- [ ] Realistic typing speed
- [ ] Scroll behavior simulation
- [ ] Battery/Network info spoofing

### P3 - Низкий приоритет
- [ ] Chrome DevTools Protocol hiding
- [ ] Permissions API advanced spoofing
- [ ] Plugin array advanced spoofing

## 📊 Метрики эффективности

### Целевые показатели

- **Success rate верификации телефона**: > 70%
- **Bot detection score** (CreepJS): > 60%
- **Canvas uniqueness**: Уникальный per session
- **WebDriver detection**: 0% (должен быть скрыт)

## 🐛 Troubleshooting

### Прокси не работает

```python
# Проверьте формат
proxy = "username:password@123.45.67.89:8080"  # ✅ Правильно
proxy = "123.45.67.89:8080:username:password"  # ❌ Неправильно

# Валидируйте перед использованием
from src.stealth import ProxyManager
pm = ProxyManager(proxies=[proxy])
if not pm.validate_proxy(proxy):
    print("Прокси не работает!")
```

### Stealth не применяется

Убедитесь что:
1. Модуль импортируется корректно
2. `page.add_init_script()` вызывается ДО `page.goto()`
3. Нет ошибок в консоли браузера

### Discord все равно детектит

Попробуйте:
1. Использовать качественные резидентные прокси
2. Добавить delay между действиями
3. Проверить соответствие timezone и IP
4. Не использовать headless режим
5. Использовать browser profiles (persistence)

## 📚 Дополнительные ресурсы

- [STEALTH_ROADMAP.md](../../STEALTH_ROADMAP.md) - Полный roadmap развития
- [Playwright Docs](https://playwright.dev/python/docs/intro)
- [Canvas Fingerprinting](https://browserleaks.com/canvas)
- [WebGL Fingerprinting](https://browserleaks.com/webgl)

---

**Версия:** 1.0  
**Дата:** 2025-10-01  
**Статус:** ✅ Базовые P0 функции реализованы

