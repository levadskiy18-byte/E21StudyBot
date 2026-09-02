import os
import json
from datetime import datetime
import pytz
import telebot
from telebot import types
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from data import CALLS, SUBJECTS, SCHEDULE

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Хранение подписчиков в файле
SUBSCRIBERS_FILE = "subscribers.json"

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        try:
            with open(SUBSCRIBERS_FILE, "r") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_subscribers(subs):
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            json.dump(list(subs), f)
    except Exception as e:
        print(f"Error saving subscribers: {e}")

subscribed_users = load_subscribers()

# Словарь синонимов предметов
ALIASES = {
    "укр": "Українська мова та література",
    "мова": "Українська мова та література",
    "укр мова": "Українська мова та література",
    "укр лит": "Українська мова та література",
    "физкультура": "Виховні години та фізичне виховання",
    "физра": "Виховні години та фізичне виховання",
    "виховна": "Виховні години та фізичне виховання",
    "физика": "Фізика",
    "фізика": "Фізика",
    "физ": "Фізика",
    "мат": "Математика",
    "матем": "Математика",
    "математика": "Математика",
    "англ": "Англійська мова",
    "английский": "Англійська мова",
    "био": "Біологія і Екологія",
    "биология": "Біологія і Екологія",
    "право": "Правознавство",
    "правоведение": "Правознавство",
    "история": "Історія 11 класс",
    "історія": "Історія 11 класс",
    "материалы": "Конструкційні та електротехнічні матеріали",
    "матеріали": "Конструкційні та електротехнічні матеріали",
    "кэм": "Конструкційні та електротехнічні матеріали"
}

DAYS_UA = {
    "Monday": "Понеділок",
    "Tuesday": "Вівторок",
    "Wednesday": "Середа",
    "Thursday": "Четвер",
    "Friday": "П'ятниця",
    "Saturday": "Субота",
    "Sunday": "Неділя"
}

def get_subject_info(subject_name):
    data = SUBJECTS.get(subject_name)
    if not data:
        return None, None
    text = f"📚 *{subject_name}*\n👨‍🏫 Выкладач: {data['teacher']}"
    markup = types.InlineKeyboardMarkup()
    if data.get("zoom"):
        markup.add(types.InlineKeyboardButton("🎥 Zoom", url=data["zoom"]))
    if data.get("classroom"):
        markup.add(types.InlineKeyboardButton("📚 Google Classroom", url=data["classroom"]))
    return text, markup

@app.route("/")
def index():
    return "Bot is running!", 200

@app.route("/" + TOKEN, methods=["POST"])
def webhook():
    json_str = request.get_data().decode("UTF-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@bot.message_handler(commands=["start"])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📅 Расписание на сегодня", "🗓 Расписание на неделю")
    markup.row("⏰ Расписание звонков", "📚 Предметы")
    markup.row("👨‍🏫 Преподаватели", "🔔 Включить/выключить уведомления")
    bot.send_message(
        message.chat.id,
        "Привет! Я бот группы Е-21.\nВыбирай нужную кнопку в меню или просто напиши название предмета (например, 'укр', 'матем', 'физика'), чтобы получить ссылку!",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "🔔 Включить/выключить уведомления")
def toggle_notifications(message):
    user_id = message.chat.id
    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        save_subscribers(subscribed_users)
        bot.send_message(user_id, "🔕 Уведомления выключены.")
    else:
        subscribed_users.add(user_id)
        save_subscribers(subscribed_users)
        bot.send_message(user_id, "🔔 Уведомления включены!")

@bot.message_handler(func=lambda message: message.text == "⏰ Расписание звонков")
def send_calls(message):
    text = "⏰ *Розклад дзвінків:*\n\n"
    for num, times in CALLS.items():
        text += f"{num} пара: {times['start']} - {times['end']}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📚 Предметы")
def send_subjects(message):
    markup = types.InlineKeyboardMarkup()
    for name in SUBJECTS.keys():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"sub_{name}"))
    bot.send_message(message.chat.id, "Обери предмет:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "👨‍🏫 Преподаватели")
def send_teachers(message):
    text = "👨‍🏫 *Список викладачів:*\n\n"
    for name, data in SUBJECTS.items():
        text += f"• *{name}*: {data['teacher']}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📅 Расписание на сегодня")
def send_today_schedule(message):
    tz = pytz.timezone("Europe/Kyiv")
    today = datetime.now(tz).strftime("%A")
    day_ua = DAYS_UA.get(today, today)
    
    day_schedule = SCHEDULE.get(today, {})
    if not day_schedule:
        bot.send_message(message.chat.id, f"📅 *Расписание на сегодня ({day_ua}):*\nСьогодні пар немає! 🎉", parse_mode="Markdown")
        return
    
    text = f"📅 *Расписание на сегодня ({day_ua}):*\n\n"
    for num, subject in day_schedule.items():
        time_info = CALLS.get(num, {})
        time_str = f"({time_info.get('start')} - {time_info.get('end')})" if time_info else ""
        text += f"*{num}. {subject}* {time_str}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "🗓 Расписание на неделю")
def send_week_schedule(message):
    text = "🗓 *Розклад на тиждень:*\n\n"
    for day_eng, day_ua in DAYS_UA.items():
        if day_eng in SCHEDULE and SCHEDULE[day_eng]:
            text += f"📌 *{day_ua}:*\n"
            for num, subject in SCHEDULE[day_eng].items():
                text += f"  {num}. {subject}\n"
            text += "\n"
    if text == "🗓 *Розклад на тиждень:*\n\n":
        text += "Розклад порожній."
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def callback_subject(call):
    sub_name = call.data.replace("sub_", "")
    info_text, markup = get_subject_info(sub_name)
    if info_text:
        bot.send_message(call.message.chat.id, info_text, parse_mode="Markdown", reply_markup=markup)

# Поиск по текстовым сокращениям
@bot.message_handler(func=lambda message: True)
def handle_custom_text(message):
    clean_text = message.text.strip().lower()
    matched = ALIASES.get(clean_text)
    
    if not matched:
        for key, full in ALIASES.items():
            if key in clean_text:
                matched = full
                break
                
    if matched:
        info_text, markup = get_subject_info(matched)
        if info_text:
            bot.send_message(message.chat.id, info_text, parse_mode="Markdown", reply_markup=markup)
            return

    bot.send_message(message.chat.id, "Я не зрозумів запит. Напиши назву предмета (наприклад: 'укр', 'матем', 'фізика') або скористайся меню.")

# Планировщик уведомлений
def check_and_send_notifications():
    tz = pytz.timezone("Europe/Kyiv")
    now = datetime.now(tz)
    today = now.strftime("%A")
    current_time = now.strftime("%H:%M")

    day_schedule = SCHEDULE.get(today, {})
    for num, subject_name in day_schedule.items():
        call_info = CALLS.get(num)
        if call_info and call_info["start"] == current_time:
            info_text, markup = get_subject_info(subject_name)
            if info_text:
                msg = f"🔔 *Пара починається!*\n\n{info_text}"
                for user_id in list(subscribed_users):
                    try:
                        bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=markup)
                    except Exception:
                        pass

scheduler = BackgroundScheduler(timezone="Europe/Kyiv")
scheduler.add_job(check_and_send_notifications, "interval", minutes=1)
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
