from ast import main
import requests
from dotenv import load_dotenv
import os
import json

load_dotenv()
API_KEY = os.getenv("API_KEY")

def get_current_weather(city: str=None, latitude: float=None, longitude: float=None) -> dict:
    if city:
        print(f"Получаем погоду для города {city}")
        latitude, longitude = get_coordinates(city)
        weather = get_weather_by_coordinates(latitude, longitude)
        return weather

    if latitude and longitude:
        print(f"Получаем погоду для координат {latitude}, {longitude}")
        return get_weather_by_coordinates(latitude, longitude)

def get_weather_by_coordinates(latitude: float, longitude: float) -> dict:
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return print(f"Ошибка: {response.status_code}")

def get_coordinates(city: str) -> tuple[float, float]:
    url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={API_KEY}&limit=1"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()[0]['lat'], response.json()[0]['lon']
    else:
        print(f"Ошибка: {response.status_code}")
        return  None

def get_hourly_weather(latitude: float, longitude: float) -> dict:
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code}")
        return None

def get_air_pollution(latitude: float, longitude: float) -> dict:
    url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={latitude}&lon={longitude}&appid={API_KEY}&units=metric&lang=ru"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Ошибка: {response.status_code}")
        return None

def analyze_air_pollution(air_pollution: dict) -> dict:
    """
    Анализирует данные о загрязнении воздуха и возвращает статус качества.
    air_pollution = {"co": 100.25, "no": 0.09, "no2": 1.14, "o3": 59.12, "so2": 0.73, "pm2_5": 0.5, "pm10": 0.5, "nh3": 0.15}
    """
    
    # Таблица пороговых значений для каждого загрязнителя (в мкг/м³)
    # Формат: [(max_value, index, status_name), ...]
    thresholds = {
        "so2": [
            (20, 1, "Good"),
            (80, 2, "Fair"),
            (250, 3, "Moderate"),
            (350, 4, "Poor"),
            (float('inf'), 5, "Very Poor")
        ],
        "no2": [
            (40, 1, "Good"),
            (70, 2, "Fair"),
            (150, 3, "Moderate"),
            (200, 4, "Poor"),
            (float('inf'), 5, "Very Poor")
        ],
        "pm10": [
            (20, 1, "Good"),
            (50, 2, "Fair"),
            (100, 3, "Moderate"),
            (200, 4, "Poor"),
            (float('inf'), 5, "Very Poor")
        ],
        "pm2_5": [
            (10, 1, "Good"),
            (25, 2, "Fair"),
            (50, 3, "Moderate"),
            (75, 4, "Poor"),
            (float('inf'), 5, "Very Poor")
        ],
        "o3": [
            (60, 1, "Good"),
            (100, 2, "Fair"),
            (140, 3, "Moderate"),
            (180, 4, "Poor"),
            (float('inf'), 5, "Very Poor")
        ],
        "co": [
            (4400, 1, "Good"),
            (9400, 2, "Fair"),
            (12400, 3, "Moderate"),
            (15400, 4, "Poor"),
            (float('inf'), 5, "Very Poor")
        ]
    }
    
    # Названия статусов на русском
    status_names = {
        1: "Хорошее",
        2: "Удовлетворительное", 
        3: "Умеренное",
        4: "Плохое",
        5: "Очень плохое"
    }
    
    # Названия загрязнителей на русском
    pollutant_names = {
        "so2": "Диоксид серы (SO₂)",
        "no2": "Диоксид азота (NO₂)",
        "pm10": "Взвешенные частицы (PM10)",
        "pm2_5": "Мелкие частицы (PM2.5)",
        "o3": "Озон (O₃)",
        "co": "Угарный газ (CO)",
        "no": "Оксид азота (NO)",
        "nh3": "Аммиак (NH₃)"
    }
    
    def get_pollutant_index(pollutant: str, value: float) -> tuple:
        """Возвращает индекс и статус для конкретного загрязнителя"""
        if pollutant not in thresholds:
            return None, None, None
        
        for max_val, index, status in thresholds[pollutant]:
            if value < max_val:
                return index, status, max_val
        return 5, "Very Poor", float('inf')
    
    # Анализ каждого загрязнителя
    detailed_info = {}
    max_index = 1
    worst_pollutant = None
    
    for pollutant, value in air_pollution.items():
        if pollutant in thresholds:
            index, status_en, threshold = get_pollutant_index(pollutant, value)
            detailed_info[pollutant] = {
                "value": value,
                "unit": "мкг/м³",
                "index": index,
                "status": status_names[index],
                "status_en": status_en,
                "threshold": threshold if threshold != float('inf') else "≥" + str(thresholds[pollutant][-2][0])
            }
            
            if index > max_index:
                max_index = index
                worst_pollutant = pollutant
        else:
            # NO и NH3 не влияют на AQI, но добавляем их информацию
            if pollutant == "no":
                detailed_info[pollutant] = {
                    "value": value,
                    "unit": "мкг/м³",
                    "note": "Не влияет на расчёт AQI (допустимый диапазон: 0.1-100)"
                }
            elif pollutant == "nh3":
                detailed_info[pollutant] = {
                    "value": value,
                    "unit": "мкг/м³",
                    "note": "Не влияет на расчёт AQI (допустимый диапазон: 0.1-200)"
                }
    
    # Формируем результат
    result = {
        "overall_index": max_index,
        "overall_status": status_names[max_index],
        "overall_status_en": ["Good", "Fair", "Moderate", "Poor", "Very Poor"][max_index - 1],
        "worst_pollutant": pollutant_names.get(worst_pollutant, None) if worst_pollutant else "Все показатели в норме",
        "detailed_info": detailed_info
    }
    
    return result


def print_air_quality_report(air_pollution_response: dict):
    """Выводит красивый отчёт о качестве воздуха"""
    # Извлекаем компоненты загрязнения из ответа API
    # API возвращает структуру: {"list": [{"components": {...}, "main": {"aqi": ...}}]}
    components = air_pollution_response["list"][0]["components"]
    analysis = analyze_air_pollution(components)
    
    print("\n" + "="*50)
    print("       ОТЧЁТ О КАЧЕСТВЕ ВОЗДУХА")
    print("="*50)
    print(f"\n🌍 Общий индекс качества: {analysis['overall_index']}/5")
    print(f"📊 Статус: {analysis['overall_status']} ({analysis['overall_status_en']})")
    print(f"⚠️  Определяющий загрязнитель: {analysis['worst_pollutant']}")
    
    print("\n" + "-"*50)
    print("        ДЕТАЛЬНАЯ ИНФОРМАЦИЯ")
    print("-"*50)
    
    pollutant_names = {
        "so2": "SO₂ (Диоксид серы)",
        "no2": "NO₂ (Диоксид азота)",
        "pm10": "PM10 (Крупные частицы)",
        "pm2_5": "PM2.5 (Мелкие частицы)",
        "o3": "O₃ (Озон)",
        "co": "CO (Угарный газ)",
        "no": "NO (Оксид азота)",
        "nh3": "NH₃ (Аммиак)"
    }
    
    for pollutant, info in analysis['detailed_info'].items():
        name = pollutant_names.get(pollutant, pollutant)
        if "index" in info:
            status_emoji = ["✅", "🟡", "🟠", "🔴", "☠️"][info['index'] - 1]
            print(f"\n{status_emoji} {name}")
            print(f"   Значение: {info['value']} {info['unit']}")
            print(f"   Статус: {info['status']} (индекс {info['index']})")
        else:
            print(f"\nℹ️  {name}")
            print(f"   Значение: {info['value']} {info['unit']}")
            print(f"   {info['note']}")
    
    print("\n" + "="*50)

if __name__ == "__main__":
    air_pollution = get_air_pollution(55.7558, 37.6176)
    print(air_pollution)
    print_air_quality_report(air_pollution)
    #print("Добро пожаловать в программу погоды!")
    #print("1. Получить погоду по городу")
    #print("2. Получить погоду по координатам")
    #print("0. Выйти")
    #choice = input("Выберите опцию: ")
    #if choice == "1":
    #    city = input("Введите город: ")
    #    weather = get_current_weather(city)
    #    print(f"Текущая погода в городе {weather['name']}: {weather['main']['temp']}°C, {weather['weather'][0]['description']}")
    #elif choice == "2":
     #   latitude = input("Введите широту: ")
     #   longitude = input("Введите долготу: ")
     #   weather = get_current_weather(latitude, longitude)
     #   print(f"Текущая погода в городе {weather['name']}: {weather['main']['temp']}°C, {weather['weather'][0]['description']}")
    #elif choice == "0":
    #    print("До свидания!")
    #else:
    #    print("Неверный выбор")

