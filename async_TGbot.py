from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup
import os
import json
import openai
import aiohttp
import requests
from moviepy.editor import *
import matplotlib.pyplot as plt
import io
from telegram import InputFile
from datetime import datetime

# Переменные окружения
load_dotenv()
TOKEN = os.environ.get("TOKEN")
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY")
GPT_SECRET_KEY = os.environ.get("GPT_SECRET_KEY")

openai.api_key = GPT_SECRET_KEY

# Состояние для ввода веса
ENTER_WEIGHT = range(1)

# Хранилище данных пользователей
users = {}

# Статусы для диалога
WEIGHT, HEIGHT, AGE, ACTIVITY, CITY = range(5)

# Функция команды /start
async def start(update, context):
    # Создаем кнопку "Start"
    keyboard = [["Start"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    # Отправляем приветственное сообщение и прикрепляем кнопку
    await update.message.reply_text(
        "Привет! 🤖 Я помогу рассчитать нормы воды 💧, калорий 🍏, трекать активность 🏃‍♂️ и распознать эмоции 😃. "
        "Для настройки профиля используйте команду /set_profile.\n\n"
        "Далее будут доступны следующие команды: /show_progress - просмотр графиков, /log_water - фиксация потребления воды, /log_food - фиксация потребления еды, /log_workout - фиксация тренировок, /fer - распознание эмоций по фото, /check_progress - проверка прогресса.\n\n"
        "Отправьте фотографию лица в любое время для автоматического распознавания эмоции.\n\n"
        "Также вы можете задать любой вопрос ChatGPT с помощью команды /chat <ваш вопрос>.",
        reply_markup=reply_markup
    )

# Настройка профиля пользователя
async def set_profile(update, context):
    await update.message.reply_text("Введите ваш вес (в кг):")
    return WEIGHT

async def weight(update, context):
    context.user_data["weight"] = int(update.message.text)
    await update.message.reply_text("Введите ваш рост (в см):")
    return HEIGHT

async def height(update, context):
    context.user_data["height"] = int(update.message.text)
    await update.message.reply_text("Введите ваш возраст:")
    return AGE

async def age(update, context):
    context.user_data["age"] = int(update.message.text)
    await update.message.reply_text("Сколько минут активности у вас в день?")
    return ACTIVITY

async def activity(update, context):
    context.user_data["activity"] = int(update.message.text)
    await update.message.reply_text("В каком городе вы находитесь?")
    return CITY

async def city(update, context):
    user_id = update.message.from_user.id
    context.user_data["city"] = update.message.text
    users[user_id] = {
        "weight": context.user_data["weight"],
        "height": context.user_data["height"],
        "age": context.user_data["age"],
        "activity": context.user_data["activity"],
        "city": context.user_data["city"],
        "logged_water": 0,
        "logged_calories": 0,
        "burned_calories": 0
    }

    await update.message.reply_text("Профиль успешно настроен!")
    return ConversationHandler.END

# Распознавание эмоций
def get_recommendations(emotion_data, temperature):
    # Определяем преобладающую эмоцию
    dominant_emotion = max(emotion_data, key=emotion_data.get)
    recommendations = {
        "angry": {
            "activity": "бокс или интенсивный бег",
            "duration": 40,
            "calories": 400
        },

        "disgust": {
            "activity": "йога или пилатес",
            "duration": 30,
            "calories": 150
        },

        "fear": {
            "activity": "легкая пробежка или прогулка",
            "duration": 20,
            "calories": 100
        },

        "happy": {
            "activity": "танцы или командные виды спорта",
            "duration": 60,
            "calories": 300
        },

        "neutral": {
            "activity": "ходьба или растяжка",
            "duration": 20,
            "calories": 50
        },

        "sad": {
            "activity": "йога или прогулка на свежем воздухе",
            "duration": 30,
            "calories": 100
        },

        "surprise": {
            "activity": "игра в волейбол или быстрые кардио-упражнения",
            "duration": 25,
            "calories": 200
        }
    }

    recommendation = recommendations.get(dominant_emotion, {"activity": "отдых", "duration": 0, "calories": 0})

    # Учет температуры
    if temperature > 30:
        recommendation["activity"] += " (в помещении)"
    elif temperature < 10:
        recommendation["activity"] += " (в теплом месте или зале)"
    return dominant_emotion, recommendation

# Обновим функцию fer для обработки эмоций и выдачи рекомендаций
async def fer(update, context):
    await update.message.reply_text('Мы получили от тебя фотографию. Идёт распознавание эмоций...')

    # Получаем ссылку на файл изображения
    imageurl = await update.message.document.get_file()
    headers = {'Content-type': 'application/json'}
    data = {'url': imageurl['file_path']}

    async with aiohttp.request(
        method='POST', 
        url='http://127.0.0.1:5000/detect_emotion', 
        data=json.dumps(data), 
        headers=headers
    ) as response:
        res = await response.json()

        # Получаем эмоции
        emotion_data = res.get("message", {})

        # Получаем город пользователя
        user_id = update.message.from_user.id
        if user_id in users:
            city = users[user_id].get("city", "Москва")
        else:
            city = "Москва"

        # Получаем температуру
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={WEATHER_API_KEY}"
        weather_response = requests.get(weather_url).json()
        temperature = weather_response.get("main", {}).get("temp", 20)

        # Рекомендации на основе эмоций и температуры
        dominant_emotion, recommendation = get_recommendations(emotion_data, temperature)

        await update.message.reply_text(
            f"Преобладающая эмоция: {dominant_emotion.capitalize()}\n"
            f"Рекомендация:\n"
            f"- Упражнение: {recommendation['activity']}\n"
            f"- Продолжительность: {recommendation['duration']} минут\n"
            f"- Сожженные калории: {recommendation['calories']} ккал\n"
            f"Текущая температура в городе {city}: {temperature}°C."
        )

# Расчёт норм воды и калорий
def calculate_water_and_calories(user):
    base_water = user["weight"] * 30  # мл на кг
    extra_water = (user["activity"] // 30) * 500  # 500 мл за каждые 30 мин активности

    # Получение текущей температуры
    city = user["city"]
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&units=metric&appid={WEATHER_API_KEY}"
    response = requests.get(weather_url).json()
    temperature = response.get("main", {}).get("temp", 20)
    if temperature > 25:
        extra_water += 500
    water_goal = base_water + extra_water

    # Формула расчёта калорий
    calorie_goal = (10 * user["weight"] + 6.25 * user["height"] - 5 * user["age"] + 200) + (user["activity"] * 5)
    return water_goal, calorie_goal



async def get_answer(text):
       completion = await openai.ChatCompletion.acreate(
           model="gpt-3.5-turbo",
           messages=[{"role": "user", "content": text}]
       )
       return completion.choices[0].message["content"]

async def chat(update, context):
       try:
           user_message = update.message.text.replace('/chat', '').strip()
           if not user_message:
               await update.message.reply_text("Введите ваш запрос после команды /chat.")
               return
           response = await get_answer(user_message)
           await update.message.reply_text(response)
       except Exception as e:
           await update.message.reply_text("Произошла ошибка при обработке вашего запроса. Попробуйте еще раз.")

# Функция для построения графиков прогресса
def plot_progress_with_dates(data, dates, title, y_label):
    plt.figure(figsize=(10, 6))
    plt.plot(dates, data, marker='o', linestyle='-', color='blue')
    plt.title(title)
    plt.xlabel("Дата")
    plt.ylabel(y_label)
    plt.xticks(rotation=45)  # Поворачиваем метки на оси X для лучшей читаемости
    plt.grid(True)

    # Сохраняем график в буфер
    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()
    return buffer

# Функция для отображения графиков прогресса
async def show_progress(update, context):
    user_id = update.message.from_user.id
    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль командой /set_profile.")
        return

    # Получение данных для графиков
    logged_water = users[user_id].get("logged_water_history", [])
    water_dates = users[user_id].get("logged_water_dates", [])
    logged_calories = users[user_id].get("logged_calories_history", [])
    calorie_dates = users[user_id].get("logged_calories_dates", [])

    if not logged_water and not logged_calories:
        await update.message.reply_text("Данные о прогрессе отсутствуют.")
        return

    if logged_water:
        water_plot = plot_progress_with_dates(logged_water, water_dates, "Прогресс по воде", "Вода (мл)")
        await update.message.reply_photo(photo=InputFile(water_plot, filename="water_progress.png"))

    if logged_calories:
        calories_plot = plot_progress_with_dates(logged_calories, calorie_dates, "Прогресс по калориям", "Калории (ккал)")
        await update.message.reply_photo(photo=InputFile(calories_plot, filename="calories_progress.png"))

# Логирование воды
async def log_water(update, context):
    user_id = update.message.from_user.id
    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль командой /set_profile.")
        return

    try:
        amount = int(context.args[0])
        users[user_id]["logged_water"] += amount
        # Добавляем данные в историю прогресса
        if "logged_water_history" not in users[user_id]:
            users[user_id]["logged_water_history"] = []
            users[user_id]["logged_water_dates"] = []
        users[user_id]["logged_water_history"].append(users[user_id]["logged_water"])
        users[user_id]["logged_water_dates"].append(datetime.now().strftime("%d-%m-%Y"))
        water_goal, _ = calculate_water_and_calories(users[user_id])
        remaining_water = max(0, water_goal - users[user_id]["logged_water"])
        await update.message.reply_text(f"Выпито: {users[user_id]['logged_water']} мл из {water_goal} мл.\nОсталось: {remaining_water} мл.")

    except (IndexError, ValueError):
        await update.message.reply_text("Используйте команду в формате: /log_water <количество>.")

# Создаём объект Application 
application = Application.builder().token(TOKEN).build()

# Функция для получения данных о продукте
async def get_food_info(food_name):
    url = "https://trackapi.nutritionix.com/v2/natural/nutrients"
    headers = {
        "x-app-id": "af9ed57e",
        "x-app-key": "bc4bbfbb81351dfbde8884f8ddf9c859",
        "Content-Type": "application/json"
    }

    payload = {"query": food_name}

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=json.dumps(payload)) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                return {"error": "Не удалось получить данные о продукте"}

# Первый шаг: ввод названия продукта
async def log_food(update, context):
    user_input = " ".join(context.args)
    if not user_input:
        await update.message.reply_text("Пожалуйста, введите название продукта. Пример: /log_food яблоко")
        return ConversationHandler.END
    await update.message.reply_text(f"Ищу информацию о продукте '{user_input}'...")
    food_data = await get_food_info(user_input)
    if "error" in food_data:
        await update.message.reply_text("Не удалось получить данные о продукте. Попробуйте позже.")
        return ConversationHandler.END

    # Сохраняем информацию о продукте в контексте
    context.user_data["food_data"] = food_data["foods"][0]
    food = food_data["foods"][0]
    food_name = food["food_name"]
    calories = food["nf_calories"]
    weight = food["serving_weight_grams"]

    await update.message.reply_text(
        f"{food_name.capitalize()} — {calories} ккал на {weight} г. Сколько грамм вы съели?"
    )

    return ENTER_WEIGHT

# Второй шаг: ввод веса
async def log_food_weight(update, context):
    try:
        weight = float(update.message.text)  # Получаем вес от пользователя
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число.")
        return ENTER_WEIGHT

    # Данные о продукте из контекста
    food = context.user_data["food_data"]
    calories_per_gram = food["nf_calories"] / food["serving_weight_grams"]
    total_calories = calories_per_gram * weight
    user_id = update.message.from_user.id
    if user_id not in users:
        users[user_id] = {
            "weight": 0,
            "height": 0,
            "age": 0,
            "activity": 0,
            "city": "",
            "logged_water": 0,
            "logged_calories": 0,
            "burned_calories": 0,
        }

    users[user_id]["logged_calories"] += total_calories

    # Добавляем данные в историю прогресса
    if "logged_calories_history" not in users[user_id]:
        users[user_id]["logged_calories_history"] = []
        users[user_id]["logged_calories_dates"] = []
    users[user_id]["logged_calories_history"].append(users[user_id]["logged_calories"])
    users[user_id]["logged_calories_dates"].append(datetime.now().strftime("%d-%m-%Y"))
    await update.message.reply_text(f"Записано: {total_calories:.1f} ккал.")
    return ConversationHandler.END

# Обработчик отмены
async def cancel(update, context):
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END

# Регистрация ConversationHandler
application.add_handler(ConversationHandler(
    entry_points=[CommandHandler("log_food", log_food)],
    states={
        ENTER_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_food_weight)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
))

# Логирование тренировок
async def log_workout(update, context):
    user_id = update.message.from_user.id
    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль командой /set_profile.")
        return
    try:
        workout_type = context.args[0]
        duration = int(context.args[1])
        burned_calories = duration * 10  # Пример расчёта
        extra_water = (duration // 30) * 200
        users[user_id]["burned_calories"] += burned_calories
        users[user_id]["logged_water"] += extra_water
        await update.message.reply_text(f"{workout_type.capitalize()} {duration} минут — {burned_calories} ккал. Выпейте дополнительно {extra_water} мл воды.")
    except (IndexError, ValueError):
        await update.message.reply_text("Используйте команду в формате: /log_workout <тип тренировки> <время (мин)>.")

# Проверка прогресса
async def check_progress(update, context):
    user_id = update.message.from_user.id
    if user_id not in users:
        await update.message.reply_text("Сначала настройте профиль командой /set_profile.")
        return
    water_goal, calorie_goal = calculate_water_and_calories(users[user_id])
    logged_water = users[user_id].get("logged_water", 0)
    logged_calories = users[user_id].get("logged_calories", 0)
    burned_calories = users[user_id].get("burned_calories", 0)
    balance = logged_calories - burned_calories
    await update.message.reply_text(
        f"Прогресс:\n\n"
        f"Вода:\n- Выпито: {logged_water} мл из {water_goal} мл.\n- Осталось: {max(0, water_goal - logged_water)} мл.\n\n"
        f"Калории:\n- Потреблено: {logged_calories:.1f} ккал из {calorie_goal:.1f} ккал.\n"
        f"- Сожжено: {burned_calories:.1f} ккал.\n"
        f"- Баланс: {balance:.1f} ккал."
    )

# Основная функция
def main():
    application = Application.builder().token(TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("set_profile", set_profile)],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, activity)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, city)],
        },
        fallbacks=[]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.IMAGE, fer))
    application.add_handler(CommandHandler("show_progress", show_progress))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("chat", chat, block=False))
    application.add_handler(CommandHandler("log_water", log_water))
    application.add_handler(ConversationHandler(
       entry_points=[CommandHandler("log_food", log_food)],
       states={
           ENTER_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, log_food_weight)],
       },
       fallbacks=[CommandHandler("cancel", cancel)],
   ))
    application.add_handler(CommandHandler("log_workout", log_workout))
    application.add_handler(CommandHandler("check_progress", check_progress))
    application.add_handler(MessageHandler(filters.Document.IMAGE, fer))  # Для распознавания эмоций

    print("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()