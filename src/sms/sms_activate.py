"""SMS-Activate API client for phone verification."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional

import requests


class SMSActivateClient:
    """Клиент для работы с API SMS-Activate."""
    
    BASE_URL = "https://api.sms-activate.org/stubs/handler_api.php"
    
    # Коды сервисов
    SERVICE_DISCORD = "ds"  # Discord
    
    # Статусы активации
    STATUS_WAIT_CODE = 1      # Ожидание SMS
    STATUS_WAIT_RETRY = 3     # Запрос еще одного кода
    STATUS_COMPLETE = 6       # Завершить активацию
    STATUS_CANCEL = 8         # Отменить активацию
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Инициализация клиента.
        
        Args:
            api_key: API ключ SMS-Activate. Если не указан, берется из файла keys/sms_activate.txt
        """
        self.api_key = api_key or self._load_api_key()
        if not self.api_key:
            raise ValueError(
                "API ключ не найден! Создайте файл keys/sms_activate.txt с вашим ключом"
            )
    
    def _load_api_key(self) -> Optional[str]:
        """Загружает API ключ только из файла keys/sms_activate.txt"""
        from ..utils import load_api_key
        return load_api_key("sms_activate", "SMS_ACTIVATE_API_KEY")
    
    def _request(self, action: str, **params) -> str:
        """Выполняет запрос к API."""
        params["api_key"] = self.api_key
        params["action"] = action
        
        try:
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            return response.text.strip()
        except requests.RequestException as e:
            raise Exception(f"Ошибка запроса к SMS-Activate: {e}")
    
    def get_balance(self) -> float:
        """Получает баланс аккаунта."""
        result = self._request("getBalance")
        
        if result.startswith("ACCESS_BALANCE:"):
            balance_str = result.split(":")[1]
            return float(balance_str)
        else:
            raise Exception(f"Не удалось получить баланс: {result}")
    
    def get_number(self, service: str = SERVICE_DISCORD, country: int = 0) -> tuple[str, str]:
        """
        Получает номер телефона для активации.
        
        Args:
            service: Код сервиса (по умолчанию Discord)
            country: Код страны (0 = Россия, 1 = Украина, и т.д.)
        
        Returns:
            Tuple (activation_id, phone_number)
        
        Raises:
            Exception: Если не удалось получить номер
        """
        result = self._request("getNumber", service=service, country=country)
        
        if result.startswith("ACCESS_NUMBER:"):
            # Формат: ACCESS_NUMBER:activation_id:phone_number
            parts = result.split(":")
            activation_id = parts[1]
            phone_number = parts[2]
            return activation_id, phone_number
        elif result == "NO_NUMBERS":
            raise Exception("Нет доступных номеров")
        elif result == "NO_BALANCE":
            raise Exception("Недостаточно средств на балансе")
        else:
            raise Exception(f"Не удалось получить номер: {result}")
    
    def get_status(self, activation_id: str) -> Optional[str]:
        """
        Получает статус активации и код SMS (если пришел).
        
        Args:
            activation_id: ID активации
        
        Returns:
            SMS код или None если код еще не пришел
        """
        result = self._request("getStatus", id=activation_id)
        
        if result.startswith("STATUS_OK:"):
            # Формат: STATUS_OK:sms_code
            code = result.split(":")[1]
            return code
        elif result == "STATUS_WAIT_CODE":
            # Ожидаем код
            return None
        elif result == "STATUS_CANCEL":
            raise Exception("Активация отменена")
        else:
            # Другие статусы пока игнорируем
            return None
    
    def set_status(self, activation_id: str, status: int) -> bool:
        """
        Устанавливает статус активации.
        
        Args:
            activation_id: ID активации
            status: Статус (1 - ожидание, 3 - повтор, 6 - завершить, 8 - отменить)
        
        Returns:
            True если статус установлен успешно
        """
        result = self._request("setStatus", id=activation_id, status=status)
        return result == "ACCESS_ACTIVATION" or result == "ACCESS_CANCEL"
    
    def wait_for_code(
        self,
        activation_id: str,
        timeout: int = 300,
        check_interval: int = 5
    ) -> Optional[str]:
        """
        Ожидает получение SMS кода.
        
        Args:
            activation_id: ID активации
            timeout: Максимальное время ожидания в секундах
            check_interval: Интервал проверки в секундах
        
        Returns:
            SMS код или None если время вышло
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                code = self.get_status(activation_id)
                if code:
                    return code
            except Exception as e:
                print(f"Ошибка проверки статуса: {e}")
            
            time.sleep(check_interval)
        
        # Время вышло - отменяем активацию
        self.set_status(activation_id, self.STATUS_CANCEL)
        return None
    
    def complete_activation(self, activation_id: str) -> bool:
        """Завершает активацию (после успешного использования кода)."""
        return self.set_status(activation_id, self.STATUS_COMPLETE)
    
    def cancel_activation(self, activation_id: str) -> bool:
        """Отменяет активацию (если номер не подошел)."""
        return self.set_status(activation_id, self.STATUS_CANCEL)


# Пример использования
if __name__ == "__main__":
    try:
        client = SMSActivateClient()
        
        # Проверяем баланс
        balance = client.get_balance()
        print(f"💰 Баланс: {balance} руб.")
        
        # Получаем номер для Discord
        activation_id, phone = client.get_number(SMSActivateClient.SERVICE_DISCORD)
        print(f"📱 Получен номер: {phone}")
        print(f"🔑 ID активации: {activation_id}")
        
        # Ожидаем SMS код
        print("⏳ Ожидаем SMS код...")
        code = client.wait_for_code(activation_id, timeout=300)
        
        if code:
            print(f"✅ Получен код: {code}")
            # Завершаем активацию
            client.complete_activation(activation_id)
        else:
            print("❌ Код не получен - время вышло")
    
    except Exception as e:
        print(f"Ошибка: {e}")
