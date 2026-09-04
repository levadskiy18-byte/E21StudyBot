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
        "BOT_TOKEN не знайдено! "
        "Додай його в Environment Variables на Render."
    )

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

KYIV = ZoneInfo("Europe/Kyiv")

SUBSCRIBERS_FILE = "subscribers.json"
USERS_FILE = "users.json"

ADMIN_ID = 857901222

feedback_waiting = set()
admin_reply_targets = {}
announcement_waiting = set()

sent_notifications = set()


# ==========================================================
# ДОНАТ
# ==========================================================

DONATE_URL = (
    "https://send.monobank.ua/jar/5r7iFcvzb7"
)


# ==========================================================
# ЧАТ ГРУПИ
# ==========================================================

GROUP_CHAT_URL = (
    "https://t.me/+GaN9ZTAYn_01ODRi"
)


# ==========================================================
# ВІВТОРОК — ВИНЯТОК
# ==========================================================
# Саме у вівторок 1 пара починається о 09:00.
# Інші дні використовують CALLS з data.py.
# ==========================================================

TUESDAY_CALLS = {
    "1": {
        "start": "09:00",
        "end": "09:35"
    },

    "2": {
        "start": "09:45",
        "end": "11:20"
    },

    "3": {
        "start": "12:00",
        "end": "13:35"
    },

    "4": {
        "start": "13:45",
        "end": "15:20"
    },

    "5": {
        "start": "15:30",
        "end": "17:05"
    }
}


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
    "Тюпа Євген"
]


# ==========================================================
# ДНІ ТИЖНЯ
# ==========================================================

DAYS_UA = {
    "Monday": "Понеділок",
    "Tuesday": "Вівторок",
    "Wednesday": "Середа",
    "Thursday": "Четвер",
    "Friday": "П'ятниця",
    "Saturday": "Субота",
    "Sunday": "Неділя"
}


# ==========================================================
# ДОПОМІЖНІ ФУНКЦІЇ ДЛЯ ДАТ
# ==========================================================

CURRENT_START_DATE = datetime.strptime(
    CURRENT_WEEK_START,
    "%Y-%m-%d"
).date()

CURRENT_END_DATE = datetime.strptime(
    CURRENT_WEEK_END,
    "%Y-%m-%d"
).date()

NEXT_START_DATE = datetime.strptime(
    NEXT_WEEK_START,
    "%Y-%m-%d"
).date()

NEXT_END_DATE = datetime.strptime(
    NEXT_WEEK_END,
    "%Y-%m-%d"
).date()


def format_date_range(start_date, end_date):
    start = datetime.strptime(
        start_date,
        "%Y-%m-%d"
    ).strftime("%d.%m.%Y")

    end = datetime.strptime(
        end_date,
        "%Y-%m-%d"
    ).strftime("%d.%m.%Y")

    return f"{start}–{end}"


# ==========================================================
# ВИЗНАЧЕННЯ ПОТОЧНОГО / НАСТУПНОГО ТИЖНЯ
# ==========================================================

def get_schedule_for_date(target_date):
    """
    Повертає:
        schedule
        тип тижня
        або None, якщо дати немає в двох підготовлених тижнях.
    """

    if (
        CURRENT_START_DATE
        <= target_date
        <= CURRENT_END_DATE
    ):
        return CURRENT_SCHEDULE, "current"

    if (
        NEXT_START_DATE
        <= target_date
        <= NEXT_END_DATE
    ):
        return NEXT_SCHEDULE, "next"

    return None, None


def get_week_schedule(week_type):
    if week_type == "current":
        return CURRENT_SCHEDULE

    if week_type == "next":
        return NEXT_SCHEDULE

    return {}


def get_week_dates(week_type):
    if week_type == "current":
        return (
            CURRENT_START_DATE,
            CURRENT_END_DATE
        )

    if week_type == "next":
        return (
            NEXT_START_DATE,
            NEXT_END_DATE
        )

    return None, None


def get_schedule_message_for_date(target_date):
    schedule, week_type = get_schedule_for_date(
        target_date
    )

    if schedule is None:
        return None, None, None

    day = target_date.strftime(
        "%A"
    )

    day_schedule = schedule.get(
        day,
        {}
    )

    return (
        day_schedule,
        week_type,
        day
    )


# ==========================================================
# ЧАСИ ПАР
# ==========================================================

def get_calls_for_day(day_name):
    if day_name == "Tuesday":
        return TUESDAY_CALLS

    return CALLS


def get_call_time(day_name, number):
    calls = get_calls_for_day(
        day_name
    )

    return calls.get(
        str(number),
        {}
    )


# ==========================================================
# ПІДПИСНИКИ
# ==========================================================

def load_subscribers():

    if not os.path.exists(
        SUBSCRIBERS_FILE
    ):
        return set()

    try:

        with open(
            SUBSCRIBERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return {
            int(user_id)
            for user_id in data
        }

    except Exception as error:

        print(
            f"Помилка завантаження "
            f"підписників: {error}"
        )

        return set()


def save_subscribers():

    try:

        with open(
            SUBSCRIBERS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                sorted(subscribed_users),
                file,
                ensure_ascii=False
            )

    except Exception as error:

        print(
            f"Помилка збереження "
            f"підписників: {error}"
        )


subscribed_users = load_subscribers()


# ==========================================================
# ВСІ КОРИСТУВАЧІ БОТА
# ==========================================================

def load_users():

    if not os.path.exists(
        USERS_FILE
    ):
        return set()

    try:

        with open(
            USERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return {
            int(user_id)
            for user_id in data
        }

    except Exception as error:

        print(
            f"Помилка завантаження "
            f"користувачів: {error}"
        )

        return set()


def save_users():

    try:

        with open(
            USERS_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                sorted(known_users),
                file,
                ensure_ascii=False
            )

    except Exception as error:

        print(
            f"Помилка збереження "
            f"користувачів: {error}"
        )


known_users = load_users()


def register_user(message):

    try:

        user_id = message.chat.id

        if user_id not in known_users:

            known_users.add(
                user_id
            )

            save_users()

    except Exception as error:

        print(
            f"Помилка реєстрації "
            f"користувача: {error}"
        )


# ==========================================================
# ГОЛОВНЕ МЕНЮ
# ==========================================================

def get_main_keyboard(
    is_admin=False
):

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
        "🧹 Хто чергує завтра?"
    )

    markup.row(
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

    markup.row(
        "🔔 Увімкнути/вимкнути сповіщення"
    )

    if is_admin:

        markup.row(
            "📢 Оголошення"
        )

    return markup


# ==========================================================
# ІНФОРМАЦІЯ ПРО ПРЕДМЕТ
# ==========================================================

def get_subject_info(subject_name):

    subject = SUBJECTS.get(
        subject_name
    )

    if not subject:
        return None, None

    teacher = subject.get(
        "teacher",
        "Не вказано"
    )

    text = (
        f"📚 *{subject_name}*\n\n"
        f"👨‍🏫 {teacher}"
    )

    markup = types.InlineKeyboardMarkup()

    zoom = subject.get(
        "zoom",
        ""
    )

    if (
        isinstance(zoom, str)
        and zoom.startswith("http")
    ):

        markup.add(
            types.InlineKeyboardButton(
                "🎥 Відкрити Zoom",
                url=zoom
            )
        )

    classroom = subject.get(
        "classroom",
        ""
    )

    if (
        isinstance(classroom, str)
        and classroom.startswith("http")
    ):

        markup.add(
            types.InlineKeyboardButton(
                "📚 Google Classroom",
                url=classroom
            )
        )

    return text, markup


# ==========================================================
# ПРЕДМЕТИ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📚 Предмети"
)
def send_subjects(message):

    register_user(message)

    markup = types.InlineKeyboardMarkup()

    subject_names = list(
        SUBJECTS.keys()
    )

    for index, name in enumerate(
        subject_names
    ):

        markup.add(
            types.InlineKeyboardButton(
                f"📚 {name}",
                callback_data=f"sub:{index}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📚 *Обери предмет:*",
        parse_mode="Markdown",
        reply_markup=markup
    )


# ==========================================================
# ВИБІР ПРЕДМЕТА
# ==========================================================

@bot.callback_query_handler(
    func=lambda call:
    isinstance(call.data, str)
    and call.data.startswith("sub:")
)
def callback_subject(call):

    try:

        index = int(
            call.data.split(
                ":",
                1
            )[1]
        )

        subject_names = list(
            SUBJECTS.keys()
        )

        if index < 0 or index >= len(
            subject_names
        ):

            bot.answer_callback_query(
                call.id,
                "Предмет не знайдено."
            )

            return

        subject_name = (
            subject_names[index]
        )

        info_text, markup = get_subject_info(
            subject_name
        )

        if info_text:

            bot.send_message(
                call.message.chat.id,
                info_text,
                parse_mode="Markdown",
                reply_markup=markup
            )

        bot.answer_callback_query(
            call.id
        )

    except Exception as error:

        print(
            f"Помилка вибору предмета: {error}"
        )

        bot.answer_callback_query(
            call.id,
            "Помилка."
        )


# ==========================================================
# START
# ==========================================================

@bot.message_handler(
    commands=["start"]
)
def send_welcome(message):

    register_user(message)

    bot.send_message(
        message.chat.id,

        "🎓 *Вітаю!*\n\n"
        "Це Telegram-бот групи *Е-21*.\n\n"
        "Тут можна переглянути розклад, "
        "викладачів та посилання на Zoom і Google Classroom.\n\n"
        "Також можна просто написати скорочення предмета:\n"
        "• укр\n"
        "• матем\n"
        "• англ\n"
        "• фізика\n"
        "• біо\n"
        "• кон",

        parse_mode="Markdown",

        reply_markup=get_main_keyboard(
            is_admin=message.chat.id == ADMIN_ID
        )
    )


# ==========================================================
# СЬОГОДНІ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📅 Сьогодні"
)
def send_today(message):

    register_user(message)

    today = datetime.now(
        KYIV
    ).date()

    schedule, week_type = get_schedule_for_date(
        today
    )

    if schedule is None:

        bot.send_message(
            message.chat.id,

            "📅 *Сьогодні*\n\n"
            f"Підготовлене розкладом "
            f"охоплено період "
            f"{format_date_range(CURRENT_WEEK_START, CURRENT_WEEK_END)} "
            f"та "
            f"{format_date_range(NEXT_WEEK_START, NEXT_WEEK_END)}.\n\n"
            "На цю дату розкладу немає.",

            parse_mode="Markdown"
        )

        return

    day = today.strftime(
        "%A"
    )

    day_ua = DAYS_UA.get(
        day,
        day
    )

    day_schedule = schedule.get(
        day,
        {}
    )

    if not day_schedule:

        bot.send_message(
            message.chat.id,

            f"📅 *Сьогодні — {day_ua}*\n\n"
            "Пар немає 🎉",

            parse_mode="Markdown"
        )

        return

    text = (
        f"📅 *Розклад на сьогодні — "
        f"{day_ua}:*\n\n"
    )

    for number, subject in day_schedule.items():

        call = get_call_time(
            day,
            number
        )

        text += (
            f"*{number} пара* "
            f"({call.get('start', '')}–"
            f"{call.get('end', '')})\n"
            f"📚 {subject}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==========================================================
# ЗАВТРА
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🔮 Завтра"
)
def send_tomorrow(message):

    register_user(message)

    tomorrow = (
        datetime.now(KYIV).date()
        + timedelta(days=1)
    )

    schedule, week_type = get_schedule_for_date(
        tomorrow
    )

    if schedule is None:

        bot.send_message(
            message.chat.id,

            "🔮 *Завтра*\n\n"
            "На цю дату підготовленого "
            "розкладу немає.",

            parse_mode="Markdown"
        )

        return

    day = tomorrow.strftime(
        "%A"
    )

    day_ua = DAYS_UA.get(
        day,
        day
    )

    day_schedule = schedule.get(
        day,
        {}
    )

    if not day_schedule:

        bot.send_message(
            message.chat.id,

            f"🔮 *Завтра — {day_ua}*\n\n"
            "Пар немає 🎉",

            parse_mode="Markdown"
        )

        return

    text = (
        f"🔮 *Розклад на завтра — "
        f"{day_ua}:*\n\n"
    )

    for number, subject in day_schedule.items():

        call = get_call_time(
            day,
            number
        )

        text += (
            f"*{number} пара* "
            f"({call.get('start', '')}–"
            f"{call.get('end', '')})\n"
            f"📚 {subject}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==========================================================
# ЦЕЙ ТИЖДЕНЬ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🗓 Цей тиждень"
)
def send_current_week(message):

    register_user(message)

    text = (
        "🗓 *Цей тиждень*\n\n"
        f"📅 {format_date_range(CURRENT_WEEK_START, CURRENT_WEEK_END)}\n\n"
    )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday"
    ]

    for day in days:

        text += (
            f"📌 *{DAYS_UA[day]}:*\n"
        )

        schedule = CURRENT_SCHEDULE.get(
            day,
            {}
        )

        if not schedule:

            text += (
                "Пар немає\n\n"
            )

            continue

        for number, subject in schedule.items():

            call = get_call_time(
                day,
                number
            )

            text += (
                f"{number}. "
                f"{call.get('start', '')}–"
                f"{call.get('end', '')} — "
                f"{subject}\n"
            )

        text += "\n"

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==========================================================
# НАСТУПНИЙ ТИЖДЕНЬ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🔮 Наступний тиждень"
)
def send_next_week(message):

    register_user(message)

    text = (
        "🔮 *Наступний тиждень*\n\n"
        f"📅 {format_date_range(NEXT_WEEK_START, NEXT_WEEK_END)}\n\n"
    )

    days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday"
    ]

    for day in days:

        text += (
            f"📌 *{DAYS_UA[day]}:*\n"
        )

        schedule = NEXT_SCHEDULE.get(
            day,
            {}
        )

        if not schedule:

            text += (
                "Пар немає\n\n"
            )

            continue

        for number, subject in schedule.items():

            call = get_call_time(
                day,
                number
            )

            text += (
                f"{number}. "
                f"{call.get('start', '')}–"
                f"{call.get('end', '')} — "
                f"{subject}\n"
            )

        text += "\n"

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==========================================================
# ВИКЛАДАЧІ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "👨‍🏫 Викладачі"
)
def send_teachers(message):

    register_user(message)

    text = (
        "👨‍🏫 *Список викладачів:*\n\n"
    )

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
        text,
        parse_mode="Markdown"
    )


# ==========================================================
# РОЗКЛАД ДЗВІНКІВ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "⏰ Розклад дзвінків"
)
def send_calls(message):

    register_user(message)

    text = (
        "⏰ *Розклад дзвінків:*\n\n"
        "1 пара — 08:00–09:35\n"
        "2 пара — 09:45–11:20\n"
        "⏸ Велика перерва\n"
        "3 пара — 12:00–13:35\n"
        "4 пара — 13:45–15:20\n"
        "5 пара — 15:30–17:05\n\n"
        "ℹ️ У вівторок 1 пара — 09:00–09:35."
    )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==========================================================
# ZOOM
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🎥 Zoom"
)
def send_zoom(message):

    register_user(message)

    markup = types.InlineKeyboardMarkup()

    for name, data in SUBJECTS.items():

        zoom = data.get(
            "zoom",
            ""
        )

        if (
            isinstance(zoom, str)
            and zoom.startswith("http")
        ):

            markup.add(
                types.InlineKeyboardButton(
                    f"🎥 {name}",
                    url=zoom
                )
            )

    bot.send_message(
        message.chat.id,
        "🎥 *Обери предмет:*",
        parse_mode="Markdown",
        reply_markup=markup
    )


# ==========================================================
# GOOGLE CLASSROOM
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📝 Google Classroom"
)
def send_classroom(message):

    register_user(message)

    markup = types.InlineKeyboardMarkup()

    for name, data in SUBJECTS.items():

        classroom = data.get(
            "classroom",
            ""
        )

        if (
            isinstance(classroom, str)
            and classroom.startswith("http")
        ):

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

        parse_mode="Markdown",
        reply_markup=markup
    )


# ==========================================================
# ЧАТ ГРУПИ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "💬 Чат групи Е-21"
)
def group_chat(message):

    register_user(message)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "💬 Відкрити чат групи Е-21",
            url=GROUP_CHAT_URL
        )
    )

    bot.send_message(
        message.chat.id,

        "💬 *Чат групи Е-21*\n\n"
        "Натисни кнопку нижче, щоб перейти до чату.",

        parse_mode="Markdown",
        reply_markup=markup
    )


# ==========================================================
# ДОНАТ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🥤 Кинь монету адміну на Кока-Колу"
)
def donate(message):

    register_user(message)

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "🥤 Кинути монетку",
            url=DONATE_URL
        )
    )

    bot.send_message(
        message.chat.id,

        "🥤 *Підтримати адміна на Кока-Колу* 😂\n\n"
        "Якщо бот тобі допомагає — можеш пригостити "
        "адміна Кока-Колою 🥤",

        parse_mode="Markdown",
        reply_markup=markup
    )


# ==========================================================
# БОТ НЕ ПРАЦЮЄ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🚨 БОТ НЕ ПРАЦЮЄ!!!"
)
def bot_not_working(message):

    register_user(message)

    feedback_waiting.add(
        message.chat.id
    )

    bot.send_message(
        message.chat.id,

        "🚨 *Опис проблеми*\n\n"
        "Напиши одним повідомленням, що саме "
        "не працює.\n\n"
        "Наприклад:\n"
        "• не показує розклад\n"
        "• не відкривається Zoom\n"
        "• не приходять сповіщення\n"
        "• не працює кнопка",

        parse_mode="Markdown"
    )


# ==========================================================
# ОТРИМАННЯ СКАРГИ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.chat.id in feedback_waiting
)
def receive_feedback(message):

    register_user(message)

    feedback_waiting.discard(
        message.chat.id
    )

    first_name = (
        message.from_user.first_name
        or ""
    )

    last_name = (
        message.from_user.last_name
        or ""
    )

    full_name = (
        f"{first_name} {last_name}"
    ).strip()

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "немає"
    )

    feedback_text = (
        message.text
        if message.text
        else "Користувач надіслав повідомлення без тексту."
    )

    admin_message = (
        "🚨 *БОТ НЕ ПРАЦЮЄ!!!*\n\n"
        f"👤 Користувач: {full_name or 'Не вказано'}\n"
        f"🔹 Username: {username}\n"
        f"🆔 ID: {message.from_user.id}\n\n"
        f"💬 Проблема:\n{feedback_text}"
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "✉️ Відповісти користувачу",
            callback_data=f"reply:{message.chat.id}"
        )
    )

    try:

        bot.send_message(
            ADMIN_ID,
            admin_message,
            parse_mode="Markdown",
            reply_markup=markup
        )

        bot.send_message(
            message.chat.id,

            "✅ Повідомлення відправлено адміністратору.\n\n"
            "Дякую! Я розберуся з проблемою.",

            reply_markup=get_main_keyboard(
                is_admin=message.chat.id == ADMIN_ID
            )
        )

    except Exception as error:

        print(
            f"Помилка відправки звернення: {error}"
        )

        bot.send_message(
            message.chat.id,
            "❌ Не вдалося відправити повідомлення адміністратору."
        )


# ==========================================================
# ВІДПОВІДЬ АДМІНІСТРАТОРА
# ==========================================================

@bot.callback_query_handler(
    func=lambda call:
    isinstance(call.data, str)
    and call.data.startswith("reply:")
)
def start_admin_reply(call):

    if call.from_user.id != ADMIN_ID:

        bot.answer_callback_query(
            call.id,
            "У вас немає доступу."
        )

        return

    try:

        target_id = int(
            call.data.split(
                ":",
                1
            )[1]
        )

        admin_reply_targets[
            ADMIN_ID
        ] = target_id

        bot.answer_callback_query(
            call.id
        )

        bot.send_message(
            ADMIN_ID,

            "✉️ *Напиши відповідь користувачу.*\n\n"
            "Наступне повідомлення буде відправлено "
            "саме цьому користувачу.",

            parse_mode="Markdown"
        )

    except Exception as error:

        print(
            f"Помилка відповіді користувачу: {error}"
        )

        bot.answer_callback_query(
            call.id,
            "Помилка."
        )


@bot.message_handler(
    func=lambda message:
    message.from_user.id == ADMIN_ID
    and message.chat.id == ADMIN_ID
    and ADMIN_ID in admin_reply_targets
)
def send_admin_reply(message):

    target_id = admin_reply_targets.pop(
        ADMIN_ID,
        None
    )

    if target_id is None:
        return

    reply_text = (
        message.text
        if message.text
        else "Адміністратор надіслав повідомлення."
    )

    try:

        bot.send_message(
            target_id,

            "👨‍💻 *Повідомлення від адміністратора:*\n\n"
            f"{reply_text}",

            parse_mode="Markdown"
        )

        bot.send_message(
            ADMIN_ID,
            "✅ Відповідь відправлена користувачу."
        )

    except Exception as error:

        print(
            f"Помилка відправки відповіді: {error}"
        )

        bot.send_message(
            ADMIN_ID,

            f"❌ Не вдалося відправити відповідь.\n\n"
            f"Помилка: {error}"
        )


# ==========================================================
# ОГОЛОШЕННЯ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "📢 Оголошення"
)
def start_announcement(message):

    if message.chat.id != ADMIN_ID:

        bot.send_message(
            message.chat.id,
            "У вас немає доступу до цієї функції."
        )

        return

    announcement_waiting.add(
        ADMIN_ID
    )

    bot.send_message(
        ADMIN_ID,

        "📢 *Нове оголошення*\n\n"
        "Напиши текст, який потрібно розіслати всій групі.",

        parse_mode="Markdown"
    )


# ==========================================================
# ВІДПРАВКА ОГОЛОШЕННЯ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.from_user.id == ADMIN_ID
    and message.chat.id == ADMIN_ID
    and ADMIN_ID in announcement_waiting
)
def send_announcement(message):

    announcement_waiting.discard(
        ADMIN_ID
    )

    announcement_text = (
        message.text
        if message.text
        else "Оголошення без тексту."
    )

    text = (
        "📢 *ОГОЛОШЕННЯ*\n\n"
        f"{announcement_text}"
    )

    recipients = set(
        known_users
    )

    recipients.update(
        subscribed_users
    )

    recipients.discard(
        ADMIN_ID
    )

    sent_count = 0
    failed_count = 0

    for chat_id in list(
        recipients
    ):

        try:

            bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown"
            )

            sent_count += 1

        except Exception as error:

            failed_count += 1

            print(
                f"Не вдалося надіслати "
                f"оголошення {chat_id}: {error}"
            )

    bot.send_message(
        ADMIN_ID,

        "✅ *Оголошення розіслано!*\n\n"
        f"📨 Надіслано: {sent_count}\n"
        f"❌ Не доставлено: {failed_count}",

        parse_mode="Markdown"
    )


# ==========================================================
# ХТО ЧЕРГУЄ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🧹 Хто чергує завтра?"
)
def random_student(message):

    register_user(message)

    student = random.choice(
        STUDENTS
    )

    bot.send_message(
        message.chat.id,

        "🧹 *Черговий завтра:*\n\n"
        f"👤 {student}",

        parse_mode="Markdown"
    )


# ==========================================================
# СПИСОК ГРУПИ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "👥 Список групи"
)
def group_list(message):

    register_user(message)

    text = (
        "👥 *Список групи Е-21:*\n\n"
    )

    for number, student in enumerate(
        STUDENTS,
        1
    ):

        text += (
            f"{number}. {student}\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==========================================================
# СПОВІЩЕННЯ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🔔 Увімкнути/вимкнути сповіщення"
)
def toggle_notifications(message):

    register_user(message)

    user_id = message.chat.id

    if user_id in subscribed_users:

        subscribed_users.remove(
            user_id
        )

        save_subscribers()

        bot.send_message(
            user_id,
            "🔕 Сповіщення вимкнено."
        )

    else:

        subscribed_users.add(
            user_id
        )

        save_subscribers()

        bot.send_message(
            user_id,

            "🔔 Сповіщення увімкнено!\n\n"
            "Нагадування надходитимуть "
            "за 10 хвилин до початку пари "
            "та в момент її початку."
        )


# ==========================================================
# КНОПКИ НАГАДУВАННЯ
# ==========================================================

def get_lesson_markup(subject):

    markup = types.InlineKeyboardMarkup()

    info = SUBJECTS.get(
        subject
    )

    if not info:
        return markup

    zoom = info.get(
        "zoom",
        ""
    )

    if (
        isinstance(zoom, str)
        and zoom.startswith("http")
    ):

        markup.add(
            types.InlineKeyboardButton(
                "🎥 Відкрити Zoom",
                url=zoom
            )
        )

    classroom = info.get(
        "classroom",
        ""
    )

    if (
        isinstance(classroom, str)
        and classroom.startswith("http")
    ):

        markup.add(
            types.InlineKeyboardButton(
                "📚 Google Classroom",
                url=classroom
            )
        )

    return markup


# ==========================================================
# НАГАДУВАННЯ ЗА 10 ХВИЛИН
# ==========================================================

def send_lesson_notification(
    number,
    subject,
    start
):

    text = (
        "🔔 *Через 10 хвилин починається пара!*\n\n"
        f"*{number} пара* — {subject}\n"
        f"⏰ Початок: {start.strftime('%H:%M')}"
    )

    markup = get_lesson_markup(
        subject
    )

    for chat_id in list(
        subscribed_users
    ):

        try:

            bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=markup
            )

        except Exception as error:

            print(
                f"Не вдалося надіслати "
                f"нагадування {chat_id}: {error}"
            )


# ==========================================================
# ПАРА ПОЧАЛАСЯ
# ==========================================================

def send_lesson_started_notification(
    number,
    subject,
    start
):

    text = (
        "▶️ *Пара почалася!*\n\n"
        f"*{number} пара* — {subject}\n"
        f"⏰ Початок: {start.strftime('%H:%M')}"
    )

    markup = get_lesson_markup(
        subject
    )

    for chat_id in list(
        subscribed_users
    ):

        try:

            bot.send_message(
                chat_id,
                text,
                parse_mode="Markdown",
                reply_markup=markup
            )

        except Exception as error:

            print(
                f"Не вдалося надіслати "
                f"повідомлення про початок "
                f"{chat_id}: {error}"
            )


# ==========================================================
# ПЕРЕВІРКА НАГАДУВАНЬ
# ==========================================================

def check_notifications():

    now = datetime.now(
        KYIV
    ).replace(
        second=0,
        microsecond=0
    )

    today = now.date()

    schedule, week_type = get_schedule_for_date(
        today
    )

    if schedule is None:
        return

    if not subscribed_users:
        return

    day = today.strftime(
        "%A"
    )

    day_schedule = schedule.get(
        day,
        {}
    )

    if not day_schedule:
        return

    for number, subject in day_schedule.items():

        call = get_call_time(
            day,
            number
        )

        if not call:
            continue

        start_text = call.get(
            "start"
        )

        if not start_text:
            continue

        try:

            start_clock = datetime.strptime(
                start_text,
                "%H:%M"
            ).time()

        except ValueError:

            print(
                f"Неправильний час для "
                f"{number} пари: {start_text}"
            )

            continue

        start = datetime.combine(
            today,
            start_clock
        ).replace(
            tzinfo=KYIV
        )

        difference = (
            start - now
        ).total_seconds()

        # --------------------------------------------------
        # ЗА 10 ХВИЛИН
        # --------------------------------------------------

        if 570 <= difference <= 630:

            key = (
                f"{today.isoformat()}_"
                f"{number}_10"
            )

            if key not in sent_notifications:

                sent_notifications.add(
                    key
                )

                print(
                    f"Надсилаю нагадування за 10 хвилин: "
                    f"{number} пара — {subject}"
                )

                send_lesson_notification(
                    number,
                    subject,
                    start
                )

        # --------------------------------------------------
        # В МОМЕНТ ПОЧАТКУ
        # --------------------------------------------------

        if 0 <= difference <= 30:

            key = (
                f"{today.isoformat()}_"
                f"{number}_start"
            )

            if key not in sent_notifications:

                sent_notifications.add(
                    key
                )

                print(
                    f"Надсилаю повідомлення про початок: "
                    f"{number} пара — {subject}"
                )

                send_lesson_started_notification(
                    number,
                    subject,
                    start
                )

    # ------------------------------------------------------
    # ОЧИЩЕННЯ СТАРИХ КЛЮЧІВ
    # ------------------------------------------------------

    today_prefix = (
        today.isoformat()
    )

    old_keys = {
        key
        for key in sent_notifications
        if not key.startswith(
            today_prefix
        )
    }

    sent_notifications.difference_update(
        old_keys
    )


# ==========================================================
# ПОШУК ПРЕДМЕТІВ
# ЦЕЙ ОБРОБНИК ЗАВЖДИ ОСТАННІЙ
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
        "виховна"
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
        "матеріал",
        "матеріали",
        "материалы",
        "електро",
        "електротехнічні",
        "электро"
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
        "матемю",
        "алгебра"
    ],

    "Біологія і екологія": [
        "біо",
        "био",
        "біологія",
        "биология",
        "екологія",
        "экология"
    ]
}


@bot.message_handler(
    func=lambda message:
    message.text is not None
)
def search_subject(message):

    register_user(message)

    text = (
        message.text.lower().strip()
    )

    for subject_name, keywords in SEARCH_WORDS.items():

        for keyword in keywords:

            if keyword in text:

                info_text, markup = get_subject_info(
                    subject_name
                )

                if info_text:

                    bot.send_message(
                        message.chat.id,
                        info_text,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )

                return

    bot.send_message(
        message.chat.id,

        "❓ Не зрозумів.\n\n"
        "Напиши предмет або скорочення:\n\n"
        "• укр\n"
        "• матем\n"
        "• англ\n"
        "• фізика\n"
        "• біо\n"
        "• кон"
    )


# ==========================================================
# ПЛАНУВАЛЬНИК
# ==========================================================

scheduler = BackgroundScheduler(
    timezone=KYIV
)

scheduler.add_job(
    check_notifications,
    "interval",
    seconds=30,
    id="lesson_notifications",
    replace_existing=True,
    max_instances=1,
    coalesce=True
)

scheduler.start()


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


# ==========================================================
# ЗАПУСК RENDER
# ==========================================================

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
