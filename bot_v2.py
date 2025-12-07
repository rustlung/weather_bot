import telebot
from telebot import types
import os
import threading
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Импортируем функции из нашего погодного модуля с кэшированием
from weather_cached import (
    get_current_weather,
    get_weather_by_coordinates,
    get_coordinates,
    get_hourly_weather,
    get_air_pollution,
    analyze_air_pollution
)

# Импортируем модуль хранилища
from storage import (
    load_user,
    save_user,
    update_user_location,
    update_user_notifications,
    has_location,
    get_subscribed_users
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не установлен BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

# ============== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==============

def get_weather_emoji(description: str) -> str:
    """Возвращает эмодзи для описания погоды"""
    desc_lower = description.lower()
    if "ясно" in desc_lower or "солнц" in desc_lower:
        return "☀️"
    elif "облач" in desc_lower or "пасмурн" in desc_lower:
        return "☁️"
    elif "дождь" in desc_lower or "ливень" in desc_lower:
        return "🌧️"
    elif "гроз" in desc_lower:
        return "⛈️"
    elif "снег" in desc_lower:
        return "❄️"
    elif "туман" in desc_lower or "дымка" in desc_lower:
        return "🌫️"
    elif "переменная" in desc_lower:
        return "⛅"
    else:
        return "🌤️"

def get_wind_direction(deg: int) -> str:
    """Возвращает направление ветра по градусам"""
    directions = ["С", "СВ", "В", "ЮВ", "Ю", "ЮЗ", "З", "СЗ"]
    idx = round(deg / 45) % 8
    return directions[idx]

def format_basic_weather(weather: dict) -> str:
    """Форматирует базовую информацию о погоде"""
    emoji = get_weather_emoji(weather['weather'][0]['description'])
    wind_dir = get_wind_direction(weather['wind'].get('deg', 0))
    
    text = f"""
{emoji} <b>Погода в {weather['name']}</b>

🌡️ <b>Температура:</b> {weather['main']['temp']:.1f}°C
🤔 <b>Ощущается как:</b> {weather['main']['feels_like']:.1f}°C
💧 <b>Влажность:</b> {weather['main']['humidity']}%
🌪️ <b>Ветер:</b> {weather['wind']['speed']} м/с ({wind_dir})
📊 <b>Давление:</b> {weather['main']['pressure']} гПа
☁️ <b>Облачность:</b> {weather['clouds']['all']}%
👁️ <b>Видимость:</b> {weather.get('visibility', 'N/A')} м

📝 <b>Описание:</b> {weather['weather'][0]['description'].capitalize()}
"""
    return text

def format_extended_weather(weather: dict, air_pollution: dict) -> str:
    """Форматирует расширенную информацию о погоде"""
    emoji = get_weather_emoji(weather['weather'][0]['description'])
    wind_dir = get_wind_direction(weather['wind'].get('deg', 0))
    
    # Время восхода и заката
    sunrise = datetime.fromtimestamp(weather['sys']['sunrise']).strftime('%H:%M')
    sunset = datetime.fromtimestamp(weather['sys']['sunset']).strftime('%H:%M')
    
    # Анализ загрязнения воздуха
    pollution_components = air_pollution["list"][0]["components"]
    pollution_analysis = analyze_air_pollution(pollution_components)
    
    aqi_emoji = ["✅", "🟡", "🟠", "🔴", "☠️"][pollution_analysis['overall_index'] - 1]
    
    text = f"""
{emoji} <b>РАСШИРЕННЫЕ ДАННЫЕ: {weather['name']}</b>
{'═' * 30}

<b>🌡️ ТЕМПЕРАТУРА</b>
├ Текущая: {weather['main']['temp']:.1f}°C
├ Ощущается: {weather['main']['feels_like']:.1f}°C
├ Мин: {weather['main']['temp_min']:.1f}°C
└ Макс: {weather['main']['temp_max']:.1f}°C

<b>💨 АТМОСФЕРА</b>
├ Влажность: {weather['main']['humidity']}%
├ Давление: {weather['main']['pressure']} гПа
├ Давление (море): {weather['main'].get('sea_level', 'N/A')} гПа
└ Давление (земля): {weather['main'].get('grnd_level', 'N/A')} гПа

<b>🌪️ ВЕТЕР</b>
├ Скорость: {weather['wind']['speed']} м/с
├ Направление: {wind_dir} ({weather['wind'].get('deg', 0)}°)
└ Порывы: {weather['wind'].get('gust', 'N/A')} м/с

<b>☁️ ОБЛАЧНОСТЬ И ВИДИМОСТЬ</b>
├ Облачность: {weather['clouds']['all']}%
└ Видимость: {weather.get('visibility', 'N/A')} м

<b>🌅 СОЛНЦЕ</b>
├ Восход: {sunrise}
└ Закат: {sunset}

<b>{aqi_emoji} КАЧЕСТВО ВОЗДУХА</b>
├ Индекс: {pollution_analysis['overall_index']}/5
├ Статус: {pollution_analysis['overall_status']}
└ Проблема: {pollution_analysis['worst_pollutant']}

<b>🔬 ЗАГРЯЗНИТЕЛИ</b>
├ PM2.5: {pollution_components.get('pm2_5', 'N/A')} мкг/м³
├ PM10: {pollution_components.get('pm10', 'N/A')} мкг/м³
├ O₃: {pollution_components.get('o3', 'N/A')} мкг/м³
├ NO₂: {pollution_components.get('no2', 'N/A')} мкг/м³
├ SO₂: {pollution_components.get('so2', 'N/A')} мкг/м³
└ CO: {pollution_components.get('co', 'N/A')} мкг/м³

📝 <b>Описание:</b> {weather['weather'][0]['description'].capitalize()}
🕐 <b>Обновлено:</b> {datetime.now().strftime('%H:%M:%S')}
"""
    return text

def format_comparison(weather1: dict, weather2: dict) -> str:
    """Форматирует сравнение двух городов"""
    emoji1 = get_weather_emoji(weather1['weather'][0]['description'])
    emoji2 = get_weather_emoji(weather2['weather'][0]['description'])
    
    # Определяем, где теплее/холоднее
    temp_diff = weather1['main']['temp'] - weather2['main']['temp']
    if temp_diff > 0:
        temp_winner = f"🏆 В {weather1['name']} теплее на {abs(temp_diff):.1f}°C"
    elif temp_diff < 0:
        temp_winner = f"🏆 В {weather2['name']} теплее на {abs(temp_diff):.1f}°C"
    else:
        temp_winner = "🤝 Температура одинаковая"
    
    text = f"""
<b>⚖️ СРАВНЕНИЕ ГОРОДОВ</b>
{'═' * 35}

<b>┌{'─' * 15}┬{'─' * 15}┐</b>
<b>│</b> {emoji1} {weather1['name'][:12]:^12} <b>│</b> {emoji2} {weather2['name'][:12]:^12} <b>│</b>
<b>├{'─' * 15}┼{'─' * 15}┤</b>

<b>🌡️ Температура</b>
│ {weather1['main']['temp']:>10.1f}°C │ {weather2['main']['temp']:>10.1f}°C │

<b>🤔 Ощущается</b>
│ {weather1['main']['feels_like']:>10.1f}°C │ {weather2['main']['feels_like']:>10.1f}°C │

<b>💧 Влажность</b>
│ {weather1['main']['humidity']:>11}% │ {weather2['main']['humidity']:>11}% │

<b>🌪️ Ветер</b>
│ {weather1['wind']['speed']:>9.1f} м/с │ {weather2['wind']['speed']:>9.1f} м/с │

<b>📊 Давление</b>
│ {weather1['main']['pressure']:>9} гПа │ {weather2['main']['pressure']:>9} гПа │

<b>☁️ Облачность</b>
│ {weather1['clouds']['all']:>11}% │ {weather2['clouds']['all']:>11}% │

<b>└{'─' * 15}┴{'─' * 15}┘</b>

{temp_winner}

📝 <b>{weather1['name']}:</b> {weather1['weather'][0]['description']}
📝 <b>{weather2['name']}:</b> {weather2['weather'][0]['description']}
"""
    return text

# ============== ПРОГНОЗ НА 5 ДНЕЙ ==============

def get_forecast_days(forecast_data: dict) -> dict:
    """Группирует прогноз по дням"""
    days = {}
    for item in forecast_data['list']:
        dt = datetime.fromtimestamp(item['dt'])
        day_key = dt.strftime('%Y-%m-%d')
        day_name = dt.strftime('%d.%m (%a)')
        
        if day_key not in days:
            days[day_key] = {
                'name': day_name,
                'date': dt,
                'items': []
            }
        days[day_key]['items'].append(item)
    return days

def format_day_summary(day_data: dict) -> str:
    """Форматирует краткую сводку по дню"""
    items = day_data['items']
    temps = [item['main']['temp'] for item in items]
    min_temp = min(temps)
    max_temp = max(temps)
    
    # Находим преобладающую погоду
    descriptions = [item['weather'][0]['description'] for item in items]
    most_common = max(set(descriptions), key=descriptions.count)
    emoji = get_weather_emoji(most_common)
    
    return f"{emoji} {day_data['name']}: {min_temp:.0f}°..{max_temp:.0f}°C"

def format_day_detailed(day_data: dict, city_name: str) -> str:
    """Форматирует детальный прогноз на день"""
    text = f"<b>📅 {day_data['name']} — {city_name}</b>\n{'─' * 30}\n\n"
    
    for item in day_data['items']:
        dt = datetime.fromtimestamp(item['dt'])
        time_str = dt.strftime('%H:%M')
        emoji = get_weather_emoji(item['weather'][0]['description'])
        
        text += f"""<b>{time_str}</b> {emoji}
├ 🌡️ {item['main']['temp']:.1f}°C (ощущ. {item['main']['feels_like']:.1f}°C)
├ 💧 {item['main']['humidity']}% │ 🌪️ {item['wind']['speed']} м/с
└ {item['weather'][0]['description']}

"""
    return text

def create_forecast_keyboard(forecast_data: dict, user_id: int) -> types.InlineKeyboardMarkup:
    """Создаёт клавиатуру для выбора дня прогноза"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    days = get_forecast_days(forecast_data)
    
    for day_key, day_data in list(days.items())[:5]:
        summary = format_day_summary(day_data)
        keyboard.add(types.InlineKeyboardButton(
            text=summary,
            callback_data=f"day_{day_key}_{user_id}"
        ))
    
    # Добавляем кнопку "Назад в главное меню"
    keyboard.add(types.InlineKeyboardButton(
        text="◀️ Главное меню",
        callback_data=f"main_menu_{user_id}"
    ))
    
    return keyboard

def create_back_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    """Создаёт клавиатуру с кнопкой назад"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="◀️ Назад к списку дней",
        callback_data=f"back_forecast_{user_id}"
    ))
    return keyboard

# ============== ГЛАВНОЕ МЕНЮ ==============

def get_main_keyboard() -> types.ReplyKeyboardMarkup:
    """Создаёт главную клавиатуру"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🌤️ Текущая погода"),
        types.KeyboardButton("📅 Прогноз на 5 дней")
    )
    keyboard.add(
        types.KeyboardButton("📍 Отправить геолокацию", request_location=True),
        types.KeyboardButton("⚖️ Сравнить города")
    )
    keyboard.add(
        types.KeyboardButton("📊 Расширенные данные"),
        types.KeyboardButton("🔔 Уведомления")
    )
    return keyboard

# ============== ОБРАБОТЧИКИ КОМАНД ==============

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Приветственное сообщение"""
    text = """
<b>🌦️ Добро пожаловать в Weather Bot!</b>

Я помогу вам узнать погоду в любой точке мира.

<b>📋 Мои возможности:</b>

🌤️ <b>Текущая погода</b> — погода по городу или геолокации
📅 <b>Прогноз на 5 дней</b> — детальный прогноз с навигацией
📍 <b>Геолокация</b> — погода по вашему местоположению
⚖️ <b>Сравнение городов</b> — сравните погоду в двух городах
📊 <b>Расширенные данные</b> — все данные включая качество воздуха
🔔 <b>Уведомления</b> — подписка на погодные оповещения

<b>🎮 Команды:</b>
/weather [город] — быстрый запрос погоды
/forecast — прогноз на 5 дней
/compare [город1] [город2] — сравнение городов
/extended [город] — расширенные данные
/subscribe — подписаться на уведомления
/unsubscribe — отписаться от уведомлений

<b>💡 Inline-режим:</b>
Попробуйте написать @вашбот Москва в любом чате!

Выберите действие на клавиатуре ниже! 👇
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=get_main_keyboard())

# ============== ТЕКУЩАЯ ПОГОДА ==============

user_states = {}  # Хранит состояния пользователей для многошаговых действий
forecast_cache = {}  # Кэш прогнозов для callback обработки

@bot.message_handler(func=lambda m: m.text == "🌤️ Текущая погода")
def request_current_weather(message):
    """Запрашивает выбор способа получения погоды"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🏙️ По городу", callback_data=f"current_city_{message.from_user.id}"),
        types.InlineKeyboardButton("📍 По геолокации", callback_data=f"current_location_{message.from_user.id}")
    )
    
    bot.send_message(
        message.chat.id,
        "🌤️ <b>Текущая погода</b>\n\nВыберите способ:",
        parse_mode='HTML',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("current_city_"))
def handle_current_city(call):
    """Обработчик выбора погоды по городу"""
    user_id = int(call.data.split("_")[2])
    user_states[user_id] = "waiting_current_city"
    
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🏙️ Введите название города:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("current_location_"))
def handle_current_location(call):
    """Обработчик выбора погоды по геолокации"""
    user_id = int(call.data.split("_")[2])
    user_data = load_user(user_id)
    
    bot.answer_callback_query(call.id)
    
    if user_data.get('lat') and user_data.get('lon'):
        # Есть сохраненная локация
        show_weather_by_location(call.message.chat.id, user_data)
    else:
        # Нет сохраненной локации
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("📍 Отправить геолокацию", request_location=True))
        keyboard.add(types.KeyboardButton("❌ Отмена"))
        
        bot.send_message(
            call.message.chat.id,
            "📍 У вас нет сохранённой локации.\n\nОтправьте геолокацию:",
            reply_markup=keyboard
        )

def show_weather_by_location(chat_id: int, user_data: dict):
    """Показывает погоду по сохраненной локации"""
    try:
        weather = get_weather_by_coordinates(user_data['lat'], user_data['lon'])
        if weather:
            city_name = user_data.get('city', weather.get('name', 'Неизвестно'))
            text = f"📍 <b>Сохранённая локация: {city_name}</b>\n" + format_basic_weather(weather)
            bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=get_main_keyboard())
        else:
            bot.send_message(
                chat_id,
                "❌ Не удалось получить данные о погоде.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ Ошибка при получении погоды.",
            reply_markup=get_main_keyboard()
        )

@bot.message_handler(commands=['weather'])
def weather_command(message):
    """Обработчик команды /weather"""
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        show_city_weather(message.chat.id, args[1])
    else:
        user_states[message.from_user.id] = "waiting_current_city"
        bot.send_message(message.chat.id, "🏙️ Введите название города:")

def show_city_weather(chat_id: int, city: str):
    """Показывает погоду для города"""
    try:
        weather = get_current_weather(city=city)
        if weather:
            text = format_basic_weather(weather)
            bot.send_message(chat_id, text, parse_mode='HTML', reply_markup=get_main_keyboard())
        else:
            bot.send_message(
                chat_id,
                "❌ Не удалось получить данные о погоде. Проверьте название города.",
                reply_markup=get_main_keyboard()
            )
    except Exception as e:
        bot.send_message(
            chat_id,
            f"❌ Ошибка: город не найден.",
            reply_markup=get_main_keyboard()
        )

# ============== ПРОГНОЗ НА 5 ДНЕЙ ==============

@bot.message_handler(func=lambda m: m.text == "📅 Прогноз на 5 дней")
def request_forecast(message):
    """Запрашивает прогноз на 5 дней"""
    user_data = load_user(message.from_user.id)
    
    if user_data.get('lat') and user_data.get('lon'):
        city_name = user_data.get('city', 'Сохранённая локация')
        show_forecast(message.chat.id, message.from_user.id,
                     user_data['lat'], user_data['lon'], city_name)
    else:
        user_states[message.from_user.id] = "waiting_forecast_city"
        bot.send_message(
            message.chat.id,
            "📍 У вас нет сохранённой локации.\n\n"
            "Отправьте геолокацию или введите название города:",
            reply_markup=types.ReplyKeyboardRemove()
        )

@bot.message_handler(commands=['forecast'])
def forecast_command(message):
    """Обработчик команды /forecast"""
    user_data = load_user(message.from_user.id)
    if user_data.get('lat') and user_data.get('lon'):
        city_name = user_data.get('city', 'Сохранённая локация')
        show_forecast(message.chat.id, message.from_user.id,
                     user_data['lat'], user_data['lon'], city_name)
    else:
        user_states[message.from_user.id] = "waiting_forecast_city"
        bot.send_message(message.chat.id, "🏙️ Введите название города для прогноза:")

def show_forecast(chat_id: int, user_id: int, lat: float, lon: float, city_name: str):
    """Показывает прогноз на 5 дней"""
    try:
        forecast = get_hourly_weather(lat, lon)
        if forecast:
            # Сохраняем в кэш для callback
            forecast_cache[user_id] = {
                'data': forecast,
                'city': city_name
            }
            
            keyboard = create_forecast_keyboard(forecast, user_id)
            text = f"<b>📅 Прогноз на 5 дней — {city_name}</b>\n\nВыберите день для подробностей:"
            
            bot.send_message(chat_id, text, parse_mode='HTML',
                           reply_markup=keyboard)
            bot.send_message(chat_id, "👆 Нажмите на день выше",
                           reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, "❌ Не удалось получить прогноз.",
                           reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при получении прогноза.",
                       reply_markup=get_main_keyboard())

@bot.callback_query_handler(func=lambda call: call.data.startswith("day_"))
def handle_day_selection(call):
    """Обработчик выбора дня"""
    parts = call.data.split("_")
    day_key = parts[1]
    user_id = int(parts[2])
    
    if user_id in forecast_cache:
        forecast = forecast_cache[user_id]['data']
        city_name = forecast_cache[user_id]['city']
        days = get_forecast_days(forecast)
        
        if day_key in days:
            text = format_day_detailed(days[day_key], city_name)
            keyboard = create_back_keyboard(user_id)
            
            # Редактируем сообщение вместо отправки нового
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                parse_mode='HTML',
                reply_markup=keyboard
            )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("back_forecast_"))
def handle_back_to_forecast(call):
    """Обработчик кнопки назад к списку дней"""
    user_id = int(call.data.split("_")[2])
    
    if user_id in forecast_cache:
        forecast = forecast_cache[user_id]['data']
        city_name = forecast_cache[user_id]['city']
        
        keyboard = create_forecast_keyboard(forecast, user_id)
        text = f"<b>📅 Прогноз на 5 дней — {city_name}</b>\n\nВыберите день для подробностей:"
        
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("main_menu_"))
def handle_main_menu(call):
    """Обработчик кнопки возврата в главное меню"""
    bot.answer_callback_query(call.id, "Возвращаемся в главное меню")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(
        call.message.chat.id,
        "🏠 Главное меню",
        reply_markup=get_main_keyboard()
    )

# ============== ГЕОЛОКАЦИЯ ==============

@bot.message_handler(content_types=['location'])
def handle_location(message):
    """Обработчик получения геолокации"""
    lat = message.location.latitude
    lon = message.location.longitude
    
    # Получаем название города
    try:
        weather = get_weather_by_coordinates(lat, lon)
        city_name = weather.get('name', 'Неизвестно') if weather else 'Неизвестно'
    except:
        city_name = 'Ваша локация'
    
    # Сохраняем локацию пользователя
    update_user_location(message.from_user.id, city=city_name, lat=lat, lon=lon)
    
    # Показываем погоду
    try:
        weather = get_weather_by_coordinates(lat, lon)
        if weather:
            text = f"📍 <b>Локация сохранена!</b>\n" + format_basic_weather(weather)
            bot.send_message(message.chat.id, text, parse_mode='HTML',
                           reply_markup=get_main_keyboard())
        else:
            bot.send_message(message.chat.id,
                           "📍 Локация сохранена, но не удалось получить погоду.",
                           reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(message.chat.id,
                       f"📍 Локация сохранена. Ошибка получения погоды.",
                       reply_markup=get_main_keyboard())

# ============== СРАВНЕНИЕ ГОРОДОВ ==============

@bot.message_handler(func=lambda m: m.text == "⚖️ Сравнить города")
def request_comparison(message):
    """Запрашивает города для сравнения"""
    user_states[message.from_user.id] = "waiting_compare_cities"
    bot.send_message(
        message.chat.id,
        "⚖️ Введите два города через запятую или пробел:\n\n"
        "<i>Например: Москва, Санкт-Петербург</i>",
        parse_mode='HTML',
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(commands=['compare'])
def compare_command(message):
    """Обработчик команды /compare"""
    args = message.text.split(maxsplit=2)
    if len(args) >= 3:
        show_comparison(message.chat.id, args[1], args[2])
    else:
        user_states[message.from_user.id] = "waiting_compare_cities"
        bot.send_message(
            message.chat.id,
            "⚖️ Введите два города через запятую:\n<i>Например: Москва, Лондон</i>",
            parse_mode='HTML'
        )

def show_comparison(chat_id: int, city1: str, city2: str):
    """Показывает сравнение двух городов"""
    try:
        weather1 = get_current_weather(city=city1.strip())
        weather2 = get_current_weather(city=city2.strip())
        
        if weather1 and weather2:
            text = format_comparison(weather1, weather2)
            bot.send_message(chat_id, text, parse_mode='HTML',
                           reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id,
                           "❌ Не удалось получить данные для одного или обоих городов.",
                           reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id,
                       f"❌ Ошибка при сравнении городов. Проверьте названия.",
                       reply_markup=get_main_keyboard())

# ============== РАСШИРЕННЫЕ ДАННЫЕ ==============

@bot.message_handler(func=lambda m: m.text == "📊 Расширенные данные")
def request_extended(message):
    """Запрашивает выбор способа получения расширенных данных"""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🏙️ По городу", callback_data=f"extended_city_{message.from_user.id}"),
        types.InlineKeyboardButton("📍 По геолокации", callback_data=f"extended_location_{message.from_user.id}")
    )
    
    bot.send_message(
        message.chat.id,
        "📊 <b>Расширенные данные</b>\n\nВыберите способ:",
        parse_mode='HTML',
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("extended_city_"))
def handle_extended_city(call):
    """Обработчик выбора расширенных данных по городу"""
    user_id = int(call.data.split("_")[2])
    user_states[user_id] = "waiting_extended_city"
    
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🏙️ Введите название города:",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("extended_location_"))
def handle_extended_location(call):
    """Обработчик выбора расширенных данных по геолокации"""
    user_id = int(call.data.split("_")[2])
    user_data = load_user(user_id)
    
    bot.answer_callback_query(call.id)
    
    if user_data.get('lat') and user_data.get('lon'):
        # Есть сохраненная локация
        show_extended(call.message.chat.id, lat=user_data['lat'], lon=user_data['lon'])
    else:
        # Нет сохраненной локации
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        keyboard.add(types.KeyboardButton("📍 Отправить геолокацию", request_location=True))
        keyboard.add(types.KeyboardButton("❌ Отмена"))
        
        user_states[user_id] = "waiting_extended_location"
        bot.send_message(
            call.message.chat.id,
            "📍 У вас нет сохранённой локации.\n\nОтправьте геолокацию:",
            reply_markup=keyboard
        )

@bot.message_handler(commands=['extended'])
def extended_command(message):
    """Обработчик команды /extended"""
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        show_extended(message.chat.id, city=args[1])
    else:
        user_data = load_user(message.from_user.id)
        if user_data.get('lat') and user_data.get('lon'):
            show_extended(message.chat.id,
                         lat=user_data['lat'],
                         lon=user_data['lon'])
        else:
            user_states[message.from_user.id] = "waiting_extended_city"
            bot.send_message(message.chat.id, "🏙️ Введите название города:")

def show_extended(chat_id: int, city: str = None, lat: float = None, lon: float = None):
    """Показывает расширенные данные"""
    try:
        if city:
            coords = get_coordinates(city)
            if coords:
                lat, lon = coords
            else:
                bot.send_message(chat_id, "❌ Город не найден.",
                               reply_markup=get_main_keyboard())
                return
        
        weather = get_weather_by_coordinates(lat, lon)
        air_pollution = get_air_pollution(lat, lon)
        
        if weather and air_pollution:
            text = format_extended_weather(weather, air_pollution)
            bot.send_message(chat_id, text, parse_mode='HTML',
                           reply_markup=get_main_keyboard())
        else:
            bot.send_message(chat_id, "❌ Не удалось получить данные.",
                           reply_markup=get_main_keyboard())
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка при получении данных.",
                       reply_markup=get_main_keyboard())

# ============== УВЕДОМЛЕНИЯ ==============

@bot.message_handler(func=lambda m: m.text == "🔔 Уведомления")
def show_notifications_menu(message):
    """Показывает меню уведомлений"""
    user_data = load_user(message.from_user.id)
    notifications = user_data.get('notifications', {})
    status = "✅ Включены" if notifications.get('enabled', False) else "❌ Выключены"
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if notifications.get('enabled', False):
        keyboard.add(types.InlineKeyboardButton(
            "🔕 Отключить", callback_data="unsubscribe"))
    else:
        keyboard.add(types.InlineKeyboardButton(
            "🔔 Включить", callback_data="subscribe"))
    
    city = user_data.get('city', 'Не указана')
    location_status = f"📍 {city}" if user_data.get('lat') else "📍 Не указана"
    
    text = f"""
<b>🔔 Погодные уведомления</b>

<b>Статус:</b> {status}
<b>Локация:</b> {location_status}

Уведомления проверяют погоду каждые 2 часа и сообщают о:
• 🌧️ Приближающемся дожде или снеге
• 🌡️ Резком изменении температуры
• ⛈️ Грозах и опасных явлениях

<i>Для работы уведомлений нужно отправить геолокацию.</i>
"""
    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=keyboard)

@bot.message_handler(commands=['subscribe'])
def subscribe_command(message):
    """Команда подписки"""
    user_data = load_user(message.from_user.id)
    if not user_data.get('lat'):
        bot.send_message(
            message.chat.id,
            "❌ Сначала отправьте геолокацию для привязки уведомлений!",
            reply_markup=get_main_keyboard()
        )
        return
    
    update_user_notifications(message.from_user.id, enabled=True)
    city = user_data.get('city', 'вашей локации')
    bot.send_message(
        message.chat.id,
        f"✅ Вы подписаны на уведомления для {city}!\n"
        "Проверка погоды каждые 2 часа.",
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(commands=['unsubscribe'])
def unsubscribe_command(message):
    """Команда отписки"""
    update_user_notifications(message.from_user.id, enabled=False)
    bot.send_message(
        message.chat.id,
        "🔕 Вы отписались от уведомлений.",
        reply_markup=get_main_keyboard()
    )

@bot.callback_query_handler(func=lambda call: call.data in ["subscribe", "unsubscribe"])
def handle_subscription(call):
    """Обработчик кнопок подписки"""
    user_data = load_user(call.from_user.id)
    
    if call.data == "subscribe":
        if not user_data.get('lat'):
            bot.answer_callback_query(
                call.id,
                "❌ Сначала отправьте геолокацию!",
                show_alert=True
            )
            return
        
        update_user_notifications(call.from_user.id, enabled=True)
        bot.answer_callback_query(call.id, "✅ Уведомления включены!")
        
    else:  # unsubscribe
        update_user_notifications(call.from_user.id, enabled=False)
        bot.answer_callback_query(call.id, "🔕 Уведомления отключены!")
    
    # Обновляем сообщение
    user_data = load_user(call.from_user.id)
    notifications = user_data.get('notifications', {})
    status = "✅ Включены" if notifications.get('enabled', False) else "❌ Выключены"
    
    keyboard = types.InlineKeyboardMarkup()
    if notifications.get('enabled', False):
        keyboard.add(types.InlineKeyboardButton(
            "🔕 Отключить", callback_data="unsubscribe"))
    else:
        keyboard.add(types.InlineKeyboardButton(
            "🔔 Включить", callback_data="subscribe"))
    
    city = user_data.get('city', 'Не указана')
    location_status = f"📍 {city}" if user_data.get('lat') else "📍 Не указана"
    
    text = f"""
<b>🔔 Погодные уведомления</b>

<b>Статус:</b> {status}
<b>Локация:</b> {location_status}

Уведомления проверяют погоду каждые 2 часа и сообщают о:
• 🌧️ Приближающемся дожде или снеге
• 🌡️ Резком изменении температуры
• ⛈️ Грозах и опасных явлениях

<i>Для работы уведомлений нужно отправить геолокацию.</i>
"""
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                         parse_mode='HTML', reply_markup=keyboard)

# ============== INLINE-РЕЖИМ ==============

@bot.inline_handler(lambda query: len(query.query) >= 0)
def inline_query_handler(query):
    """Обработчик inline-запросов для быстрого поиска погоды"""
    try:
        city = query.query.strip()
        
        # Проверяем минимальную длину запроса
        if len(city) < 3:
            # Слишком короткий запрос - показываем подсказку
            results = [types.InlineQueryResultArticle(
                id='1',
                title='🔍 Введите название города',
                description='Минимум 3 символа (например: Москва, Paris, Tokyo)',
                input_message_content=types.InputTextMessageContent(
                    message_text='ℹ️ Для поиска погоды введите название города (минимум 3 символа)',
                    parse_mode='HTML'
                )
            )]
            bot.answer_inline_query(query.id, results, cache_time=1, is_personal=True)
            return
        
        # Получаем погоду для города
        weather = get_current_weather(city=city)
        
        if not weather:
            # Город не найден
            results = [types.InlineQueryResultArticle(
                id='1',
                title=f'❌ Город "{city}" не найден',
                description='Проверьте правильность написания',
                input_message_content=types.InputTextMessageContent(
                    message_text=f"❌ Город <b>{city}</b> не найден.\n\n💡 Попробуйте:\n• Проверить правописание\n• Использовать английское название\n• Указать страну (например: London, UK)",
                    parse_mode='HTML'
                )
            )]
            bot.answer_inline_query(query.id, results, cache_time=60, is_personal=True)
            return
        
        # Формируем короткое описание
        temp = weather['main']['temp']
        feels_like = weather['main']['feels_like']
        description = weather['weather'][0]['description']
        emoji = get_weather_emoji(description)
        
        # Создаем результат
        message_text = f"""
{emoji} <b>Погода в {weather['name']}</b>

🌡️ Температура: {temp:.1f}°C (ощущ. {feels_like:.1f}°C)
📝 {description.capitalize()}
💧 Влажность: {weather['main']['humidity']}%
🌪️ Ветер: {weather['wind']['speed']} м/с

<i>Отправлено через Weather Bot</i>
"""
        
        results = [types.InlineQueryResultArticle(
            id='1',
            title=f'{emoji} {weather["name"]}: {temp:.1f}°C',
            description=f'{description.capitalize()} • Ощущается как {feels_like:.1f}°C',
            input_message_content=types.InputTextMessageContent(
                message_text=message_text,
                parse_mode='HTML'
            ),
            thumbnail_url='https://cdn-icons-png.flaticon.com/512/1163/1163661.png'
        )]
        
        bot.answer_inline_query(query.id, results, cache_time=300, is_personal=True)
        
    except Exception as e:
        # В случае ошибки возвращаем информативное сообщение
        try:
            results = [types.InlineQueryResultArticle(
                id='1',
                title='⚠️ Ошибка получения данных',
                description='Попробуйте ещё раз или используйте другой город',
                input_message_content=types.InputTextMessageContent(
                    message_text=f'⚠️ Ошибка при получении погоды\n\n💡 Что можно сделать:\n• Проверьте название города\n• Попробуйте использовать английское название\n• Убедитесь в наличии интернет-соединения',
                    parse_mode='HTML'
                )
            )]
            bot.answer_inline_query(query.id, results, cache_time=10, is_personal=True)
        except:
            pass  # Игнорируем ошибки при отправке результата ошибки

# ============== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (СОСТОЯНИЯ) ==============

@bot.message_handler(func=lambda m: True, content_types=['text'])
def handle_text(message):
    """Универсальный обработчик текстовых сообщений"""
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    # Проверка на отмену
    if message.text == "❌ Отмена":
        user_states.pop(user_id, None)
        bot.send_message(
            message.chat.id,
            "❌ Операция отменена",
            reply_markup=get_main_keyboard()
        )
        return
    
    # Обработка состояний
    if state == "waiting_current_city":
        user_states.pop(user_id, None)
        show_city_weather(message.chat.id, message.text)
        
    elif state == "waiting_forecast_city":
        user_states.pop(user_id, None)
        try:
            coords = get_coordinates(message.text)
            if coords:
                show_forecast(message.chat.id, user_id, coords[0], coords[1], message.text)
            else:
                bot.send_message(message.chat.id, "❌ Город не найден.",
                               reply_markup=get_main_keyboard())
        except:
            bot.send_message(message.chat.id, "❌ Ошибка поиска города.",
                           reply_markup=get_main_keyboard())
            
    elif state == "waiting_compare_cities":
        user_states.pop(user_id, None)
        # Разделяем по запятой или пробелу
        if "," in message.text:
            cities = message.text.split(",")
        else:
            cities = message.text.split()
        
        if len(cities) >= 2:
            show_comparison(message.chat.id, cities[0], cities[1])
        else:
            bot.send_message(message.chat.id,
                           "❌ Укажите два города через запятую.",
                           reply_markup=get_main_keyboard())
            
    elif state == "waiting_extended_city":
        user_states.pop(user_id, None)
        show_extended(message.chat.id, city=message.text)
    
    elif state == "waiting_extended_location":
        # Ожидаем геолокацию, не текст
        bot.send_message(
            message.chat.id,
            "📍 Пожалуйста, отправьте геолокацию используя кнопку",
            reply_markup=get_main_keyboard()
        )
        user_states.pop(user_id, None)
        
    else:
        # Если не в состоянии и не команда — возвращаем в меню
        bot.send_message(
            message.chat.id,
            "🤔 Не понял команду. Используйте кнопки меню или /help",
            reply_markup=get_main_keyboard()
        )

# ============== СИСТЕМА УВЕДОМЛЕНИЙ (ФОНОВЫЙ ПОТОК) ==============

def check_weather_alerts():
    """Проверяет погоду для подписчиков и отправляет уведомления"""
    while True:
        try:
            subscribed_users = get_subscribed_users()
            
            for user_id, user_data in subscribed_users.items():
                if not user_data.get('lat') or not user_data.get('lon'):
                    continue
                
                try:
                    lat = user_data['lat']
                    lon = user_data['lon']
                    city_name = user_data.get('city', 'вашем местоположении')
                    
                    # Получаем прогноз
                    forecast = get_hourly_weather(lat, lon)
                    if not forecast:
                        continue
                    
                    current_weather = get_weather_by_coordinates(lat, lon)
                    
                    alerts = []
                    
                    # Проверяем ближайшие 12 часов
                    for item in forecast['list'][:4]:  # 4 записи = 12 часов
                        weather_main = item['weather'][0]['main'].lower()
                        description = item['weather'][0]['description']
                        dt = datetime.fromtimestamp(item['dt'])
                        time_str = dt.strftime('%H:%M')
                        
                        # Проверяем опасные явления
                        if 'rain' in weather_main or 'дождь' in description:
                            alerts.append(f"🌧️ Ожидается дождь в {time_str}")
                        elif 'snow' in weather_main or 'снег' in description:
                            alerts.append(f"❄️ Ожидается снег в {time_str}")
                        elif 'thunderstorm' in weather_main or 'гроз' in description:
                            alerts.append(f"⛈️ Ожидается гроза в {time_str}")
                    
                    # Проверяем резкое изменение температуры
                    if current_weather and forecast['list']:
                        current_temp = current_weather['main']['temp']
                        future_temp = forecast['list'][3]['main']['temp']  # через 9 часов
                        temp_diff = future_temp - current_temp
                        
                        if abs(temp_diff) >= 5:
                            direction = "потеплеет" if temp_diff > 0 else "похолодает"
                            alerts.append(f"🌡️ К вечеру {direction} на {abs(temp_diff):.0f}°C")
                    
                    # Отправляем уведомления
                    if alerts:
                        # Убираем дубликаты
                        alerts = list(dict.fromkeys(alerts))
                        
                        text = f"<b>⚠️ Погодное уведомление — {city_name}</b>\n\n"
                        text += "\n".join(alerts[:5])  # Максимум 5 оповещений
                        text += "\n\n<i>Отключить: /unsubscribe</i>"
                        
                        try:
                            bot.send_message(user_id, text, parse_mode='HTML')
                        except:
                            pass  # Пользователь мог заблокировать бота
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            pass
        
        # Ждём 2 часа
        time.sleep(7200)

# Запускаем фоновый поток для уведомлений
notification_thread = threading.Thread(target=check_weather_alerts, daemon=True)
notification_thread.start()

# ============== ЗАПУСК БОТА ==============

if __name__ == "__main__":
    print("🤖 Бот запущен...")
    print("📡 Ожидание сообщений...")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

