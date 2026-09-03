# -*- coding: utf-8 -*-
import json
import os
import random
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import telebot
from telebot import types
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

from data import CALLS, SUBJECTS, SCHEDULE, SUBJECT_ALIASES

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN не знайдено! Додай його в Environment Variables на Render.")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
KYIV = ZoneInfo("Europe/Kyiv")
SUBSCRIBERS_FILE = "subscribers.json"

STUDENTS = [
    "Болтенков Кирило", "Будко Микола", "Буцьківський Антон", "Веклич Олександр",
    "Воротніков Микола", "Гунбін Дмитро", "Дрінь Дмитро", "Желєзняк Владислав",
    "Задорожний Іван", "Кабанець Олексій", "Кищак Михайло", "Козаков Платон",
    "Конова Альбіна", "Корінєв Андрій", "Кравцов Олександр", "Кривозуб Олександр",
    "Лазаренко Віталій", "Лахмієнко Микола", "Левадноий Дмитро", "Левадський Олександр",
    "Літовщик Владислав", "Ломака Артем", "Макеєв Максим", "Мухортов Антон",
    "Остапенко Максим", "Перепелиця Артур", "Плахотній Станіслав", "Порошин Єгор",
    "Репринцев Владислав", "Семак Іван", "Скидан Юрій", "Суржко Валерій",
    "Сябро Лев", "Танцюра Даріна", "Тертишник Василь", "Тюпа Євген"
]
# Виправлення прізвища, яке не повинно змінювати логіку бота.
STUDENTS[18] = "Левадний Дмитро"

DAYS_UA = {
    "Monday": "Понеділок", "Tuesday": "Вівторок", "Wednesday": "Середа",
    "Thursday": "Четвер", "Friday": "П'ятниця", "Saturday": "Субота", "Sunday": "Неділя"
}


def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()
    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return {int(x) for x in json.load(f)}
    except Exception as e:
        print(f"Помилка завантаження підписників: {e}")
        return set()


def save_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(subscribed_users), f, ensure_ascii=False)
    except Exception as e:
        print(f"Помилка збереження підписників: {e}")


subscribed_users = load_subscribers()
sent_notifications = set()


def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📅 Сьогодні", "🔮 Завтра")
    markup.row("🗓 Розклад на тиждень")
    markup.row("📚 Предмети", "👨‍🏫 Викладачі")
    markup.row("🎥 Zoom", "📝 Google Classroom")
    markup.row("⏰ Розклад дзвінків")
    markup.row("🧹 Хто чергує завтра?")
    markup.row("👥 Список групи")
    markup.row("🔔 Увімкнути/вимкнути сповіщення")
    return markup


def get_subject_info(subject_name):
    data = SUBJECTS.get(subject_name)
    if not data:
        return None, None
    text = f"📚 *{subject_name}*\n\n👨‍🏫 {data.get('teacher', 'Не вказано')}"
    markup = types.InlineKeyboardMarkup()
    if data.get("zoom", "").startswith("http"):
        markup.add(types.InlineKeyboardButton("🎥 Відкрити Zoom", url=data["zoom"]))
    if data.get("classroom", "").startswith("http"):
        markup.add(types.InlineKeyboardButton("📚 Google Classroom", url=data["classroom"]))
    return text, markup


def normalize_subject(raw):
    low = raw.lower().strip()
    if low in SUBJECT_ALIASES:
        return SUBJECT_ALIASES[low]
    if "біолог" in low:
        return "Біологія і екологія"
    if "фізика" in low:
        return "Фізика"
    if "правознав" in low:
        return "Правознавство"
    if "англ" in low or "ін. мова" in low:
        return "Англійська мова"
    if "укр" in low:
        return "Українська мова та література"
    if "кон" in low or "констр" in low or "матеріал" in low or "електротех" in low:
        return "Конструкційні та електротехнічні матеріали"
    return raw


@app.route("/")
def index():
    return "Бот групи Е-21 працює!", 200


@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.send_message(message.chat.id,
        "🎓 *Вітаю!*\n\nЦе Telegram-бот групи *Е-21*.\n\n"
        "Тут можна переглянути розклад, викладачів та посилання на Zoom і Google Classroom.\n\n"
        "Також можеш просто написати назву або скорочення предмета: укр, матем, англ, фізика, біо, кон.",
        parse_mode="Markdown", reply_markup=get_main_keyboard())


def send_schedule_for(message, target_date, title):
    day = target_date.strftime("%A")
    schedule = SCHEDULE.get(day, {})
    day_ua = DAYS_UA.get(day, day)
    if not schedule:
        bot.send_message(message.chat.id, f"{title} *{day_ua}*\n\nПар немає 🎉", parse_mode="Markdown")
        return
    text = f"{title} *{day_ua}:*\n\n"
    for number, subject in schedule.items():
        call = CALLS.get(number, {})
        text += f"*{number} пара* ({call.get('start','')}–{call.get('end','')})\n📚 {subject}\n\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "📅 Сьогодні")
def send_today(message):
    send_schedule_for(message, datetime.now(KYIV), "📅 *Розклад на сьогодні —")


@bot.message_handler(func=lambda m: m.text == "🔮 Завтра")
def send_tomorrow(message):
    send_schedule_for(message, datetime.now(KYIV) + timedelta(days=1), "🔮 *Розклад на завтра —")


@bot.message_handler(func=lambda m: m.text == "🗓 Розклад на тиждень")
def send_week(message):
    text = "🗓 *Розклад на тиждень:*\n\n"
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
        text += f"📌 *{DAYS_UA[day]}:*\n"
        schedule = SCHEDULE.get(day, {})
        if not schedule:
            text += "Пар немає\n\n"
            continue
        for number, subject in schedule.items():
            call = CALLS.get(number, {})
            text += f"{number}. {call.get('start','')}–{call.get('end','')} — {subject}\n"
        text += "\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "📚 Предмети")
def send_subjects(message):
    markup = types.InlineKeyboardMarkup()
    for name in SUBJECTS:
        markup.add(types.InlineKeyboardButton(f"📚 {name}", callback_data=f"sub_{name}"))
    bot.send_message(message.chat.id, "📚 *Обери предмет:*", parse_mode="Markdown", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def callback_subject(call):
    subject_name = call.data[4:]
    info_text, markup = get_subject_info(subject_name)
    if info_text:
        bot.send_message(call.message.chat.id, info_text, parse_mode="Markdown", reply_markup=markup)
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda m: m.text == "👨‍🏫 Викладачі")
def send_teachers(message):
    text = "👨‍🏫 *Список викладачів:*\n\n"
    for name, data in SUBJECTS.items():
        text += f"📚 *{name}*\n👨‍🏫 {data.get('teacher', 'Не вказано')}\n\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "⏰ Розклад дзвінків")
def send_calls(message):
    text = "⏰ *Розклад дзвінків:*\n\n"
    for number, times in CALLS.items():
        text += f"{number} пара — {times['start']}–{times['end']}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "🎥 Zoom")
def send_zoom(message):
    markup = types.InlineKeyboardMarkup()
    for name, data in SUBJECTS.items():
        if data.get("zoom", "").startswith("http"):
            markup.add(types.InlineKeyboardButton(f"🎥 {name}", url=data["zoom"]))
    bot.send_message(message.chat.id, "🎥 *Обери предмет:*", parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "📝 Google Classroom")
def send_classroom(message):
    markup = types.InlineKeyboardMarkup()
    for name, data in SUBJECTS.items():
        if data.get("classroom", "").startswith("http"):
            markup.add(types.InlineKeyboardButton(f"📚 {name}", url=data["classroom"]))
    bot.send_message(message.chat.id, "📚 *Google Classroom*\n\nОбери предмет:", parse_mode="Markdown", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == "🧹 Хто чергує завтра?")
def random_student(message):
    bot.send_message(message.chat.id, f"🧹 *Черговий завтра:*\n\n👤 {random.choice(STUDENTS)}", parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "👥 Список групи")
def group_list(message):
    text = "👥 *Список групи Е-21:*\n\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(STUDENTS, 1))
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


@bot.message_handler(func=lambda m: m.text == "🔔 Увімкнути/вимкнути сповіщення")
def toggle_notifications(message):
    user_id = message.chat.id
    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        save_subscribers()
        bot.send_message(user_id, "🔕 Сповіщення вимкнено.")
    else:
        subscribed_users.add(user_id)
        save_subscribers()
        bot.send_message(user_id, "🔔 Сповіщення увімкнено! Надалі бот надсилатиме нагадування за 10 хвилин до пари.")


def send_lesson_notification(number, subject, start_time):
    info = SUBJECTS.get(subject)
    text = f"🔔 *Через 10 хвилин починається пара!*\n\n*{number} пара* — {subject}\n⏰ Початок: {start_time.strftime('%H:%M')}"
    markup = types.InlineKeyboardMarkup()
    if info and info.get("zoom", "").startswith("http"):
        markup.add(types.InlineKeyboardButton("🎥 Відкрити Zoom", url=info["zoom"]))
    if info and info.get("classroom", "").startswith("http"):
        markup.add(types.InlineKeyboardButton("📚 Google Classroom", url=info["classroom"]))
    for chat_id in list(subscribed_users):
        try:
            bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            print(f"Не вдалося надіслати сповіщення {chat_id}: {e}")


def check_notifications():
    now = datetime.now(KYIV).replace(second=0, microsecond=0)
    day = now.strftime("%A")
    schedule = SCHEDULE.get(day, {})
    if not schedule or not subscribed_users:
        return

    for number, subject in schedule.items():
        call = CALLS.get(number)
        if not call:
            continue
        start = datetime.combine(now.date(), datetime.strptime(call["start"], "%H:%M").time(), tzinfo=KYIV)
        diff = int((start - now).total_seconds())
        # Похибка ±30 секунд, щоб нагадування не пропускалось через запуск задачі.
        if 570 <= diff <= 630:
            key = f"{now.date().isoformat()}_{number}"
            if key not in sent_notifications:
                sent_notifications.add(key)
                send_lesson_notification(number, subject, start)

    # Чистимо старі ключі.
    today_prefix = now.date().isoformat()
    sent_notifications.intersection_update({k for k in sent_notifications if k.startswith(today_prefix)})


# Пошук по предметах — завжди останній обробник.
SEARCH_WORDS = {
    "Українська мова та література": ["укр", "українська", "украинский", "література", "літ"],
    "Виховні години та фізичне виховання": ["фізра", "физра", "фізичне", "фізвих", "виховна"],
    "Фізика": ["фізика", "физика", "фіз"],
    "Конструкційні та електротехнічні матеріали": ["кон", "констр", "конструк", "конструкційні", "матеріали", "материалы", "електро", "електротехнічні"],
    "Історія 9 клас": ["історія 9", "история 9", "історія9", "история9"],
    "Історія 11 клас": ["історія 11", "история 11", "історія11", "история11"],
    "Правознавство": ["право", "правознавство"],
    "Англійська мова": ["англ", "англійська", "английский"],
    "Математика": ["матем", "математика", "матемю", "алгебра"],
    "Біологія і екологія": ["біо", "био", "біологія", "биология", "екологія", "экология"],
}


@bot.message_handler(func=lambda m: m.text is not None)
def search_subject(message):
    text = message.text.lower().strip()
    for subject_name, keywords in SEARCH_WORDS.items():
        if any(keyword in text for keyword in keywords):
            info_text, markup = get_subject_info(subject_name)
            if info_text:
                bot.send_message(message.chat.id, info_text, parse_mode="Markdown", reply_markup=markup)
            return
    bot.send_message(message.chat.id, "❓ Не зрозумів.\n\nНапиши предмет або скорочення: укр, матем, англ, фізика, біо, кон")


scheduler = BackgroundScheduler(timezone=KYIV)
scheduler.add_job(check_notifications, "interval", seconds=30, id="lesson_notifications", replace_existing=True)
scheduler.start()


def run_bot():
    try:
        bot.remove_webhook()
        print("Telegram-бот запущений!")
        bot.infinity_polling(skip_pending=True, timeout=30, long_polling_timeout=30)
    except Exception as error:
        print(f"Помилка Telegram-бота: {error}")


if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 10000))
    print(f"Flask-сервер запущений на порту {port}")
    app.run(host="0.0.0.0", port=port)
