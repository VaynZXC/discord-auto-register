"""Stealth модуль для антидетект браузера."""

from .browser_config import get_stealth_browser_config, get_stealth_context_options
from .injections import get_stealth_js
from .proxy_manager import ProxyManager

__all__ = [
    'get_stealth_browser_config',
    'get_stealth_context_options',
    'get_stealth_js',
    'ProxyManager',
]

