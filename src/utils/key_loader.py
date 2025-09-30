"""Универсальная загрузка API ключей из папки keys."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def load_api_key(service_name: str, env_var: Optional[str] = None) -> Optional[str]:
    """
    Загружает API ключ для сервиса.
    
    Приоритет:
    1. Файл keys/{service_name}.txt
    2. Переменная окружения (если указана)
    
    Args:
        service_name: Имя сервиса (например, "openai", "sms_activate")
        env_var: Имя переменной окружения (опционально)
    
    Returns:
        API ключ или None
    
    Example:
        >>> key = load_api_key("openai", "OPENAI_API_KEY")
        >>> key = load_api_key("sms_activate")
    """
    # 1. Из файла (приоритет)
    key_path = Path(f"keys/{service_name}.txt")
    if key_path.exists():
        content = key_path.read_text(encoding="utf-8").strip()
        # Убираем комментарии и пустые строки
        lines = [
            line.strip() 
            for line in content.split("\n") 
            if line.strip() and not line.startswith("#")
        ]
        if lines:
            return lines[0]
    
    # 2. Из переменной окружения (fallback)
    if env_var:
        env_key = os.getenv(env_var)
        if env_key:
            return env_key
    
    return None


def validate_key(key: Optional[str], service_name: str) -> str:
    """
    Проверяет наличие ключа и выбрасывает исключение если его нет.
    
    Args:
        key: API ключ
        service_name: Имя сервиса для сообщения об ошибке
    
    Returns:
        Ключ (если он есть)
    
    Raises:
        ValueError: Если ключ не найден
    """
    if not key:
        raise ValueError(
            f"API ключ {service_name} не найден!\n"
            f"Создайте файл keys/{service_name}.txt с вашим ключом"
        )
    return key
