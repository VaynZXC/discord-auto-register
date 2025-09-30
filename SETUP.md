# Настройка проекта Discord Captcha Solver

## 1. Установка зависимостей

```bash
pip install -r requirements.txt
playwright install chromium
```

## 2. Настройка API ключей

Все API ключи хранятся в папке `keys/`. Файлы с ключами НЕ коммитятся в git.

### 2.1 OpenAI API (для GPT-4 Vision анализа капчи)

1. Создайте файл `keys/openai.txt`
2. Вставьте ваш OpenAI API ключ
3. Получить ключ: https://platform.openai.com/api-keys

**Пример `keys/openai.txt`:**
```
sk-proj-ваш_ключ_здесь
```

### 2.2 SMS-Activate API (для верификации по телефону)

1. Создайте файл `keys/sms_activate.txt`
2. Вставьте ваш SMS-Activate API ключ
3. Получить ключ: https://sms-activate.org/en/profile

**Пример `keys/sms_activate.txt`:**
```
ваш_ключ_здесь
```

## 3. Настройка email адресов (опционально)

Создайте файл `mails.txt` в корне проекта со списком email адресов (по одному на строку):

```
email1@sabistory.com
email2@sabistory.com
email3@sabistory.com
```

Если файл не создан, будут генерироваться случайные email.

## 4. Структура ключей

```
keys/
├── openai.txt          # Ваш OpenAI API ключ
├── sms_activate.txt    # Ваш SMS-Activate API ключ
├── openai.txt.example  # Пример для OpenAI
└── sms_activate.txt.example  # Пример для SMS-Activate
```

## 5. Проверка настройки

### Проверить OpenAI:
```bash
python -c "from src.utils import load_api_key; print('OpenAI:', load_api_key('openai'))"
```

### Проверить SMS-Activate:
```bash
python src/sms/sms_activate.py
```

## 6. Запуск регистрации

```bash
# Одна регистрация
python scripts/discord_auto_register.py

# Несколько регистраций
python scripts/discord_auto_register.py --count 5

# С задержкой между попытками
python scripts/discord_auto_register.py --count 5 --delay 10
```

## 7. Результаты

- **accounts.txt** - Успешно зарегистрированные аккаунты
- **analysis/** - Скриншоты и анализ капчи

## 8. Безопасность

Файлы в `.gitignore`:
- `keys/*.txt` - Все ключи
- `accounts.txt` - Данные аккаунтов
- `mails.txt` - Email адреса
- `dataset/` - Датасет
- `src/gpt/analyzer.py` - Код с потенциальными ключами

**❗ Никогда не коммитьте файлы с ключами в git!**
