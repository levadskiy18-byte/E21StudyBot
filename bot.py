import os
import json
import random
from datetime import datetime, timedelta, timezone

import telebot
from telebot import types
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

from data import CALLS, SUBJECTS, SCHEDULE


# ==============================
# НАСТРОЙКИ БОТА
# ==============================

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN не знайдено! Додай його в Environment Variables на Render.")

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
# ЧАС КИЄВА
# ==============================

def get_kyiv_time():
    kyiv_timezone = timezone(timedelta(hours=3))
    return datetime.now(kyiv_timezone)


# ==============================
# ПІДПИСНИКИ НА СПОВІЩЕННЯ
# ==============================

def load_subscribers():
    if not os.path.exists(SUBSCRIBERS_FILE):
        return set()

    try:
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as file:
            return set(json.load(file))

    except Exception:
        return set()


def save_subscribers(subscribers):
    try:
        with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as file:
            json.dump(list(subscribers), file)

    except Exception as error:
        print(f"Помилка збереження підписників: {error}")


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
        "🧹 Хто чергує завтра?",
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
        f"👨‍🏫 Викладач: {teacher}"
    )

    markup = types.InlineKeyboardMarkup()

    if data.get("zoom"):

        markup.add(
            types.InlineKeyboardButton(
                "🎥 Zoom",
                url=data["zoom"]
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
# КОМАНДА START
# ==============================

@bot.message_handler(commands=["start"])
def send_welcome(message):

    bot.send_message(
        message.chat.id,
        "🎓 *Вітаю!*\n\n"
        "Це Telegram-бот групи *Е-21*.\n\n"
        "Тут ти можеш переглянути:\n"
        "📅 Розклад пар\n"
        "📚 Предмети\n"
        "👨‍🏫 Викладачів\n"
        "🎥 Zoom\n"
        "📝 Google Classroom\n"
        "🔔 Нагадування про пари\n\n"
        "Обери потрібний пункт нижче 👇",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
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

        subscribed_users.remove(user_id)

        save_subscribers(
            subscribed_users
        )

        bot.send_message(
            user_id,
            "🔕 Сповіщення вимкнено."
        )

    else:

        subscribed_users.add(user_id)

        save_subscribers(
            subscribed_users
        )

        bot.send_message(
            user_id,
            "🔔 Сповіщення увімкнено!\n\n"
            "Бот нагадуватиме про пару за 5 хвилин до її початку."
        )


# ==============================
# РОЗКЛАД ДЗВІНКІВ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "⏰ Розклад дзвінків"
)
def send_calls(message):

    text = "⏰ *Розклад дзвінків:*\n\n"

    for number, times in CALLS.items():

        text += (
            f"{number} пара: "
            f"{times['start']} — "
            f"{times['end']}\n"
        )

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
# ВИКЛАДАЧІ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "👨‍🏫 Викладачі"
)
def send_teachers(message):

    text = "👨‍🏫 *Список викладачів:*\n\n"

    for name, data in SUBJECTS.items():

        teacher = data.get(
            "teacher",
            "Не вказано"
        )

        text += (
            f"• *{name}*\n"
            f"👨‍🏫 {teacher}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==============================
# ПОСИЛАННЯ ZOOM
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🎥 Zoom"
)
def send_zoom_links(message):

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
            "❌ Посилання на Zoom поки що не додані."
        )

        return

    bot.send_message(
        message.chat.id,
        "🎥 *Посилання на Zoom:*\n\n"
        "Обери потрібний предмет:",
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
def send_classroom_links(message):

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
            "❌ Посилання на Google Classroom поки що не додані."
        )

        return

    bot.send_message(
        message.chat.id,
        "📚 *Google Classroom:*\n\n"
        "Обери потрібний предмет:",
        parse_mode="Markdown",
        reply_markup=markup
    )


# ==============================
# РОЗКЛАД НА СЬОГОДНІ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "📅 Сьогодні"
)
def send_today_schedule(message):

    now = get_kyiv_time()

    today = now.strftime("%A")

    day_ua = DAYS_UA.get(
        today,
        today
    )

    day_schedule = SCHEDULE.get(
        today,
        {}
    )

    if not day_schedule:

        bot.send_message(
            message.chat.id,
            f"📅 *Розклад на сьогодні ({day_ua}):*\n\n"
            "Сьогодні пар немає! 🎉",
            parse_mode="Markdown"
        )

        return

    text = (
        f"📅 *Розклад на сьогодні ({day_ua}):*\n\n"
    )

    for number, subject in day_schedule.items():

        time_info = CALLS.get(
            number,
            {}
        )

        start = time_info.get(
            "start",
            ""
        )

        end = time_info.get(
            "end",
            ""
        )

        text += (
            f"*{number} пара:* {subject}\n"
            f"🕒 {start} — {end}\n\n"
        )

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
    )


# ==============================
# РОЗКЛАД НА ЗАВТРА
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🔮 Завтра"
)
def send_tomorrow_schedule(message):

    tomorrow_date = (
        get_kyiv_time()
        + timedelta(days=1)
    )

    tomorrow = tomorrow_date.strftime(
        "%A"
    )

    day_ua = DAYS_UA.get(
        tomorrow,
        tomorrow
    )

    day_schedule = SCHEDULE.get(
        tomorrow,
        {}
    )

    if not day_schedule:

        bot.send_message(
            message.chat.id,
            f"🔮 *Розклад на завтра ({day_ua}):*\n\n"
            "Завтра пар немає! 🎉",
            parse_mode="Markdown"
        )

        return

    text = (
        f"🔮 *Розклад на завтра ({day_ua}):*\n\n"
    )

    for number, subject in day_schedule.items():

        time_info = CALLS.get(
            number,
            {}
        )

        start = time_info.get(
            "start",
            ""
        )

        end = time_info.get(
            "end",
            ""
        )

        text += (
            f"*{number} пара:* {subject}\n"
            f"🕒 {start} — {end}\n\n"
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
def send_week_schedule(message):

    text = (
        "🗓 *Розклад на тиждень:*\n\n"
    )

    week_days = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday"
    ]

    for day in week_days:

        day_ua = DAYS_UA.get(
            day,
            day
        )

        day_schedule = SCHEDULE.get(
            day,
            {}
        )

        text += (
            f"📌 *{day_ua}:*\n"
        )

        if day_schedule:

            for number, subject in day_schedule.items():

                time_info = CALLS.get(
                    number,
                    {}
                )

                start = time_info.get(
                    "start",
                    ""
                )

                end = time_info.get(
                    "end",
                    ""
                )

                text += (
                    f"{number} пара "
                    f"({start}–{end}) — "
                    f"{subject}\n"
                )

        else:

            text += "Пар немає\n"

        text += "\n"

    bot.send_message(
        message.chat.id,
        text,
        parse_mode="Markdown"
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
# ХТО ЧЕРГУЄ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "🧹 Хто чергує завтра?"
)
def random_student(message):

    chosen = random.choice(
        STUDENTS
    )

    bot.send_message(
        message.chat.id,
        f"🧹 *Черговий завтра:*\n\n"
        f"👤 {chosen}",
        parse_mode="Markdown"
    )


# ==============================
# СПИСОК ГРУПИ
# ==============================

@bot.message_handler(
    func=lambda message:
    message.text == "👥 Список групи"
)
def send_group_list(message):

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
# НАГАДУВАННЯ ПРО ПАРИ
# ==============================

def check_and_send_notifications():

    now = get_kyiv_time()

    today = now.strftime(
        "%A"
    )

    current_time = now.strftime(
        "%H:%M"
    )

    day_schedule = SCHEDULE.get(
        today,
        {}
    )

    for number, subject_name in day_schedule.items():

        call_info = CALLS.get(
            number
        )

        if not call_info:

            continue

        start_time = datetime.strptime(
            call_info["start"],
            "%H:%M"
        )

        notification_time = (
            start_time
            - timedelta(minutes=5)
        ).strftime("%H:%M")

        if current_time == notification_time:

            info_text, markup = get_subject_info(
                subject_name
            )

            if not info_text:

                continue

            text = (
                "🔔 *Через 5 хвилин починається пара!*\n\n"
                f"{info_text}"
            )

            for user_id in list(
                subscribed_users
            ):

                try:

                    bot.send_message(
                        user_id,
                        text,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )

                except Exception as error:

                    print(
                        f"Помилка надсилання "
                        f"{user_id}: {error}"
                    )


# ==============================
# ПЛАНУВАЛЬНИК
# ==============================

scheduler = BackgroundScheduler()

scheduler.add_job(
    check_and_send_notifications,
    "interval",
    minutes=1
)

scheduler.start()


# ==============================
# ЗАПУСК БОТА
# ==============================

if __name__ == "__main__":

    bot.remove_webhook()

    bot.infinity_polling(
        skip_pending=True,
        timeout=20
    )
