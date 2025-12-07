"""
Модуль для работы с данными пользователей
Хранит настройки, локации и подписки в user_data.json
"""

import os
import json
from typing import Optional, Dict, Any

USER_DATA_FILE = "user_data.json"


def load_all_users() -> Dict[str, Any]:
    """Загружает все данные пользователей из файла"""
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_all_users(data: Dict[str, Any]) -> None:
    """Сохраняет все данные пользователей в файл"""
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_user(user_id: int) -> dict:
    """
    Загружает данные конкретного пользователя
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        dict: Данные пользователя со структурой:
        {
            "city": str | None,
            "lat": float | None,
            "lon": float | None,
            "notifications": {
                "enabled": bool,
                "interval_h": int
            },
            "last_weather": dict | None
        }
    """
    data = load_all_users()
    user_id_str = str(user_id)
    
    if user_id_str not in data:
        # Создаем нового пользователя с дефолтными настройками
        default_user = {
            "city": None,
            "lat": None,
            "lon": None,
            "notifications": {
                "enabled": False,
                "interval_h": 2
            },
            "last_weather": None
        }
        data[user_id_str] = default_user
        save_all_users(data)
        return default_user
    
    return data[user_id_str]


def save_user(user_id: int, user_data: dict) -> None:
    """
    Сохраняет данные пользователя
    
    Args:
        user_id: ID пользователя Telegram
        user_data: Словарь с данными пользователя
    """
    data = load_all_users()
    data[str(user_id)] = user_data
    save_all_users(data)


def update_user_location(user_id: int, city: str = None, lat: float = None, lon: float = None) -> None:
    """
    Обновляет локацию пользователя
    
    Args:
        user_id: ID пользователя
        city: Название города (опционально)
        lat: Широта (опционально)
        lon: Долгота (опционально)
    """
    user_data = load_user(user_id)
    
    if city:
        user_data["city"] = city
    if lat is not None:
        user_data["lat"] = lat
    if lon is not None:
        user_data["lon"] = lon
    
    save_user(user_id, user_data)


def update_user_notifications(user_id: int, enabled: bool = None, interval_h: int = None) -> None:
    """
    Обновляет настройки уведомлений пользователя
    
    Args:
        user_id: ID пользователя
        enabled: Включены ли уведомления (опционально)
        interval_h: Интервал проверки в часах (опционально)
    """
    user_data = load_user(user_id)
    
    if enabled is not None:
        user_data["notifications"]["enabled"] = enabled
    if interval_h is not None:
        user_data["notifications"]["interval_h"] = interval_h
    
    save_user(user_id, user_data)


def has_location(user_id: int) -> bool:
    """
    Проверяет, сохранена ли локация пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        bool: True если есть координаты или город
    """
    user_data = load_user(user_id)
    return (user_data.get("lat") is not None and user_data.get("lon") is not None) or user_data.get("city") is not None


def get_subscribed_users() -> Dict[int, dict]:
    """
    Возвращает всех пользователей с включенными уведомлениями
    
    Returns:
        dict: Словарь {user_id: user_data} для подписанных пользователей
    """
    data = load_all_users()
    subscribed = {}
    
    for user_id_str, user_data in data.items():
        if user_data.get("notifications", {}).get("enabled", False):
            subscribed[int(user_id_str)] = user_data
    
    return subscribed

