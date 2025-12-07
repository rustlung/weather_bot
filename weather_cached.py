"""
Модуль-обертка для weather_app_v2.py с поддержкой кэширования
Все запросы к API кэшируются на 10 минут
"""

from weather_app_v2 import (
    get_weather_by_coordinates as _get_weather_by_coordinates,
    get_coordinates as _get_coordinates,
    get_hourly_weather as _get_hourly_weather,
    get_air_pollution as _get_air_pollution,
    analyze_air_pollution
)
from cache import get_cached, set_cached
from typing import Optional, Tuple


def get_weather_by_coordinates(latitude: float, longitude: float) -> Optional[dict]:
    """
    Получает текущую погоду по координатам с использованием кэша
    
    Args:
        latitude: Широта
        longitude: Долгота
        
    Returns:
        dict: Данные о погоде или None
    """
    # Пытаемся получить из кэша
    cached_data = get_cached(latitude, longitude, "weather")
    if cached_data:
        return cached_data
    
    # Если в кэше нет, запрашиваем у API
    data = _get_weather_by_coordinates(latitude, longitude)
    if data:
        set_cached(latitude, longitude, "weather", data)
    
    return data


def get_hourly_weather(latitude: float, longitude: float) -> Optional[dict]:
    """
    Получает почасовой прогноз по координатам с использованием кэша
    
    Args:
        latitude: Широта
        longitude: Долгота
        
    Returns:
        dict: Данные прогноза или None
    """
    # Пытаемся получить из кэша
    cached_data = get_cached(latitude, longitude, "forecast")
    if cached_data:
        return cached_data
    
    # Если в кэше нет, запрашиваем у API
    data = _get_hourly_weather(latitude, longitude)
    if data:
        set_cached(latitude, longitude, "forecast", data)
    
    return data


def get_air_pollution(latitude: float, longitude: float) -> Optional[dict]:
    """
    Получает данные о загрязнении воздуха по координатам с использованием кэша
    
    Args:
        latitude: Широта
        longitude: Долгота
        
    Returns:
        dict: Данные о загрязнении или None
    """
    # Пытаемся получить из кэша
    cached_data = get_cached(latitude, longitude, "air_pollution")
    if cached_data:
        return cached_data
    
    # Если в кэше нет, запрашиваем у API
    data = _get_air_pollution(latitude, longitude)
    if data:
        set_cached(latitude, longitude, "air_pollution", data)
    
    return data


def get_coordinates(city: str) -> Optional[Tuple[float, float]]:
    """
    Получает координаты города (без кэширования, т.к. используется редко)
    
    Args:
        city: Название города
        
    Returns:
        tuple: (latitude, longitude) или None
    """
    return _get_coordinates(city)


def get_current_weather(city: str = None, latitude: float = None, longitude: float = None) -> Optional[dict]:
    """
    Получает текущую погоду по городу или координатам
    
    Args:
        city: Название города (опционально)
        latitude: Широта (опционально)
        longitude: Долгота (опционально)
        
    Returns:
        dict: Данные о погоде или None
    """
    if city:
        coords = get_coordinates(city)
        if coords:
            latitude, longitude = coords
            return get_weather_by_coordinates(latitude, longitude)
        return None
    
    if latitude and longitude:
        return get_weather_by_coordinates(latitude, longitude)
    
    return None


# Экспортируем analyze_air_pollution без изменений
__all__ = [
    'get_current_weather',
    'get_weather_by_coordinates',
    'get_coordinates',
    'get_hourly_weather',
    'get_air_pollution',
    'analyze_air_pollution'
]

