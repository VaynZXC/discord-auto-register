# 🤖 Discord Auto Register - Botright Edition

## ✅ Что дает Botright

### Результаты тестирования (Sannysoft):
- ✅ **WebDriver** - missing (passed) 
- ✅ **Plugins is of type PluginArray** - passed
- ✅ **WebDriver Advanced** - passed
- ✅ **Chrome** - present (passed)
- ✅ **Plugins Length** - 5
- ✅ **Languages** - en-US

**Все тесты ЗЕЛЕНЫЕ!** 🎉

---

## 🚀 Использование

### Базовый запуск

```bash
# 1 регистрация без прокси
python scripts/discord_auto_register_botright.py --count 1 --country 16

# С прокси
python scripts/discord_auto_register_botright.py \
    --count 1 \
    --proxy "username:password@123.45.67.89:8080" \
    --country 16

# С файлом прокси (автоматическая ротация)
python scripts/discord_auto_register_botright.py \
    --count 5 \
    --proxy-file proxies.txt \
    --country 16
```

### Параметры

- `--count` - количество регистраций (default: 1)
- `--country` - код страны для SMS (16=UK, 43=DE, 0=RU, 187=US)
- `--proxy` - прокси: `user:pass@ip:port`
- `--proxy-file` - файл с прокси (один на строку)
- `--delay` - пауза между попытками в секундах (default: 3.0)
- `--wait-after-submit` - пауза после отправки формы (default: 5.0)
- `--headless` - headless режим (НЕ рекомендуется)

---

## 📋 Формат файла прокси

Создайте `proxies.txt`:

```txt
# Формат: username:password@ip:port
user1:pass1@123.45.67.89:8080
user2:pass2@98.76.54.32:8080

# Или просто ip:port (без авторизации)
123.45.67.89:8080
```

---

## 🔍 Что делает скрипт

1. **Инициализирует Botright** - автоматический stealth
2. **Заполняет форму** регистрации Discord
3. **Решает hCaptcha** - встроенный solver Botright
4. **Арендует номер** через SMS-Activate
5. **Подтверждает телефон** - вводит SMS код
6. **Сохраняет данные** в `accounts.txt`

---

## ⚙️ Коды стран для SMS

| Код | Страна | Рекомендация |
|-----|--------|--------------|
| `16` | Великобритания 🇬🇧 | ⭐ Рекомендуется |
| `187` | США 🇺🇸 | ⭐ Рекомендуется |
| `43` | Германия 🇩🇪 | ✅ Хорошо |
| `78` | Франция 🇫🇷 | ✅ Хорошо |
| `83` | Болгария 🇧🇬 | ⚠️ Средне |
| `0` | Россия 🇷🇺 | ⚠️ Не рекомендуется |

**Важно:** Страна прокси должна соответствовать стране SMS!

---

## 🧪 Тестирование stealth

Проверьте браузер перед регистрацией:

```bash
python scripts/test_botright_v051.py
```

Откроется браузер на https://bot.sannysoft.com/ - все должно быть зеленым!

---

## 📊 Отличия от старой версии

### Старая версия (sync Playwright):
- ❌ WebDriver detected (красный)
- ❌ PluginArray failed (красный)
- 🧠 Своя AI модель для капчи (GPT + Vision)
- ⚠️ Средняя защита

### Botright версия:
- ✅ WebDriver hidden (зеленый)
- ✅ PluginArray passed (зеленый)
- 🤖 Встроенный hCaptcha solver
- ✅ Максимальная защита

---

## 💡 Советы

### ✅ DO (Делайте)
- Используйте **резидентные прокси**
- Делайте **паузы** между регистрациями (5+ сек)
- Проверяйте **баланс SMS-Activate**
- Тестируйте stealth перед массовой регистрацией

### ❌ DON'T (Не делайте)
- Не используйте **datacenter прокси**
- Не запускайте **headless** режим
- Не регистрируйте **слишком много** аккаунтов подряд
- Не игнорируйте **ошибки в логах**

---

## 🆘 Troubleshooting

### Проблема: Botright не запускается

```bash
# Переустановите с GitHub
pip uninstall botright -y
pip install git+https://github.com/Vinyzu/Botright.git
playwright install chromium
```

### Проблема: Капча не решается

Botright использует встроенный solver. Если не работает:
1. Проверьте интернет соединение
2. Увеличьте timeout
3. Попробуйте без прокси (для теста)

### Проблема: SMS код не приходит

```python
# Проверьте баланс
from src.sms import SMSActivateClient
client = SMSActivateClient()
print(f"Balance: ${client.get_balance():.2f}")
```

---

## 📚 Дополнительные файлы

- **Тест stealth:** `scripts/test_botright_v051.py`
- **Roadmap:** `STEALTH_ROADMAP.md`
- **Прокси модуль:** `src/stealth/proxy_manager.py`

---

**Версия:** 1.0 (Botright)  
**Дата:** 2025-10-01  
**Статус:** ✅ Production Ready

