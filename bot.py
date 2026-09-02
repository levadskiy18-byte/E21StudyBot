import os
import json
from datetime import datetime
import telebot
from telebot import types
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
from data import CALLS, SUBJECTS, SCHEDULE

TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Постоянное хранение подписчиков в файле
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

# Словарь быстрых слов для поиска предметов
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
    "алгебра": "Математика",
    "геометрия": "Математика",
    "англ": "Англійська мова",
    "английский": "Англійська мова",
    "english": "Англійська мова",
    "био": "Біологія і Екологія",
    "биология": "Біологія і Екологія",
    "экология": "Біологія і Екологія",
    "право": "Правознавство",
    "правоведение": "Правознавство",
    "история": "Історія 11 класс",
    "історія": "Історія 11 класс",
    "материалы": "Конструкційні та електротехнічні матеріали",
    "матеріали": "Конструкційні та електротехнічні матеріали",
    "кэм": "Конструкційні та електротехнічні матеріали"
}

def get_subject_info_text(subject_name):
    data = SUBJECTS.get(subject_name)
    if not data:
        return None, None
    text = f"📚 *{subject_name}*\n👨‍🏫 Преподаватель: {data['teacher']}"
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
        "Привет! Я бот группы Е-21.\nМожешь использовать меню или просто написать название предмета (например: 'укр', 'матем', 'физика'), чтобы получить ссылку!",
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
        bot.send_message(user_id, "🔔 Уведомления включены! Теперь ты будешь получать ссылки перед парами.")

# Обработка коротких названий предметов
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text_clean = message.text.strip().lower()
    
    # Поиск по словарю сокращений
    matched_subject = ALIASES.get(text_clean)
    
    # Если прямого совпадения нет, ищем частичное
    if not matched_subject:
        for key, full_name in ALIASES.items():
            if key in text_clean:
                matched_subject = full_name
                break

    if matched_subject:
        info_text, reply_markup = get_subject_info_text(matched_subject)
        if info_text:
            bot.send_message(message.chat.id, info_text, parse_mode="Markdown", reply_markup=reply_markup)
            return

    # Если предмет не найден — стандартный ответ
    if message.text == "📅 Расписание на сегодня":
        bot.send_message(message.chat.id, "Функция расписания работает по меню.")
    else:
        bot.send_message(message.chat.id, "Я не понял запрос. Напиши сокращенное название предмета (например: 'укр', 'матем', 'физика') или воспользуйся меню.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
