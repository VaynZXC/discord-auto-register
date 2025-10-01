# 📦 Установка Botright для Discord Auto Register

## ⚡ Быстрая установка

### 1. Удалите старые версии

```bash
pip uninstall botright playwright -y
```

### 2. Установите Botright с GitHub

```bash
pip install git+https://github.com/Vinyzu/Botright.git
pip install fake-useragent
```

### 3. Установите браузер Chromium

```bash
playwright install chromium
```

### 4. Готово! Проверьте установку

```bash
python scripts/test_botright_v051.py
```

Должно открыться окно браузера на https://bot.sannysoft.com/ с **ВСЕ ЗЕЛЕНЫМИ** результатами!

---

## 🧪 Проверка stealth качества

### Тест 1: Sannysoft Bot Detector

```bash
python scripts/test_botright_v051.py
```

**Ожидаемый результат:**
- ✅ WebDriver (New) - **missing (passed)**
- ✅ Plugins is of type PluginArray - **passed**
- ✅ WebDriver Advanced - **passed**
- ✅ Chrome (New) - **present (passed)**
- ✅ Plugins Length - **5**

### Тест 2: Регистрация Discord

```bash
# Тестовая регистрация (1 аккаунт)
python scripts/discord_auto_register_botright.py --count 1 --country 16
```

---

## ⚙️ Настройка прокси

### Создайте файл `proxies.txt`

```txt
# Формат: username:password@ip:port
myuser:mypass@123.45.67.89:8080
```

### Запустите с прокси

```bash
python scripts/discord_auto_register_botright.py \
    --count 1 \
    --proxy-file proxies.txt \
    --country 16
```

---

## 🔧 Настройка SMS-Activate

### Создайте файл `keys/sms_activate.txt`

```txt
YOUR_API_KEY_HERE
```

Получить API ключ: https://sms-activate.org/ru/api

---

## ❓ Проблемы и решения

### Ошибка: ModuleNotFoundError

```bash
# Установите недостающие зависимости
pip install -r requirements.txt
pip install fake-useragent
```

### Ошибка: Playwright browser not found

```bash
# Переустановите браузер
playwright install chromium
```

### Ошибка: hcaptcha_challenger errors

Это нормально - Botright сам справится. Ошибки при инициализации можно игнорировать.

---

## ✅ Финальная проверка

Запустите все по порядку:

```bash
# 1. Тест stealth
python scripts/test_botright_v051.py

# 2. Проверьте что все зеленое на Sannysoft
# 3. Закройте браузер (Enter)

# 4. Запустите регистрацию
python scripts/discord_auto_register_botright.py --count 1 --country 16
```

Если все работает - вы готовы к массовой регистрации! 🚀

---

**Важно:** Botright работает лучше всего на **Windows 10/11** с последним Python 3.11+

