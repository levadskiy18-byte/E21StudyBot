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

from data import CALLS, SUBJECTS, SCHEDULE


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

# Твій Telegram ID
ADMIN_ID = 857901222

# Користувачі, які зараз пишуть звернення
feedback_waiting = set()

# Кому адміністратор зараз відповідає
admin_reply_targets = {}

# Очікуємо від адміністратора текст оголошення
announcement_waiting = set()


# ==========================================================
# ПОСИЛАННЯ НА ДОНАТ
# ==========================================================

DONATE_URL = (
    "https://send.monobank.ua/jar/5r7iFcvzb7"
)


# ==========================================================
# ВІВТОРОК — ВИНЯТОК
# ==========================================================
# У вівторок 1 пара починається о 09:00.
# В інші дні використовуються CALLS з data.py.
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
# СПИСОК ГРУПИ Е-21
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
# ПІДПИСНИКИ НА СПОВІЩЕННЯ
# ==========================================================

def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
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
            f"Помилка завантаження підписників: {error}"
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
            f"Помилка збереження підписників: {error}"
        )


subscribed_users = load_subscribers()


# ==========================================================
# ВСІ ВІДОМІ КОРИСТУВАЧІ БОТА
# ==========================================================

def load_users():
    if not os.path.exists(USERS_FILE):
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
            f"Помилка завантаження користувачів: {error}"
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
            f"Помилка збереження користувачів: {error}"
        )


known_users = load_users()


def register_user(message):
    try:
        user_id = message.chat.id

        if user_id not in known_users:
            known_users.add(user_id)
            save_users()

    except Exception as error:
        print(
            f"Помилка реєстрації користувача: {error}"
        )


# ==========================================================
# ЗАПОБІГАННЯ ПОВТОРНИМ НАГАДУВАННЯМ
# ==========================================================

sent_notifications = set()


# ==========================================================
# ЧАСИ ПАР
# ==========================================================

def get_calls_for_day(day_name):
    if day_name == "Tuesday":
        return TUESDAY_CALLS

    return CALLS


def get_call_time(day_name, number):
    calls = get_calls_for_day(day_name)

    return calls.get(
        str(number),
        {}
    )


# ==========================================================
# ГОЛОВНЕ МЕНЮ
# ==========================================================

def get_main_keyboard(is_admin=False):

    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    markup.row(
        "📅 Сьогодні",
        "🔮 Завтра"
    )

    markup.row(
        "🗓 Розклад на тиждень"
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
# ПОШУК ПРЕДМЕТІВ
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


# ==========================================================
# WEB-СЕРВЕР ДЛЯ RENDER
# ==========================================================

@app.route("/")
def index():
    return "Бот групи Е-21 працює!", 200


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
        "Також можеш просто написати назву "
        "або скорочення предмета:\n\n"
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
# СЬОГОДНІ / ЗАВТРА
# ==========================================================

def send_schedule_for(
    message,
    target_date,
    title
):

    register_user(message)

    day = target_date.strftime(
        "%A"
    )

    schedule = SCHEDULE.get(
        day,
        {}
    )

    day_ua = DAYS_UA.get(
        day,
        day
    )

    if not schedule:

        bot.send_message(
            message.chat.id,

            f"*{title} {day_ua}*\n\n"
            "Пар немає 🎉",

            parse_mode="Markdown"
        )

        return

    text = (
        f"*{title} {day_ua}:*\n\n"
    )

    for number, subject in schedule.items():

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


@bot.message_handler(
    func=lambda message:
    message.text == "📅 Сьогодні"
)
def send_today(message):

    send_schedule_for(
        message,
        datetime.now(KYIV),
        "📅 Розклад на сьогодні —"
    )


@bot.message_handler(
    func=lambda message:
    message.text == "🔮 Завтра"
)
def send_tomorrow(message):

    send_schedule_for(
        message,
        datetime.now(KYIV) + timedelta(days=1),
        "🔮 Розклад на завтра —"
    )


# ==========================================================
# РОЗКЛАД НА ТИЖДЕНЬ
# ==========================================================

@bot.message_handler(
    func=lambda message:
    message.text == "🗓 Розклад на тиждень"
)
def send_week(message):

    register_user(message)

    text = (
        "🗓 *Розклад на тиждень:*\n\n"
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

        schedule = SCHEDULE.get(
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
        "5 пара — 15:30–17:05"
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
            url="https://t.me/+GaN9ZTAYn_01ODRi"
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
# ВІДПРАВКА ОГОЛОШЕННЯ ВСІМ
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
            "за 10 хвилин до початку пари."
        )


# ==========================================================
# ВІДПРАВКА НАГАДУВАННЯ
# ==========================================================

def send_lesson_notification(
    number,
    subject,
    start
):

    info = SUBJECTS.get(
        subject
    )

    text = (
        "🔔 *Через 10 хвилин починається пара!*\n\n"
        f"*{number} пара* — {subject}\n"
        f"⏰ Початок: {start.strftime('%H:%M')}"
    )

    markup = types.InlineKeyboardMarkup()

    if info:

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
                f"сповіщення {chat_id}: {error}"
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

    day = now.strftime(
        "%A"
    )

    schedule = SCHEDULE.get(
        day,
        {}
    )

    if not schedule:
        return

    if not subscribed_users:
        return

    for number, subject in schedule.items():

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
            now.date(),
            start_clock
        ).replace(
            tzinfo=KYIV
        )

        difference = (
            start - now
        ).total_seconds()

        if 570 <= difference <= 630:

            key = (
                f"{now.date().isoformat()}_"
                f"{number}"
            )

            if key in sent_notifications:
                continue

            sent_notifications.add(
                key
            )

            print(
                f"Надсилаю нагадування: "
                f"{number} пара — {subject}"
            )

            send_lesson_notification(
                number,
                subject,
                start
            )

    today_prefix = (
        now.date().isoformat()
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
# ПОШУК ПО ПРЕДМЕТАХ
# ЦЕЙ ОБРОБНИК ОСТАННІЙ
# ==========================================================

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
    replace_existing=True
)

scheduler.start()


# ==========================================================
# ЗАПУСК TELEGRAM-БОТА
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
