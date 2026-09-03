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


TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise ValueError(
        "BOT_TOKEN не знайдено! Додай його в Environment Variables на Render."
    )

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

KYIV = ZoneInfo("Europe/Kyiv")
SUBSCRIBERS_FILE = "subscribers.json"

# ==========================================================
# ВИНЯТОК ДЛЯ ВІВТОРКА
# У вівторок 1 пара починається о 09:00
# В інші дні використовується CALLS
# ==========================================================

TUESDAY_CALLS = {
    "1": {"start": "09:00", "end": "09:35"},
    "2": {"start": "09:45", "end": "11:20"},
    "3": {"start": "12:00", "end": "13:35"},
    "4": {"start": "13:45", "end": "15:20"},
    "5": {"start": "15:30", "end": "17:05"},
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
    "Тюпа Євген",
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
    "Sunday": "Неділя",
}


# ==========================================================
# ПІДПИСНИКИ
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
            return {int(x) for x in json.load(file)}

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

# Щоб одне й те саме нагадування не надсилалося двічі
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
    return calls.get(number, {})


# ==========================================================
# ГОЛОВНЕ МЕНЮ
# ==========================================================

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


# ==========================================================
# ІНФОРМАЦІЯ ПРО ПРЕДМЕТ
# ==========================================================

def get_subject_info(subject_name):
    subject = SUBJECTS.get(subject_name)

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

    if zoom.startswith("http"):
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

    if classroom.startswith("http"):
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
    ],
}


# ==========================================================
# ВЕБ-СЕРВЕР ДЛЯ RENDER
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
        reply_markup=get_main_keyboard()
    )


# ==========================================================
# ФУНКЦІЯ РОЗКЛАДУ
# ==========================================================

def send_schedule_for(
    message,
    target_date,
    title
):
    day = target_date.strftime("%A")

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
            f"{title} *{day_ua}*\n\n"
            "Пар немає 🎉",
            parse_mode="Markdown"
        )
        return

    text = (
        f"{title} *{day_ua}:*\n\n"
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


# ==========================================================
# СЬОГОДНІ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "📅 Сьогодні"
)
def send_today(message):
    send_schedule_for(
        message,
        datetime.now(KYIV),
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
    send_schedule_for(
        message,
        datetime.now(KYIV) + timedelta(days=1),
        "🔮 *Розклад на завтра —"
    )


# ==========================================================
# РОЗКЛАД НА ТИЖДЕНЬ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🗓 Розклад на тиждень"
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
    func=lambda m:
    m.text == "📚 Предмети"
)
def send_subjects(message):
    markup = types.InlineKeyboardMarkup()

    # ВАЖНО:
    # callback_data коротке, щоб не було
    # BUTTON_DATA_INVALID
    for index, name in enumerate(
        SUBJECTS.keys()
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
    call.data.startswith("sub:")
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

        subject_name = subject_names[index]

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
    func=lambda m:
    m.text == "👨‍🏫 Викладачі"
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


# ==========================================================
# РОЗКЛАД ДЗВІНКІВ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "⏰ Розклад дзвінків"
)
def send_calls(message):
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
    func=lambda m:
    m.text == "🎥 Zoom"
)
def send_zoom(message):
    markup = types.InlineKeyboardMarkup()

    for index, (
        name,
        data
    ) in enumerate(
        SUBJECTS.items()
    ):
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
    func=lambda m:
    m.text == "📝 Google Classroom"
)
def send_classroom(message):
    markup = types.InlineKeyboardMarkup()

    for index, (
        name,
        data
    ) in enumerate(
        SUBJECTS.items()
    ):
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

    bot.send_message(
        message.chat.id,
        "📚 *Google Classroom*\n\n"
        "Обери предмет:",
        parse_mode="Markdown",
        reply_markup=markup
    )


# ==========================================================
# ХТО ЧЕРГУЄ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🧹 Хто чергує завтра?"
)
def random_student(message):
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
    func=lambda m:
    m.text == "👥 Список групи"
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


# ==========================================================
# СПОВІЩЕННЯ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text == "🔔 Увімкнути/вимкнути сповіщення"
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
            "🔔 Сповіщення увімкнено!\n\n"
            "Бот надсилатиме нагадування "
            "за 10 хвилин до початку пари."
        )


# ==========================================================
# ВІДПРАВКА СПОВІЩЕННЯ
# ==========================================================

def send_lesson_notification(
    number,
    subject,
    start_time
):
    info = SUBJECTS.get(
        subject
    )

    text = (
        "🔔 *Через 10 хвилин починається пара!*\n\n"
        f"*{number} пара* — {subject}\n"
        f"⏰ Початок: "
        f"{start_time.strftime('%H:%M')}"
    )

    markup = types.InlineKeyboardMarkup()

    if info:
        zoom = info.get(
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

        classroom = info.get(
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
# ПЕРЕВІРКА СПОВІЩЕНЬ
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

        start_time = datetime.strptime(
            call["start"],
            "%H:%M"
        ).time()

        start = datetime.combine(
            now.date(),
            start_time
        ).replace(
            tzinfo=KYIV
        )

        difference = int(
            (
                start - now
            ).total_seconds()
        )

        # 10 хвилин = 600 секунд
        # Дозволяємо похибку від 570 до 630 секунд
        if 570 <= difference <= 630:

            key = (
                f"{now.date().isoformat()}_"
                f"{number}"
            )

            if key not in sent_notifications:

                sent_notifications.add(
                    key
                )

                send_lesson_notification(
                    number,
                    subject,
                    start
                )

    # Видаляємо старі ключі
    today_prefix = (
        now.date().isoformat()
    )

    sent_notifications.intersection_update(
        {
            key
            for key in sent_notifications
            if key.startswith(
                today_prefix
            )
        }
    )


# ==========================================================
# ПОШУК ПО ПРЕДМЕТАХ
# ЦЕЙ ОБРОБНИК ПОВИНЕН БУТИ ОСТАННІМ
# ==========================================================

@bot.message_handler(
    func=lambda m:
    m.text is not None
)
def search_subject(message):
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
# ПЛАНУВАЛЬНИК СПОВІЩЕНЬ
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
# ЗАПУСК
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
