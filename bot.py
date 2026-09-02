import os
import json
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import telebot
from telebot import types
from flask import Flask

from data import CALLS, SUBJECTS, SCHEDULE

# ==============================

# НАСТРОЙКИ БОТА

# ==============================

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
raise ValueError(
"BOT_TOKEN не знайдено! Додай токен у Environment Variables на Render."
)

bot = telebot.TeleBot(TOKEN)
app = Flask(**name**)

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

# ЧАС УКРАЇНИ

# ==============================

KYIV_TZ = ZoneInfo("Europe/Kyiv")

def get_kyiv_time():
return datetime.now(KYIV_TZ)

# ==============================

# ПІДПИСНИКИ

# ==============================

def load_subscribers():

```
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
    print(f"Помилка завантаження підписників: {error}")
    return set()
```

def save_subscribers(subscribers):

```
try:
    with open(
        SUBSCRIBERS_FILE,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            list(subscribers),
            file
        )

except Exception as error:
    print(f"Помилка збереження підписників: {error}")
```

subscribed_users = load_subscribers()

# ==============================

# ГОЛОВНЕ МЕНЮ

# ==============================

def get_main_keyboard():

```
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
```

# ==============================

# ІНФОРМАЦІЯ ПРО ПРЕДМЕТ

# ==============================

def get_subject_info(subject_name):

```
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
            "📝 Google Classroom",
            url=classroom
        )
    )

return text, markup
```

# ==============================

# WEB-СЕРВЕР ДЛЯ RENDER

# ==============================

@app.route("/")
def index():

```
return "Бот групи Е-21 працює!", 200
```

# ==============================

# START

# ==============================

@bot.message_handler(commands=["start"])
def send_welcome(message):

```
bot.send_message(
    message.chat.id,
    "🎓 *Вітаю!*\n\n"
    "Це Telegram-бот групи *Е-21*.\n\n"
    "Можна:\n"
    "📅 Дивитися розклад\n"
    "🎥 Отримувати Zoom-посилання\n"
    "📝 Відкривати Google Classroom\n"
    "🔔 Увімкнути нагадування\n\n"
    "💡 Також просто напиши назву предмета.\n"
    "Наприклад: *укр*, *матем*, *англ*, *біо*.",
    parse_mode="Markdown",
    reply_markup=get_main_keyboard()
)
```

# ==============================

# СПОВІЩЕННЯ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "🔔 Увімкнути/вимкнути сповіщення"
)
def toggle_notifications(message):

```
user_id = message.chat.id

if user_id in subscribed_users:

    subscribed_users.remove(user_id)
    save_subscribers(subscribed_users)

    bot.send_message(
        user_id,
        "🔕 Сповіщення вимкнено."
    )

else:

    subscribed_users.add(user_id)
    save_subscribers(subscribed_users)

    bot.send_message(
        user_id,
        "🔔 Сповіщення увімкнено!\n\n"
        "Бот нагадуватиме про пару за 5 хвилин до початку."
    )
```

# ==============================

# РОЗКЛАД ДЗВІНКІВ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "⏰ Розклад дзвінків"
)
def send_calls(message):

```
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
```

# ==============================

# ПРЕДМЕТИ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "📚 Предмети"
)
def send_subjects(message):

```
markup = types.InlineKeyboardMarkup()

for number, name in enumerate(
    SUBJECTS.keys()
):

    markup.add(
        types.InlineKeyboardButton(
            f"📚 {name}",
            callback_data=f"sub_{number}"
        )
    )

bot.send_message(
    message.chat.id,
    "📚 *Обери предмет:*",
    parse_mode="Markdown",
    reply_markup=markup
)
```

# ==============================

# ВИБІР ПРЕДМЕТА

# ==============================

@bot.callback_query_handler(
func=lambda call:
call.data.startswith("sub_")
)
def callback_subject(call):

```
try:

    subject_number = int(
        call.data.replace(
            "sub_",
            "",
            1
        )
    )

    subjects_list = list(
        SUBJECTS.keys()
    )

    subject_name = subjects_list[
        subject_number
    ]

except Exception:

    bot.answer_callback_query(
        call.id,
        "Помилка. Спробуй ще раз."
    )

    return

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
```

# ==============================

# ВИКЛАДАЧІ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "👨‍🏫 Викладачі"
)
def send_teachers(message):

```
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
    text,
    parse_mode="Markdown"
)
```

# ==============================

# ZOOM

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "🎥 Zoom"
)
def send_zoom_links(message):

```
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
        "❌ Посилання на Zoom поки немає."
    )

    return

bot.send_message(
    message.chat.id,
    "🎥 *Zoom-посилання:*\n\n"
    "Обери потрібний предмет:",
    parse_mode="Markdown",
    reply_markup=markup
)
```

# ==============================

# GOOGLE CLASSROOM

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "📝 Google Classroom"
)
def send_classroom_links(message):

```
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
                f"📝 {name}",
                url=classroom
            )
        )

        count += 1

if count == 0:

    bot.send_message(
        message.chat.id,
        "❌ Посилань на Google Classroom поки немає."
    )

    return

bot.send_message(
    message.chat.id,
    "📝 *Google Classroom:*\n\n"
    "Обери потрібний предмет:",
    parse_mode="Markdown",
    reply_markup=markup
)
```

# ==============================

# РОЗКЛАД НА СЬОГОДНІ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "📅 Сьогодні"
)
def send_today_schedule(message):

```
now = get_kyiv_time()

today = now.strftime(
    "%A"
)

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
```

# ==============================

# РОЗКЛАД НА ЗАВТРА

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "🔮 Завтра"
)
def send_tomorrow_schedule(message):

```
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
```

# ==============================

# РОЗКЛАД НА ТИЖДЕНЬ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "🗓 Розклад на тиждень"
)
def send_week_schedule(message):

```
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

    text += f"📌 *{day_ua}:*\n"

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
```

# ==============================

# ХТО ЧЕРГУЄ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "🧹 Хто чергує завтра?"
)
def random_student(message):

```
chosen = random.choice(
    STUDENTS
)

bot.send_message(
    message.chat.id,
    f"🧹 *Черговий завтра:*\n\n"
    f"👤 {chosen}",
    parse_mode="Markdown"
)
```

# ==============================

# СПИСОК ГРУПИ

# ==============================

@bot.message_handler(
func=lambda message:
message.text == "👥 Список групи"
)
def send_group_list(message):

```
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
```

# ==============================

# ПОШУК ПРЕДМЕТІВ

# ==============================

@bot.message_handler(
func=lambda message:
message.text is not None
)
def search_subject(message):

```
text = message.text.lower().strip()

search_words = {
    "Українська мова та література": [
        "укр",
        "україн",
        "украин",
        "літератур",
        "литератур"
    ],

    "Виховні години та фізичне виховання": [
        "фізра",
        "физра",
        "фізич",
        "физическ",
        "виховн"
    ],

    "Фізика": [
        "фізика",
        "физика"
    ],

    "Конструкційні та електротехнічні матеріали": [
        "матеріал",
        "материал",
        "конструкц",
        "електротех",
        "электротех"
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
        "правознав"
    ],

    "Англійська мова": [
        "англ",
        "англий",
        "англій"
    ],

    "Математика": [
        "матем",
        "матим",
        "матемю",
        "матеша",
        "алгебр"
    ],

    "Біологія і екологія": [
        "біо",
        "био",
        "біолог",
        "биолог",
        "еколог",
        "эколог"
    ]
}

for subject_name, keywords in search_words.items():

    if subject_name not in SUBJECTS:
        continue

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
    "❓ Не знайшов предмет.\n\n"
    "Напиши, наприклад:\n"
    "• укр\n"
    "• матем\n"
    "• англ\n"
    "• фізика\n"
    "• біо"
)
```

# ==============================

# ПЕРЕВІРКА НАГАДУВАНЬ

# ==============================

last_notifications = set()

def check_and_send_notifications():

```
now = get_kyiv_time()

today = now.strftime(
    "%A"
)

day_schedule = SCHEDULE.get(
    today,
    {}
)

for number, subject_name in day_schedule.items():

    call_info = CALLS.get(number)

    if not call_info:
        continue

    start_hour, start_minute = map(
        int,
        call_info["start"].split(":")
    )

    lesson_time = now.replace(
        hour=start_hour,
        minute=start_minute,
        second=0,
        microsecond=0
    )

    notification_time = (
        lesson_time
        - timedelta(minutes=5)
    )

    notification_key = (
        f"{now.date()}_"
        f"{number}_"
        f"{subject_name}"
    )

    if (
        now.hour == notification_time.hour
        and now.minute == notification_time.minute
        and notification_key not in last_notifications
    ):

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

        last_notifications.add(
            notification_key
        )
```

# ==============================

# ЗАПУСК БОТА

# ==============================

if **name** == "**main**":

```
bot.remove_webhook()

print(
    "Бот Е-21 запущений!"
)

last_check_minute = None

while True:

    try:

        now = get_kyiv_time()

        current_minute = (
            now.year,
            now.month,
            now.day,
            now.hour,
            now.minute
        )

        if current_minute != last_check_minute:

            check_and_send_notifications()

            last_check_minute = current_minute

        bot.polling(
            none_stop=False,
            interval=1,
            timeout=20,
            long_polling_timeout=20
        )

    except Exception as error:

        print(
            f"Помилка бота: {error}"
        )
```
