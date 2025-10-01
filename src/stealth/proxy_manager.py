"""Менеджер прокси для ротации и валидации."""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import List, Optional
import requests


class ProxyManager:
    """Менеджер для работы с прокси."""
    
    def __init__(self, proxy_file: Optional[str] = None, proxies: Optional[List[str]] = None):
        """
        Инициализирует менеджер прокси.
        
        Args:
            proxy_file: Путь к файлу с прокси (один на строку)
            proxies: Список прокси напрямую
        """
        self.proxies: List[str] = []
        self.used_proxies: set[str] = set()
        
        if proxy_file:
            self.load_from_file(proxy_file)
        elif proxies:
            self.proxies = proxies.copy()
    
    def load_from_file(self, file_path: str) -> None:
        """
        Загружает прокси из файла.
        
        Args:
            file_path: Путь к файлу с прокси
        """
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️ Файл прокси не найден: {file_path}")
            return
        
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Конвертируем формат если нужно
                    converted = self._convert_proxy_format(line)
                    
                    # Валидируем формат прокси
                    if self._is_valid_proxy_format(converted):
                        self.proxies.append(converted)
                    else:
                        print(f"⚠️ Неверный формат прокси: {line}")
        
        print(f"✅ Загружено {len(self.proxies)} прокси из {file_path}")
    
    def _convert_proxy_format(self, proxy: str) -> str:
        """
        Конвертирует прокси из формата ip:port:user:pass в user:pass@ip:port
        
        Args:
            proxy: Строка прокси в любом формате
        
        Returns:
            Прокси в формате user:pass@ip:port
        """
        # Если уже в правильном формате - вернуть как есть
        if '@' in proxy or proxy.startswith('http://') or proxy.startswith('socks5://'):
            return proxy
        
        # Проверяем формат ip:port:user:pass
        parts = proxy.split(':')
        
        if len(parts) == 4:
            # Формат: ip:port:username:password
            ip, port, username, password = parts
            converted = f"{username}:{password}@{ip}:{port}"
            print(f"   Конвертировано: {proxy} -> {converted}")
            return converted
        
        # Если не подходит ни под один формат - вернуть как есть
        return proxy
    
    def _is_valid_proxy_format(self, proxy: str) -> bool:
        """
        Проверяет формат прокси.
        
        Args:
            proxy: Строка прокси
        
        Returns:
            True если формат правильный
        """
        # Форматы:
        # ip:port
        # user:pass@ip:port
        # http://ip:port
        # http://user:pass@ip:port
        # socks5://ip:port
        
        patterns = [
            r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$',  # ip:port
            r'^.+:.+@\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$',  # user:pass@ip:port
            r'^https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$',  # http://ip:port
            r'^https?://.+:.+@\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$',  # http://user:pass@ip:port
            r'^socks5://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$',  # socks5://ip:port
        ]
        
        return any(re.match(pattern, proxy) for pattern in patterns)
    
    def get_proxy(self, random_select: bool = True) -> Optional[str]:
        """
        Возвращает прокси для использования.
        
        Args:
            random_select: Выбирать случайный прокси или по порядку
        
        Returns:
            Прокси строка или None если нет доступных
        """
        if not self.proxies:
            return None
        
        # Фильтруем уже использованные
        available = [p for p in self.proxies if p not in self.used_proxies]
        
        # Если все использованы - сбрасываем счетчик
        if not available:
            self.used_proxies.clear()
            available = self.proxies.copy()
        
        # Выбираем прокси
        if random_select:
            proxy = random.choice(available)
        else:
            proxy = available[0]
        
        self.used_proxies.add(proxy)
        return proxy
    
    def validate_proxy(self, proxy: str, timeout: int = 10) -> bool:
        """
        Проверяет работоспособность прокси.
        
        Args:
            proxy: Прокси для проверки
            timeout: Timeout для проверки в секундах
        
        Returns:
            True если прокси работает
        """
        try:
            # Нормализуем формат прокси для requests
            proxy_dict = self._format_proxy_for_requests(proxy)
            
            # Делаем тестовый запрос
            response = requests.get(
                'https://httpbin.org/ip',
                proxies=proxy_dict,
                timeout=timeout
            )
            
            return response.status_code == 200
            
        except Exception as e:
            print(f"⚠️ Прокси {proxy} не работает: {e}")
            return False
    
    def _format_proxy_for_requests(self, proxy: str) -> dict:
        """
        Форматирует прокси для библиотеки requests.
        
        Args:
            proxy: Прокси строка
        
        Returns:
            Dict для requests.get(proxies=...)
        """
        # Если уже есть протокол - используем как есть
        if proxy.startswith('http://') or proxy.startswith('https://') or proxy.startswith('socks5://'):
            return {
                'http': proxy,
                'https': proxy,
            }
        
        # Если формат user:pass@ip:port или ip:port - добавляем http://
        return {
            'http': f'http://{proxy}',
            'https': f'http://{proxy}',
        }
    
    def get_country_from_proxy(self, proxy: str) -> Optional[str]:
        """
        Пытается определить страну прокси через IP API.
        
        Args:
            proxy: Прокси для проверки
        
        Returns:
            Код страны (RU, US, etc.) или None
        """
        try:
            # Извлекаем IP из прокси
            ip_match = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', proxy)
            if not ip_match:
                return None
            
            ip = ip_match.group(0)
            
            # Используем ip-api.com для определения страны
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get('countryCode')
                
        except Exception as e:
            print(f"⚠️ Не удалось определить страну для {proxy}: {e}")
        
        return None
    
    def count_available(self) -> int:
        """Возвращает количество доступных прокси."""
        return len(self.proxies)
    
    def count_used(self) -> int:
        """Возвращает количество использованных прокси."""
        return len(self.used_proxies)
    
    def reset_used(self) -> None:
        """Сбрасывает счетчик использованных прокси."""
        self.used_proxies.clear()
        print("✅ Счетчик использованных прокси сброшен")

