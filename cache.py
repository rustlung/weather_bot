"""
Модуль для кэширования API запросов к OpenWeatherMap
Кэш хранится в ./.cache/*.json и действителен 10 минут
"""

import os
import json
import hashlib
import time
from typing import Optional, Any, Dict

CACHE_DIR = ".cache"
CACHE_DURATION = 600  # 10 минут в секундах


def _ensure_cache_dir():
    """Создает директорию для кэша если её нет"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def _get_cache_key(lat: float, lon: float, endpoint: str) -> str:
    """
    Генерирует ключ кэша на основе координат и endpoint
    
    Args:
        lat: Широта
        lon: Долгота
        endpoint: Название API endpoint (weather, forecast, air_pollution и т.д.)
        
    Returns:
        str: MD5 хэш для использования в качестве имени файла
    """
    key_string = f"{lat:.4f}_{lon:.4f}_{endpoint}"
    return hashlib.md5(key_string.encode()).hexdigest()


def _get_cache_path(cache_key: str) -> str:
    """Возвращает полный путь к файлу кэша"""
    return os.path.join(CACHE_DIR, f"{cache_key}.json")


def get_cached(lat: float, lon: float, endpoint: str) -> Optional[Dict[str, Any]]:
    """
    Получает данные из кэша если они не устарели
    
    Args:
        lat: Широта
        lon: Долгота
        endpoint: Название API endpoint
        
    Returns:
        dict или None: Данные из кэша или None если кэш отсутствует/устарел
    """
    _ensure_cache_dir()
    
    cache_key = _get_cache_key(lat, lon, endpoint)
    cache_path = _get_cache_path(cache_key)
    
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cache_data = json.load(f)
        
        # Проверяем время кэша
        cached_time = cache_data.get("cached_at", 0)
        current_time = time.time()
        
        if current_time - cached_time > CACHE_DURATION:
            # Кэш устарел, удаляем файл
            os.remove(cache_path)
            return None
        
        return cache_data.get("data")
        
    except (json.JSONDecodeError, KeyError, OSError):
        # Если файл поврежден, удаляем его
        try:
            os.remove(cache_path)
        except OSError:
            pass
        return None


def set_cached(lat: float, lon: float, endpoint: str, data: Dict[str, Any]) -> None:
    """
    Сохраняет данные в кэш
    
    Args:
        lat: Широта
        lon: Долгота
        endpoint: Название API endpoint
        data: Данные для кэширования
    """
    _ensure_cache_dir()
    
    cache_key = _get_cache_key(lat, lon, endpoint)
    cache_path = _get_cache_path(cache_key)
    
    cache_data = {
        "cached_at": time.time(),
        "lat": lat,
        "lon": lon,
        "endpoint": endpoint,
        "data": data
    }
    
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        # Если не удалось сохранить кэш, просто игнорируем
        pass


def clear_cache() -> int:
    """
    Очищает весь кэш
    
    Returns:
        int: Количество удаленных файлов
    """
    if not os.path.exists(CACHE_DIR):
        return 0
    
    count = 0
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".json"):
            try:
                os.remove(os.path.join(CACHE_DIR, filename))
                count += 1
            except OSError:
                pass
    
    return count


def clear_old_cache() -> int:
    """
    Очищает только устаревший кэш
    
    Returns:
        int: Количество удаленных файлов
    """
    if not os.path.exists(CACHE_DIR):
        return 0
    
    count = 0
    current_time = time.time()
    
    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith(".json"):
            continue
            
        filepath = os.path.join(CACHE_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            cached_time = cache_data.get("cached_at", 0)
            if current_time - cached_time > CACHE_DURATION:
                os.remove(filepath)
                count += 1
                
        except (json.JSONDecodeError, KeyError, OSError):
            # Если файл поврежден, удаляем его
            try:
                os.remove(filepath)
                count += 1
            except OSError:
                pass
    
    return count


def get_cache_stats() -> Dict[str, Any]:
    """
    Возвращает статистику кэша
    
    Returns:
        dict: Статистика с количеством файлов, размером и т.д.
    """
    if not os.path.exists(CACHE_DIR):
        return {
            "total_files": 0,
            "total_size_bytes": 0,
            "valid_files": 0,
            "expired_files": 0
        }
    
    stats = {
        "total_files": 0,
        "total_size_bytes": 0,
        "valid_files": 0,
        "expired_files": 0
    }
    
    current_time = time.time()
    
    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith(".json"):
            continue
        
        filepath = os.path.join(CACHE_DIR, filename)
        stats["total_files"] += 1
        
        try:
            stats["total_size_bytes"] += os.path.getsize(filepath)
            
            with open(filepath, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            
            cached_time = cache_data.get("cached_at", 0)
            if current_time - cached_time > CACHE_DURATION:
                stats["expired_files"] += 1
            else:
                stats["valid_files"] += 1
                
        except (json.JSONDecodeError, KeyError, OSError):
            pass
    
    return stats

