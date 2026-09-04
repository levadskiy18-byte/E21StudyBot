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

from data import (
    CALLS,
    SUBJECTS,
    CURRENT_SCHEDULE,
    NEXT_SCHEDULE,
    CURRENT_WEEK_START,
    CURRENT_WEEK_END,
    NEXT_WEEK_START,
    NEXT_WEEK_END,
)

# ==========================================================
# НАСТРОЙКИ
# ==========================================================

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError(
        "BOT_TOKEN не знайдено! Додай його в Environment Variables на Render."
    )

ADMIN_ID = 857901222
GROUP_CHAT_URL = "https://t.me/+GaN9ZTAYn_01ODRi"
DONATE_URL = "https://send.monobank.ua/jar/5r7iFcvzb7"

KYIV = ZoneInfo("Europe/Kyiv")

bot = telebot.TeleBot(
    TOKEN,
    parse_mode="Markdown"
)

app = Flask(__name__)

SUBSCRIBERS_FILE = "subscribers.json"
USERS_FILE = "users.json"

# ==========================================================
# СПИСОК ГРУПИ
# ==========================================================

STUDENTS = [
    "Болтенков Кирило",
    "Будко Микола",
    "Буцьківський Антон",
    "Веклич Олександр",
    "Воротніков Микола",
    "Гунбін Дмитро",
    "Дрінь Дмитро",
    "Желєзняк Владислав",
    "Задорожний Іван",
    "Кабанець Олексій",
    "Кищак Михайло",
    "Козаков Платон",
    "Конова Альбіна",
    "Корінєв Андрій",
    "Кравцов Олександр",
    "Кривозуб Олександр",
    "Лазаренко Віталій",
    "Лахмієнко Микола",
    "Левадний Дмитро",
    "Левадський Олександр",
    "Літовщик Владислав",
    "Ломака Артем",
    "Макеєв Максим",
    "Мухортов Антон",
    "Остапенко Максим",
    "Перепелиця Артур",
    "Плахотній Станіслав",
    "Порошин Єгор",
    "Репринцев Владислав",
    "Семак Іван",
    "Скидан Юрій",
    "Суржко Валерій",
    "Сябро Лев",
    "Танцюра Даріна",
    "Тертишник Василь",
    "Тюпа Євген",
]

# ==========================================================
# ДАННЫЕ ПОЛЬЗОВАТЕЛЕЙ
# ==========================================================

subscribed_users = set()
known_users = set()

sent_notifications = set()

pending_complaints = {}
pending_admin_replies = {}
pending_announcement = set()

# ==========================================================
# ФАЙЛЫ
# ==========================================================

def load_ids(filename):
    if not os.path.exists(filename):
        return set()

    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {int(x) for x in data}

    except Exception as e:
        print(f"Помилка завантаження {filename}: {e}")
        return set()


def save_ids(filename, values):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                sorted(values),
                f,
                ensure_ascii=False
            )

    except Exception as e:
        print(f"Помилка збереження {filename}: {e}")


subscribed_users = load_ids(SUBSCRIBERS_FILE)
known_users = load_ids(USERS_FILE)


def remember_user(user_id):
    known_users.add(user_id)
    save_ids(USERS_FILE, known_users)


def save_subscribers():
    save_ids(
        SUBSCRIBERS_FILE,
        subscribed_users
    )

# ==========================================================
# ДНИ НЕДЕЛИ
# ==========================================================

DAYS_UA = {
    "Monday": "Понеділок",
    "Tuesday": "Вівторок",
    "Wednesday": "Середа",
    "Thursday": "Четвер",
    "Friday": "П'ятниця",
    "Saturday": "Субота",
    "Sunday": "Неділя",
}

# ==========================================================
# ВРЕМЯ ПАР
# ==========================================================

def get_call_time(target_date, number):
    number = str(number)

    # Только понедельник: первая пара с 08:45
    if target_date.weekday() == 0 and number == "1":
        return "08:45", "09:35"

    call = CALLS.get(number)

    if not call:
        return "", ""

    return call.get("start", ""), call.get("end", "")

# ==========================================================
# РАСПИСАНИЕ ПО ДАТЕ
# ==========================================================

def get_schedule_for_date(target_date):
    current_start = datetime.strptime(
        CURRENT_WEEK_START,
        "%Y-%m-%d"
    ).date()

    current_end = datetime.strptime(
        CURRENT_WEEK_END,
        "%Y-%m-%d"
    ).date()

    next_start = datetime.strptime(
        NEXT_WEEK_START,
        "%Y-%m-%d"
    ).date()

    next_end = datetime.strptime(
        NEXT_WEEK_END,
        "%Y-%m-%d"
    ).date()

    day_name = target_date.strftime("%A")

    if current_start <= target_date <= current_end:
        return CURRENT_SCHEDULE.get(day_name, {})

    if next_start <= target_date <= next_end:
        return NEXT_SCHEDULE.get(day_name, {})

    return {}

# ==========================================================
# ТЕКУЩАЯ НЕДЕЛЯ
# ==========================================================

def get_current_week():
    today = datetime.now(KYIV).date()

    current_start = datetime.strptime(
        CURRENT_WEEK_START,
        "%Y-%m-%d"
    ).date()

    current_end = datetime.strptime(
        CURRENT_WEEK_END,
        "%Y-%m-%d"
    ).date()

    next_start = datetime.strptime(
        NEXT_WEEK_START,
        "%Y-%m-%d"
    ).date()

    next_end = datetime.strptime(
        NEXT_WEEK_END,
        "%Y-%m-%d"
    ).date()

    if current_start <= today <= current_end:
        return CURRENT_SCHEDULE, current_start, current_end

    if next_start <= today <= next_end:
        return NEXT_SCHEDULE, next_start, next_end

    return None, None, None

# ==========================================================
# СЛЕДУЮЩАЯ НЕДЕЛЯ
# ==========================================================

def get_next_week():
    today = datetime.now(KYIV).date()

    current_start = datetime.strptime(
        CURRENT_WEEK_START,
        "%Y-%m-%d"
    ).date()

    current_end = datetime.strptime(
        CURRENT_WEEK_END,
        "%Y-%m-%d"
    ).date()

    next_start = datetime.strptime(
        NEXT_WEEK_START,
        "%Y-%m-%d"
    ).date()

    next_end = datetime.strptime(
        NEXT_WEEK_END,
        "%Y-%m-%d"
    ).date()

    if current_start <= today <= current_end:
        return NEXT_SCHEDULE, next_start, next_end

    if next_start <= today <= next_end:
        return None, None, None

    return None, None, None

# ==========================================================
# ГЛАВНОЕ МЕНЮ
# ==========================================================

def get_main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        "📅 Сьогодні",
        "🔮 Завтра"
    )

    markup.row(
        "🗓 Цей тиждень",
        "🔮 Наступний тиждень"
    )

    markup.row(
        "📚 Предмети",
        "👨‍🏫 Викладачі"
    )

    markup.row(
        "🎥 Zoom",
        "📝 Google Classroom"
    )

    markup.row(
        "⏰ Розклад дзвінків"
    )

    markup.row(
        "🧹 Хто чергує завтра?",
        "👥 Список групи"
    )

    markup.row(
        "💬 Чат групи Е-21"
    )

    markup.row(
        "🥤 Кинь монету адміну на Кока-Колу"
    )

    markup.row(
        "🚨 БОТ НЕ ПРАЦЮЄ!!!"
    )

    if user_id in subscribed_users:
        markup.row(
            "🔔 Вимкнути сповіщення"
        )
    else:
        markup.row(
            "🔔 Увімкнути сповіщення"
        )

    if user_id == ADMIN_ID:
        markup.row(
            "📢 Оголошення"
        )

    return markup

# ==========================================================
# ИНФОРМАЦИЯ О ПРЕДМЕТЕ
# ==========================================================

def get_subject_info(subject_name):
    data = SUBJECTS.get(subject_name)

    if not data and subject_name == "Фізвиховання":
        data = SUBJECTS.get(
            "Виховні години та фізичне виховання"
        )
        subject_name = "Виховні години та фізичне виховання"

    if not data:
        return None, None

    teacher = data.get(
        "teacher",
        "Не вказано"
    )

    text = (
        f"📚 *{subject_name}*\n\n"
        f"👨‍🏫 {teacher}"
    )

    markup = types.InlineKeyboardMarkup()

    zoom = data.get("zoom", "")
    classroom = data.get("classroom", "")

    if zoom.startswith("http"):
        markup.add(
            types.InlineKeyboardButton(
                "🎥 Відкрити Zoom",
                url=zoom
            )
        )

    if classroom.startswith("http"):
        markup.add(
            types.InlineKeyboardButton(
                "📚 Google Classroom",
                url=classroom
            )
        )

    return text, markup

# ==========================================================
# СЕГОДНЯ / ЗАВТРА
# ==========================================================

def send_schedule_for(message, target_date, title):
    schedule = get_schedule_for_date(target_date)

    day_name = target_date.strftime("%A")
    day_ua = DAYS_UA.get(day_name, day_name)

    if not schedule:
        bot.send_message(
            message.chat.id,
            f"{title} *{day_ua}:*\n\nПар немає 🎉"
        )
        return

    text = f"{title} *{day_ua}:*\n\n"

    for number, subject in schedule.items():
        start, end = get_call_time(
            target_date,
            number
        )

        if subject == "Фізвиховання":
            subject = "Виховні години та фізичне виховання"

        text += (
            f"*{number} пара* "
            f"({start}–{end})\n"
            f"📚 {subject}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )

# ==========================================================
# START
# ==========================================================

@bot.message_handler(commands=["start"])
def send_welcome(message):
    remember_user(message.from_user.id)

    bot.send_message(
        message.chat.id,
        "🎓 *Вітаю!*\n\n"
        "Це Telegram-бот групи *Е-21*.\n\n"
        "Тут можна переглянути розклад, "
        "викладачів та посилання на Zoom "
        "і Google Classroom.\n\n"
        "Також можеш просто написати "
        "назву або скорочення предмета.",
        reply_markup=get_main_keyboard(
            message.from_user.id
        )
    )

# ==========================================================
# СЬОГОДНІ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "📅 Сьогодні"
)
def send_today(message):
    remember_user(message.from_user.id)

    today = datetime.now(KYIV).date()

    send_schedule_for(
        message,
        today,
        "📅 *Розклад на сьогодні —"
    )

# ==========================================================
# ЗАВТРА
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🔮 Завтра"
)
def send_tomorrow(message):
    remember_user(message.from_user.id)

    tomorrow = (
        datetime.now(KYIV).date()
        + timedelta(days=1)
    )

    send_schedule_for(
        message,
        tomorrow,
        "🔮 *Розклад на завтра —"
    )

# ==========================================================
# ЦЕЙ ТИЖДЕНЬ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🗓 Цей тиждень"
)
def send_current_week(message):
    remember_user(message.from_user.id)

    schedule_data, start_date, end_date = get_current_week()

    if not schedule_data:
        bot.send_message(
            message.chat.id,
            "📭 Розклад поточного тижня "
            "ще не завантажений."
        )
        return

    text = (
        "🗓 *Розклад поточного тижня:*\n"
        f"{start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}\n\n"
    )

    current = start_date

    while current <= end_date:
        day_name = current.strftime("%A")
        day_ua = DAYS_UA.get(day_name, day_name)

        schedule = schedule_data.get(day_name, {})

        text += f"📌 *{day_ua}:*\n"

        if not schedule:
            text += "Пар немає 🎉\n\n"
        else:
            for number, subject in schedule.items():
                start, end = get_call_time(
                    current,
                    number
                )

                if subject == "Фізвиховання":
                    subject = "Виховні години та фізичне виховання"

                text += (
                    f"{number}. {start}–{end} — "
                    f"{subject}\n"
                )

            text += "\n"

        current += timedelta(days=1)

    bot.send_message(
        message.chat.id,
        text
    )

# ==========================================================
# НАСТУПНИЙ ТИЖДЕНЬ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🔮 Наступний тиждень"
)
def send_next_week(message):
    remember_user(message.from_user.id)

    schedule_data, start_date, end_date = get_next_week()

    if not schedule_data:
        bot.send_message(
            message.chat.id,
            "📭 Розклад наступного тижня "
            "ще не завантажений."
        )
        return

    text = (
        "🗓 *Розклад наступного тижня:*\n"
        f"{start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}\n\n"
    )

    current = start_date

    while current <= end_date:
        day_name = current.strftime("%A")
        day_ua = DAYS_UA.get(day_name, day_name)

        schedule = schedule_data.get(day_name, {})

        text += f"📌 *{day_ua}:*\n"

        if not schedule:
            text += "Пар немає 🎉\n\n"
        else:
            for number, subject in schedule.items():
                start, end = get_call_time(
                    current,
                    number
                )

                if subject == "Фізвиховання":
                    subject = "Виховні години та фізичне виховання"

                text += (
                    f"{number}. {start}–{end} — "
                    f"{subject}\n"
                )

            text += "\n"

        current += timedelta(days=1)

    bot.send_message(
        message.chat.id,
        text
    )

# ==========================================================
# РОЗКЛАД ДЗВОНКІВ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "⏰ Розклад дзвінків"
)
def send_calls(message):
    remember_user(message.from_user.id)

    text = (
        "⏰ *Розклад дзвінків:*\n\n"
        "1 пара — 08:00–09:35\n"
        "ℹ️ У понеділок 1-а пара — 08:45–09:35\n\n"
    )

    for number, times in CALLS.items():
        if str(number) == "1":
            continue

        text += (
            f"{number} пара — "
            f"{times['start']}–{times['end']}\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )

# ==========================================================
# ПРЕДМЕТИ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "📚 Предмети"
)
def send_subjects(message):
    remember_user(message.from_user.id)

    subject_names = list(SUBJECTS.keys())
    markup = types.InlineKeyboardMarkup()

    for index, name in enumerate(subject_names):
        markup.add(
            types.InlineKeyboardButton(
                f"📚 {name}",
                callback_data=f"sub:{index}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📚 *Обери предмет:*",
        reply_markup=markup
    )


@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("sub:")
)
def callback_subject(call):
    try:
        index = int(
            call.data.split(":", 1)[1]
        )

        subject_names = list(SUBJECTS.keys())
        subject_name = subject_names[index]

    except (ValueError, IndexError):
        bot.answer_callback_query(
            call.id,
            "Помилка."
        )
        return

    info_text, markup = get_subject_info(
        subject_name
    )

    if info_text:
        bot.send_message(
            call.message.chat.id,
            info_text,
            reply_markup=markup
        )

    bot.answer_callback_query(call.id)

# ==========================================================
# ВИКЛАДАЧІ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "👨‍🏫 Викладачі"
)
def send_teachers(message):
    remember_user(message.from_user.id)

    text = "👨‍🏫 *Список викладачів:*\n\n"

    for name, data in SUBJECTS.items():
        teacher = data.get(
            "teacher",
            "Не вказано"
        )

        text += (
            f"📚 *{name}*\n"
            f"👨‍🏫 {teacher}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text
    )

# ==========================================================
# ZOOM
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🎥 Zoom"
)
def send_zoom(message):
    remember_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()

    for name, data in SUBJECTS.items():
        zoom = data.get("zoom", "")

        if zoom.startswith("http"):
            markup.add(
                types.InlineKeyboardButton(
                    f"🎥 {name}",
                    url=zoom
                )
            )

    bot.send_message(
        message.chat.id,
        "🎥 *Обери предмет:*",
        reply_markup=markup
    )

# ==========================================================
# CLASSROOM
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "📝 Google Classroom"
)
def send_classroom(message):
    remember_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()

    for name, data in SUBJECTS.items():
        classroom = data.get("classroom", "")

        if classroom.startswith("http"):
            markup.add(
                types.InlineKeyboardButton(
                    f"📚 {name}",
                    url=classroom
                )
            )

    bot.send_message(
        message.chat.id,
        "📚 *Google Classroom*\n\n"
        "Обери предмет:",
        reply_markup=markup
    )

# ==========================================================
# ДЕЖУРНЫЙ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🧹 Хто чергує завтра?"
)
def random_student(message):
    remember_user(message.from_user.id)

    student = random.choice(STUDENTS)

    bot.send_message(
        message.chat.id,
        "🧹 *Черговий завтра:*\n\n"
        f"👤 {student}"
    )

# ==========================================================
# СПИСОК ГРУППЫ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "👥 Список групи"
)
def group_list(message):
    remember_user(message.from_user.id)

    text = "👥 *Список групи Е-21:*\n\n"

    for i, student in enumerate(
        STUDENTS,
        1
    ):
        text += f"{i}. {student}\n"

    bot.send_message(
        message.chat.id,
        text
    )

# ==========================================================
# ЧАТ ГРУППЫ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "💬 Чат групи Е-21"
)
def group_chat(message):
    remember_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "💬 Відкрити чат групи",
            url=GROUP_CHAT_URL
        )
    )

    bot.send_message(
        message.chat.id,
        "💬 *Чат групи Е-21*",
        reply_markup=markup
    )

# ==========================================================
# КОКА-КОЛА
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🥤 Кинь монету адміну на Кока-Колу"
)
def donate(message):
    remember_user(message.from_user.id)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "🥤 Закинути на Кока-Колу",
            url=DONATE_URL
        )
    )

    bot.send_message(
        message.chat.id,
        "🥤 Якщо хочеш пригостити "
        "адміна Кока-Колою 😎",
        reply_markup=markup
    )

# ==========================================================
# УВІМЛЕННЯ / ВИМКНЕННЯ СПОВЕЩЕНИЙ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text in [
        "🔔 Увімкнути сповіщення",
        "🔔 Вимкнути сповіщення"
    ]
)
def toggle_notifications(message):
    remember_user(message.from_user.id)

    user_id = message.from_user.id

    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        save_subscribers()

        bot.send_message(
            user_id,
            "🔕 Сповіщення вимкнено.",
            reply_markup=get_main_keyboard(user_id)
        )

    else:
        subscribed_users.add(user_id)
        save_subscribers()

        bot.send_message(
            user_id,
            "🔔 Сповіщення увімкнено!\n\n"
            "Бот надсилатиме нагадування "
            "за 10 хвилин до пари та "
            "повідомлення в момент її початку.",
            reply_markup=get_main_keyboard(user_id)
        )

# ==========================================================
# УВЕДОМЛЕНИЕ О ПАРЕ
# ==========================================================

def send_lesson_notification(
    number,
    subject,
    start_time,
    kind="before"
):
    if subject == "Фізвиховання":
        subject = "Виховні години та фізичне виховання"

    info = SUBJECTS.get(subject)

    if kind == "before":
        text = (
            "🔔 *Через 10 хвилин "
            "починається пара!*\n\n"
            f"*{number} пара* — {subject}\n"
            f"⏰ Початок: {start_time}"
        )
    else:
        text = (
            "▶️ *Пара почалася!*\n\n"
            f"*{number} пара* — {subject}\n"
            f"⏰ Початок: {start_time}"
        )

    markup = types.InlineKeyboardMarkup()

    if info:
        zoom = info.get("zoom", "")
        classroom = info.get("classroom", "")

        buttons = []

        if zoom.startswith("http"):
            buttons.append(
                types.InlineKeyboardButton(
                    "🎥 Відкрити Zoom",
                    url=zoom
                )
            )

        if classroom.startswith("http"):
            buttons.append(
                types.InlineKeyboardButton(
                    "📚 Google Classroom",
                    url=classroom
                )
            )

        if buttons:
            markup.row(*buttons)

    for chat_id in list(subscribed_users):
        try:
            if markup.keyboard:
                bot.send_message(
                    chat_id,
                    text,
                    reply_markup=markup
                )
            else:
                bot.send_message(
                    chat_id,
                    text
                )

        except Exception as e:
            print(
                f"Не вдалося надіслати "
                f"сповіщення {chat_id}: {e}"
            )

# ==========================================================
# ПРОВЕРКА НАПОМИНАНИЙ
# ==========================================================

def check_notifications():
    now = datetime.now(KYIV).replace(
        second=0,
        microsecond=0
    )

    today = now.date()

    schedule = get_schedule_for_date(
        today
    )

    if not schedule:
        return

    for number, subject in schedule.items():

        start_str, end_str = get_call_time(
            today,
            number
        )

        if not start_str:
            continue

        try:
            start_time = datetime.strptime(
                start_str,
                "%H:%M"
            ).time()

        except ValueError:
            continue

        start_dt = datetime.combine(
            today,
            start_time
        ).replace(
            tzinfo=KYIV
        )

        diff = int(
            (start_dt - now).total_seconds()
        )

        # За 10 хвилин
        if 570 <= diff <= 630:
            key = (
                f"{today.isoformat()}_"
                f"{number}_before"
            )

            if key not in sent_notifications:
                sent_notifications.add(key)

                send_lesson_notification(
                    number,
                    subject,
                    start_str,
                    "before"
                )

        # В момент початку
        elif -30 <= diff <= 30:
            key = (
                f"{today.isoformat()}_"
                f"{number}_start"
            )

            if key not in sent_notifications:
                sent_notifications.add(key)

                send_lesson_notification(
                    number,
                    subject,
                    start_str,
                    "start"
                )

    # Удаляем старые записи
    prefix = today.isoformat()

    sent_notifications_copy = set(
        sent_notifications
    )

    for key in sent_notifications_copy:
        if not key.startswith(prefix):
            sent_notifications.discard(key)

# ==========================================================
# ЖАЛОБЫ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🚨 БОТ НЕ ПРАЦЮЄ!!!"
)
def complaint_start(message):
    remember_user(message.from_user.id)

    pending_complaints[
        message.from_user.id
    ] = True

    bot.send_message(
        message.chat.id,
        "🚨 Напиши, що саме не працює.\n\n"
        "Я передам повідомлення адміну."
    )


@bot.message_handler(
    func=lambda m:
    m.from_user.id in pending_complaints
)
def complaint_message(message):
    user_id = message.from_user.id

    pending_complaints.pop(
        user_id,
        None
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "немає username"
    )

    full_name = " ".join(
        x for x in [
            message.from_user.first_name,
            message.from_user.last_name
        ] if x
    )

    text = (
        "🚨 *Нова скарга: БОТ НЕ ПРАЦЮЄ!!!*\n\n"
        f"👤 Ім’я: {full_name or 'не вказано'}\n"
        f"🔹 Username: {username}\n"
        f"🆔 ID: `{user_id}`\n\n"
        f"💬 *Проблема:*\n{message.text}"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✉️ Відповісти користувачу",
            callback_data=f"reply:{user_id}"
        )
    )

    try:
        bot.send_message(
            ADMIN_ID,
            text,
            reply_markup=markup
        )

        bot.send_message(
            message.chat.id,
            "✅ Проблему передано адміну."
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Не вдалося передати проблему: `{e}`"
        )

# ==========================================================
# ОТВЕТ АДМИНА
# ==========================================================

@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("reply:")
)
def reply_button(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "Немає доступу."
        )
        return

    try:
        user_id = int(
            call.data.split(":", 1)[1]
        )

    except Exception:
        bot.answer_callback_query(
            call.id,
            "Помилка."
        )
        return

    pending_admin_replies[
        ADMIN_ID
    ] = user_id

    bot.answer_callback_query(
        call.id
    )

    bot.send_message(
        call.message.chat.id,
        f"✉️ Напиши відповідь користувачу "
        f"`{user_id}` одним повідомленням."
    )


@bot.message_handler(
    func=lambda m:
    m.from_user.id == ADMIN_ID
    and m.from_user.id in pending_admin_replies
)
def admin_reply(message):
    user_id = pending_admin_replies.pop(
        ADMIN_ID,
        None
    )

    if not user_id:
        return

    try:
        bot.send_message(
            user_id,
            "✉️ *Відповідь адміністратора:*\n\n"
            + message.text
        )

        bot.send_message(
            message.chat.id,
            "✅ Відповідь користувачу відправлена."
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            f"❌ Не вдалося відправити відповідь: `{e}`"
        )

# ==========================================================
# ОБЪЯВЛЕНИЯ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.from_user.id == ADMIN_ID
    and m.text == "📢 Оголошення"
)
def announcement_start(message):
    pending_announcement.add(
        ADMIN_ID
    )

    bot.send_message(
        message.chat.id,
        "📢 Напиши текст оголошення."
    )


@bot.message_handler(
    func=lambda m:
    m.from_user.id == ADMIN_ID
    and m.from_user.id in pending_announcement
)
def announcement_send(message):
    pending_announcement.discard(
        ADMIN_ID
    )

    recipients = (
        set(known_users)
        | set(subscribed_users)
    )

    recipients.discard(
        ADMIN_ID
    )

    text = (
        "📢 *Оголошення*\n\n"
        + message.text
    )

    sent = 0
    failed = 0

    for user_id in recipients:
        try:
            bot.send_message(
                user_id,
                text
            )
            sent += 1

        except Exception:
            failed += 1

    bot.send_message(
        message.chat.id,
        f"✅ Оголошення розіслано.\n\n"
        f"📨 Надіслано: {sent}\n"
        f"❌ Не доставлено: {failed}"
    )

# ==========================================================
# ПОИСК ПРЕДМЕТА
# ==========================================================

SEARCH_WORDS = {
    "Українська мова та література": [
        "укр",
        "українська",
        "украинский",
        "література",
        "літ"
    ],

    "Виховні години та фізичне виховання": [
        "фізра",
        "физра",
        "фізичне",
        "фізвих",
        "фізвиховання",
        "виховна",
        "фізкультура"
    ],

    "Фізика": [
        "фізика",
        "физика",
        "фіз"
    ],

    "Конструкційні та електротехнічні матеріали": [
        "кон",
        "констр",
        "конструк",
        "конструкційні",
        "матеріали",
        "материалы",
        "електро",
        "електротехнічні"
    ],

    "Історія 9 клас": [
        "історія 9",
        "история 9",
        "історія9",
        "история9"
    ],

    "Історія 11 клас": [
        "історія 11",
        "история 11",
        "історія11",
        "история11"
    ],

    "Правознавство": [
        "право",
        "правознавство"
    ],

    "Англійська мова": [
        "англ",
        "англійська",
        "английский"
    ],

    "Математика": [
        "матем",
        "математика",
        "алгебра"
    ],

    "Біологія і екологія": [
        "біо",
        "био",
        "біологія",
        "биология",
        "екологія",
        "экология"
    ],

    "Інформаційна тематична година": [
        "інформаційна",
        "тематична",
        "інф"
    ],
}


@bot.message_handler(
    func=lambda m:
    m.text is not None
)
def search_subject(message):
    text = (
        message.text
        .lower()
        .strip()
    )

    for subject_name, keywords in SEARCH_WORDS.items():

        if any(
            keyword in text
            for keyword in keywords
        ):

            info_text, markup = get_subject_info(
                subject_name
            )

            if info_text:
                bot.send_message(
                    message.chat.id,
                    info_text,
                    reply_markup=markup
                )

            return

    bot.send_message(
        message.chat.id,
        "❓ Не зрозумів.\n\n"
        "Напиши предмет або скорочення:\n"
        "укр, матем, англ, фізика, біо, кон"
    )

# ==========================================================
# RENDER
# ==========================================================

@app.route("/")
def index():
    return "Бот групи Е-21 працює!", 200


@app.route("/health")
def health():
    return "OK", 200

# ==========================================================
# ЗАПУСК БОТА
# ==========================================================

def run_bot():
    try:
        bot.remove_webhook()

        print(
            "Telegram-бот запущений!"
        )

        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30
        )

    except Exception as error:
        print(
            f"Помилка Telegram-бота: {error}"
        )


scheduler = BackgroundScheduler(
    timezone=KYIV
)

scheduler.add_job(
    check_notifications,
    "interval",
    seconds=30,
    id="lesson_notifications",
    replace_existing=True,
    max_instances=1
)

scheduler.start()


if __name__ == "__main__":

    bot_thread = threading.Thread(
        target=run_bot,
        daemon=True
    )

    bot_thread.start()

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    print(
        f"Flask-сервер запущений "
        f"на порту {port}"
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
