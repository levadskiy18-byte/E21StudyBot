import os
import json
import random
import threading
from datetime import datetime, timedelta

import telebot
from telebot import types
from flask import Flask

from data import CALLS, SUBJECTS, SCHEDULE


# ==============================
# НАСТРОЙКИ
# ==============================

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError(
        "BOT_TOKEN не знайдено! "
        "Додай його в Environment Variables на Render."
    )

bot = telebot.TeleBot(TOKEN)

app = Flask(__name__)

SUBSCRIBERS_FILE = "subscribers.json"


# ==============================
# СПИСОК ГРУПИ Е-21
# ==============================

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


# ==============================
# ДНІ ТИЖНЯ
# ==============================

DAYS_UA = {
    "Monday": "Понеділок",
    "Tuesday": "Вівторок",
    "Wednesday": "Середа",
    "Thursday": "Четвер",
    "Friday": "П'ятниця",
    "Saturday": "Субота",
    "Sunday": "Неділя"
}


# ==============================
# ПІДПИСНИКИ
# ==============================

def load_subscribers():

    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()

    try:

        with open(
            SUBSCRIBERS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return set(json.load(file))

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
                list(subscribed_users),
                file
            )

    except Exception as error:

        print(
            f"Помилка збереження підписників: {error}"
        )


subscribed_users = load_subscribers()


# ==============================
# ГОЛОВНЕ МЕНЮ
# ==============================

def get_main_keyboard():

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
        "🔔 Увімкнути/вимкнути сповіщення"
    )

    return markup


# ==============================
# ІНФОРМАЦІЯ ПРО ПРЕДМЕТ
# ==============================

def get_subject_info(subject_name):

    data = SUBJECTS.get(subject_name)

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

    zoom = data.get(
        "zoom",
        ""
    )

    if zoom.startswith("http"):

        markup.add(
            types.InlineKeyboardButton(
                "🎥 Відкрити Zoom",
                url=zoom
            )
        )

    classroom = data.get(
        "classroom",
        ""
    )

    if classroom.startswith("http"):

        markup.add(
            types.InlineKeyboardButton(
                "📚 Google Classroom",
                url=classroom
            )
        )

    return text, markup


# ==============================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
# ==============================

@app.route("/")
def index():

    return "Бот групи Е-21 працює!", 200


# ==============================
# START
# ==============================

@bot.message_handler(
    commands=["start"]
)
def send_welcome(message):

    bot.send_message(
        message.chat.id,
        "🎓 *Вітаю!*\n\n"
        "Це Telegram-бот групи *Е-21*.\n\n"
        "Тут можна переглянути розклад, "
        "викладачів та посилання на Zoom і Google Classroom.\n\n"
        "Також можеш просто написати назву предмета:\n\n"
        "• укр\n"
        "• матем\n"
        "• англ\n"
        "• фізика\n"
        "• біо\n"
        "• кон",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )


# ==============================
# СЬОГОДНІ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "📅 Сьогодні"
)
def send_today(message):

    today = datetime.now().strftime(
        "%A"
    )

    day_ua = DAYS_UA.get(
        today,
        today
    )

    schedule = SCHEDULE.get(
        today,
        {}
    )

    if not schedule:

        bot.send_message(
            message.chat.id,
            f"📅 *{day_ua}*\n\n"
            "Сьогодні пар немає 🎉",
            parse_mode="Markdown"
        )

        return

    text = (
        f"📅 *Розклад на сьогодні — "
        f"{day_ua}:*\n\n"
    )

    for number, subject in schedule.items():

        call = CALLS.get(
            number,
            {}
        )

        start = call.get(
            "start",
            ""
        )

        end = call.get(
            "end",
            ""
        )

        text += (
            f"*{number} пара* "
            f"({start}–{end})\n"
            f"📚 {subject}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==============================
# ЗАВТРА
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🔮 Завтра"
)
def send_tomorrow(message):

    tomorrow_date = (
        datetime.now()
        + timedelta(days=1)
    )

    tomorrow = tomorrow_date.strftime(
        "%A"
    )

    day_ua = DAYS_UA.get(
        tomorrow,
        tomorrow
    )

    schedule = SCHEDULE.get(
        tomorrow,
        {}
    )

    if not schedule:

        bot.send_message(
            message.chat.id,
            f"🔮 *{day_ua}*\n\n"
            "Завтра пар немає 🎉",
            parse_mode="Markdown"
        )

        return

    text = (
        f"🔮 *Розклад на завтра — "
        f"{day_ua}:*\n\n"
    )

    for number, subject in schedule.items():

        call = CALLS.get(
            number,
            {}
        )

        start = call.get(
            "start",
            ""
        )

        end = call.get(
            "end",
            ""
        )

        text += (
            f"*{number} пара* "
            f"({start}–{end})\n"
            f"📚 {subject}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==============================
# РОЗКЛАД НА ТИЖДЕНЬ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🗓 Розклад на тиждень"
)
def send_week(message):

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

            call = CALLS.get(
                number,
                {}
            )

            text += (
                f"{number}. "
                f"{call.get('start', '')}"
                f"–"
                f"{call.get('end', '')}"
                f" — {subject}\n"
            )

        text += "\n"

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==============================
# ПРЕДМЕТИ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "📚 Предмети"
)
def send_subjects(message):

    markup = types.InlineKeyboardMarkup()

    for name in SUBJECTS.keys():

        markup.add(
            types.InlineKeyboardButton(
                f"📚 {name}",
                callback_data=f"sub_{name}"
            )
        )

    bot.send_message(
        message.chat.id,
        "📚 *Обери предмет:*",
        parse_mode="Markdown",
        reply_markup=markup
    )


# ==============================
# ВИБІР ПРЕДМЕТА
# ==============================

@bot.callback_query_handler(
    func=lambda call:
    call.data.startswith("sub_")
)
def callback_subject(call):

    subject_name = call.data.replace(
        "sub_",
        "",
        1
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


# ==============================
# ВИКЛАДАЧІ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "👨‍🏫 Викладачі"
)
def send_teachers(message):

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


# ==============================
# РОЗКЛАД ДЗВІНКІВ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "⏰ Розклад дзвінків"
)
def send_calls(message):

    text = (
        "⏰ *Розклад дзвінків:*\n\n"
    )

    for number, times in CALLS.items():

        text += (
            f"{number} пара — "
            f"{times['start']}–"
            f"{times['end']}\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==============================
# ZOOM
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🎥 Zoom"
)
def send_zoom(message):

    markup = types.InlineKeyboardMarkup()

    count = 0

    for name, data in SUBJECTS.items():

        zoom = data.get(
            "zoom",
            ""
        )

        if zoom.startswith("http"):

            markup.add(
                types.InlineKeyboardButton(
                    f"🎥 {name}",
                    url=zoom
                )
            )

            count += 1

    if count == 0:

        bot.send_message(
            message.chat.id,
            "❌ Посилання на Zoom поки що немає."
        )

        return

    bot.send_message(
        message.chat.id,
        "🎥 *Обери предмет:*",
        parse_mode="Markdown",
        reply_markup=markup
    )


# ==============================
# GOOGLE CLASSROOM
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "📝 Google Classroom"
)
def send_classroom(message):

    markup = types.InlineKeyboardMarkup()

    count = 0

    for name, data in SUBJECTS.items():

        classroom = data.get(
            "classroom",
            ""
        )

        if classroom.startswith("http"):

            markup.add(
                types.InlineKeyboardButton(
                    f"📚 {name}",
                    url=classroom
                )
            )

            count += 1

    if count == 0:

        bot.send_message(
            message.chat.id,
            "❌ Посилання на Google Classroom поки що немає."
        )

        return

    bot.send_message(
        message.chat.id,
        "📚 *Google Classroom*\n\n"
        "Обери предмет:",
        parse_mode="Markdown",
        reply_markup=markup
    )


# ==============================
# ХТО ЧЕРГУЄ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🧹 Хто чергує завтра?"
)
def random_student(message):

    student = random.choice(
        STUDENTS
    )

    bot.send_message(
        message.chat.id,
        f"🧹 *Черговий завтра:*\n\n"
        f"👤 {student}",
        parse_mode="Markdown"
    )


# ==============================
# СПИСОК ГРУПИ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "👥 Список групи"
)
def group_list(message):

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


# ==============================
# СПОВІЩЕННЯ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🔔 Увімкнути/вимкнути сповіщення"
)
def toggle_notifications(message):

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
            "🔔 Сповіщення увімкнено!"
        )


# ==============================
# ПОШУК ПРЕДМЕТІВ
# ЦЕЙ ОБРОБНИК ОСТАННІЙ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text is not None
)
def search_subject(message):

    text = message.text.lower().strip()

    search_words = {

        "Українська мова та література": [
            "укр",
            "українська",
            "украинский",
            "література",
            "литература"
        ],

        "Виховні години та фізичне виховання": [
            "фізра",
            "физра",
            "фізичне",
            "физическое",
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
            "матеріали",
            "материалы",
            "електро",
            "електротехнічні",
            "електротехника"
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
        ]
    }

    for subject_name, keywords in search_words.items():

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
        "Напиши назву предмета "
        "або скорочення:\n\n"
        "• укр\n"
        "• матем\n"
        "• англ\n"
        "• фізика\n"
        "• біо\n"
        "• кон"
    )


# ==============================
# ЗАПУСК TELEGRAM-БОТА
# ==============================

def run_bot():

    try:

        bot.remove_webhook()

        print("Telegram-бот запущений!")

        bot.infinity_polling(
            skip_pending=True,
            timeout=30,
            long_polling_timeout=30
        )

    except Exception as error:

        print(
            f"Помилка Telegram-бота: {error}"
        )


# ==============================
# ЗАПУСК
# ==============================

if __name__ == "__main__":

    bot_thread = threading.Thread(
        target=run_bot
    )

    bot_thread.daemon = True

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
