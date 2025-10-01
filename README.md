# 🤖 DiscordCaptcha - Автоматическая регистрация Discord с AI

Полнофункциональная система автоматической регистрации аккаунтов Discord с решением капч hCaptcha и антидетект технологиями.

## 🎯 Возможности

### Основные
- ✅ **Автоматическая регистрация** Discord аккаунтов
- 🧠 **AI решение капч** hCaptcha (любые типы заданий)
- 📱 **SMS верификация** через SMS-Activate API
- 🥷 **Stealth режим** - обход детекта автоматизации

### Антидетект (NEW!)
- 🔒 **WebDriver Masking** - скрытие automation флагов
- 🌐 **Proxy Support** - HTTP/HTTPS/SOCKS5 с ротацией
- 🖐️ **Fingerprint Protection** - Canvas/WebGL/Audio spoofing
- 🌍 **Locale/Timezone** - соответствие IP прокси
- 💾 **Browser Profiles** - persistent cookies/localStorage

## 📦 Установка

### 1. Клонирование репозитория
```bash
git clone <url>
cd DiscordCaptcha
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Установка для GPU (рекомендуется)
Для ускорения работы с нейросетями:
```bash
# Для NVIDIA GPU
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Проверка GPU
python -c "import torch; print(f'CUDA доступен: {torch.cuda.is_available()}')"
```

## 🚀 Использование

### 🎯 Discord Auto Register - Botright Edition (РЕКОМЕНДУЕТСЯ) ✅

**100% Stealth - Все тесты зеленые на Sannysoft!**

```bash
# Регистрация 1 аккаунта (без прокси)
python scripts/discord_auto_register_botright.py --count 1 --country 16

# С прокси (рекомендуется)
python scripts/discord_auto_register_botright.py --count 1 \
    --proxy "username:password@123.45.67.89:8080" \
    --country 16

# С файлом прокси (автоматическая ротация)
python scripts/discord_auto_register_botright.py --count 5 \
    --proxy-file proxies.txt \
    --country 16
```

### 🔧 Discord Auto Register - Classic (Старая версия)

```bash
# Работает, но stealth слабее (для тестов)
python scripts/discord_auto_register.py --count 1 \
    --proxy-file proxies.txt \
    --country 16
```

#### Параметры
- `--count` - количество регистраций
- `--country` - код страны для SMS (16=UK, 43=DE, 0=RU, 187=US)
- `--proxy` - прокси в формате `user:pass@ip:port`
- `--proxy-file` - файл с прокси (один на строку)
- `--profile-dir` - директория для сохранения профилей
- `--headless` - headless режим (не рекомендуется)

#### Формат файла прокси (proxies.txt)
```txt
# HTTP/HTTPS прокси
username:password@123.45.67.89:8080
123.45.67.89:8080

# SOCKS5
socks5://123.45.67.89:1080
```

### 🧪 Тестирование капч

1. **Запустите тестовый сервер** (в первом терминале):
   ```bash
   python server.py
   ```

2. **Запустите анализатор капч** (во втором терминале):
   ```bash
   python capture.py
   ```

### Что происходит при регистрации:

1. 🌐 Открывается браузер с stealth настройками
2. 📝 Заполняется форма регистрации
3. 🔍 Автоматически решается hCaptcha
4. 📱 Арендуется номер через SMS-Activate
5. ✅ Подтверждается телефон
6. 💾 Данные аккаунта сохраняются в `accounts.txt`

## 📁 Структура файлов

```
DiscordCaptcha/
├── server.py              # Тестовый сервер с hCaptcha
├── capture.py             # Автоматизация браузера + анализ
├── captcha_analyzer.py    # ИИ анализатор капч
├── requirements.txt       # Зависимости Python
├── roadmap.md            # План развития проекта
├── analysis/             # Скриншоты капч
│   └── captcha.png       # Последний скриншот (заменяется)
└── solutions/            # Решения от ИИ
    ├── analysis.json     # Структурированные данные (заменяется)
    └── solution.txt      # Текстовое решение (заменяется)
```

## 🧠 Как работает ИИ анализ

### Используемые модели:
1. **LLaVA 1.5-7B** (основная) - multimodal модель для понимания изображений и текста
2. **Kosmos-2** (резервная) - Microsoft модель для vision-language задач  
3. **BLIP2** (легкая) - быстрая модель для простых случаев

### Что анализируется:
- 🔍 **Тип задания** (сетка изображений, текст, движение)
- 📝 **Инструкции** (распознавание текста заданий)
- 🎯 **Объекты** (что нужно найти/выбрать)
- ✅ **Решение** (пошаговое описание действий)

### Пример анализа:
```
ТИП: Сетка изображений 3x3
ИНСТРУКЦИЯ: Выберите все изображения с автомобилями
РЕШЕНИЕ: Кликнуть на ячейки: верхняя левая, центральная, нижняя правая
ОБЪЕКТЫ: автомобиль (3), дерево (2), здание (4)
```

## ⚙️ Конфигурация

### Изменение модели ИИ
В `captcha_analyzer.py` можно поменять приоритет моделей:
```python
models_to_try = [
    "llava-hf/llava-1.5-7b-hf",      # Лучшее качество
    "microsoft/kosmos-2-patch14-224", # Средний баланс  
    "Salesforce/blip2-opt-2.7b"      # Самая быстрая
]
```

### Настройка hCaptcha ключа
В `server.py` уже установлен рабочий ключ. Для смены:
```python
def _sitekey() -> str:
    return "ваш-новый-ключ-hcaptcha"
```

## 🔧 Системные требования

### Минимальные:
- **Python**: 3.9+
- **RAM**: 8GB
- **Storage**: 5GB для моделей
- **GPU**: Не обязательно, но ускоряет в 10x раз

### Рекомендуемые:
- **GPU**: NVIDIA RTX 3060+ (8GB VRAM)  
- **RAM**: 16GB+
- **Storage**: SSD для быстрой загрузки моделей

## 📊 Производительность

| Модель | Размер | Скорость | Качество | GPU RAM |
|--------|---------|----------|----------|---------|
| BLIP2-2.7B | ~6GB | ~3 сек | ⭐⭐⭐ | 4GB |
| Kosmos-2 | ~8GB | ~5 сек | ⭐⭐⭐⭐ | 6GB |
| LLaVA-1.5-7B | ~14GB | ~8 сек | ⭐⭐⭐⭐⭐ | 8GB |

## 🛠️ Разработка

### Запуск только анализатора:
```bash
python captcha_analyzer.py path/to/captcha.png
```

### Добавление новых типов капч:
1. Собрать образцы в `analysis/`
2. Обновить промпт в `_create_analysis_prompt()`
3. Протестировать на разных типах заданий

## 🐛 Устранение неполадок

### Ошибка "CUDA out of memory":
```bash
# Используйте CPU режим
export CUDA_VISIBLE_DEVICES=""
python capture.py
```

### Ошибка установки bitsandbytes:
```bash
# Для Windows
pip install bitsandbytes --prefer-binary
```

### Медленная работа:
- Убедитесь что используется GPU
- Попробуйте более легкую модель
- Закройте другие GPU-приложения

## 📋 TODO

- [ ] Добавить автоматические клики по найденным объектам
- [ ] Интеграция с реальными сайтами (не только тестовый)
- [ ] Поддержка reCAPTCHA v2/v3
- [ ] Web API для удаленного использования
- [ ] Датасет для fine-tuning моделей

## 📄 Лицензия

Проект предназначен только для образовательных целей и исследований в области компьютерного зрения.

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Сделайте изменения
4. Протестируйте на разных типах капч
5. Создайте Pull Request

---

**⚠️ Важно**: Данный проект создан исключительно в образовательных целях для изучения современных технологий машинного обучения и компьютерного зрения.
