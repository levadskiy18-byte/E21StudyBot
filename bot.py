import os
import json
import random
import time
from datetime import datetime, timezone, timedelta

import telebot
from telebot import types
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler

from data import CALLS, SUBJECTS, SCHEDULE

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
raise ValueError("BOT_TOKEN не знайдено!")

bot = telebot.TeleBot(TOKEN)
app = Flask(**name**)

SUBSCRIBERS_FILE = "subscribers.json"

STUDENTS = [
"Болтенков Кирило", "Будко Микола", "Буцьківський Антон",
"Веклич Олександр", "Воротніков Микола", "Гунбін Дмитро",
"Дрінь Дмитро", "Желєзняк Владислав", "Задорожний Іван",
"Кабанець Олексій", "Кищак Михайло", "Козаков Платон",
"Конова Альбіна", "Корінєв Андрій", "Кравцов Олександр",
"Кривозуб Олександр", "Лазаренко Віталій", "Лахмієнко Микола",
"Левадний Дмитро", "Левадський Олександр", "Літовщик Владислав",
"Ломака Артем", "Макеєв Максим", "Мухортов Антон",
"Остапенко Максим", "Перепелиця Артур", "Плахотній Станіслав",
"Порошин Єгор", "Репринцев Владислав", "Семак Іван",
"Скидан Юрій", "Суржко Валерій", "Сябро Лев",
"Танцюра Даріна", "Тертишник Василь", "Тюпа Євген"
]

def load_subscribers():
if os.path.exists(SUBSCRIBERS_FILE):
try:
with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
return set(json.load(f))
except Exception:
return set()
return set()

def save_subscribers(subs):
try:
with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
json.dump(list(subs), f)
except Exception as e:
print(f"Помилка збереження підписників: {e}")

subscribed_users = load_subscribers()

ALIASES = {
"укр": "Укр. Мова",
"українська": "Укр. Мова",
"мова": "Укр. Мова",
"література": "Укр. Літ",

```
"фізкультура": "Фізвиховання",
"физкультура": "Фізвиховання",
"фізра": "Фізвиховання",
"виховна": "Виховна",

"фізика": "Фізика",
"физика": "Фізика",

"математика": "Математика",
"матем": "Математика",

"англійська": "Ін. мова 12а/преп",
"англійська мова": "Ін. мова 12а/преп",
"англ": "Ін. мова 12а/преп",

"біологія": "Біологія",
"биология": "Біологія",

"правознавство": "Правознавство",
"право": "Правознавство",

"матеріали": "Конструкційні матеріали",
"материалы": "Конструкційні матеріали"
```

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

def get_kyiv_time():
kyiv_tz = timezone(timedelta(hours=3))
return datetime.now(kyiv_tz)

def get_main_keyboard():
markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

```
markup.row("📅 Сьогодні", "🔮 Завтра")
markup.row("🗓 Розклад на тиждень")
markup.row("📚 Предмети", "👨‍🏫 Викладачі")
markup.row("🎥 Zoom", "📝 Google Classroom")
markup.row("⏰ Розклад дзвінків")
markup.row("🧹 Хто чергує завтра?", "👥 Список групи")
markup.row("🔔 Увімкнути/вимкнути сповіщення")

return markup
```

def get_subject_info(subject_name):
data = SUBJECTS.get(subject_name)

```
if not data:
    return None, None

teacher = data.get("teacher", "Не вказано")

text = (
    f"📚 *{subject_name}*\n"
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

classroom = data.get("classroom", "")

if classroom.startswith("http"):
    markup.add(
        types.InlineKeyboardButton(
            "📚 Google Classroom",
            url=classroom
        )
    )

return text, markup
```

@app.route("/")
def index():
return "Бот групи Е-21 працює!", 200

@app.route("/" + TOKEN, methods=["POST"])
def webhook():
json_str = request.get_data().decode("UTF-8")
update = telebot.types.Update.de_json(json_str)

```
bot.process_new_updates([update])

return "OK", 200
```

@bot.message_handler(commands=["start"])
def send_welcome(message):

```
bot.send_message(
    message.chat.id,
    "🎓 Вітаю! Це бот групи *Е-21*.\n\n"
    "Тут ти можеш переглянути розклад, предмети, викладачів, "
    "посилання на Zoom та Google Classroom.\n\n"
    "Обери потрібний пункт у меню 👇",
    parse_mode="Markdown",
    reply_markup=get_main_keyboard()
)
```

@bot.message_handler(
func=lambda message: message.text == "🔔 Увімкнути/вимкнути сповіщення"
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
        "Бот надсилатиме нагадування за 5 хвилин до початку пари."
    )
```

@bot.message_handler(
func=lambda message: message.text == "⏰ Розклад дзвінків"
)
def send_calls(message):

```
text = "⏰ *Розклад дзвінків:*\n\n"

for num, times in CALLS.items():
    text += (
        f"{num} пара: "
        f"{times['start']} — {times['end']}\n"
    )

bot.send_message(
    message.chat.id,
    text,
    parse_mode="Markdown"
)
```

@bot.message_handler(
func=lambda message: message.text == "📚 Предмети"
)
def send_subjects(message):

```
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
```

@bot.message_handler(
func=lambda message: message.text == "👨‍🏫 Викладачі"
)
def send_teachers(message):

```
text = "👨‍🏫 *Список викладачів:*\n\n"

for name, data in SUBJECTS.items():

    teacher = data.get(
        "teacher",
        "Не вказано"
    )

    text += f"• *{name}*: {teacher}\n"

bot.send_message(
    message.chat.id,
    text,
    parse_mode="Markdown"
)
```

@bot.message_handler(
func=lambda message: message.text == "🎥 Zoom"
)
def send_zoom_links(message):

```
markup = types.InlineKeyboardMarkup()

count = 0

for name, data in SUBJECTS.items():

    zoom = data.get("zoom", "")

    if zoom:

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
```

@bot.message_handler(
func=lambda message: message.text == "📝 Google Classroom"
)
def send_classroom_links(message):

```
markup = types.InlineKeyboardMarkup()

count = 0

for name, data in SUBJECTS.items():

    classroom = data.get("classroom", "")

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
```

@bot.message_handler(
func=lambda message: message.text == "📅 Сьогодні"
)
def send_today_schedule(message):

```
now = get_kyiv_time()

today = now.strftime("%A")

day_ua = DAYS_UA.get(today, today)

day_schedule = SCHEDULE.get(today, {})

if not day_schedule:

    bot.send_message(
        message.chat.id,
        f"📅 *Розклад на сьогодні ({day_ua}):*\n\n"
        "Сьогодні пар немає! 🎉",
        parse_mode="Markdown"
    )

    return

text = f"📅 *Розклад на сьогодні ({day_ua}):*\n\n"

for num, subject in day_schedule.items():

    time_info = CALLS.get(num, {})

    start = time_info.get("start", "")
    end = time_info.get("end", "")

    text += (
        f"*{num} пара:* {subject}\n"
        f"🕒 {start} — {end}\n\n"
    )

bot.send_message(
    message.chat.id,
    text,
    parse_mode="Markdown"
)
```

@bot.message_handler(
func=lambda message: message.text == "🔮 Завтра"
)
def send_tomorrow_schedule(message):

```
tomorrow_dt = get_kyiv_time() + timedelta(days=1)

tomorrow = tomorrow_dt.strftime("%A")

day_ua = DAYS_UA.get(tomorrow, tomorrow)

day_schedule = SCHEDULE.get(tomorrow, {})

if not day_schedule:

    bot.send_message(
        message.chat.id,
        f"🔮 *Розклад на завтра ({day_ua}):*\n\n"
        "Завтра пар немає! 🎉",
        parse_mode="Markdown"
    )

    return

text = f"🔮 *Розклад на завтра ({day_ua}):*\n\n"

for num, subject in day_schedule.items():

    time_info = CALLS.get(num, {})

    start = time_info.get("start", "")
    end = time_info.get("end", "")

    text += (
        f"*{num} пара:* {subject}\n"
        f"🕒 {start} — {end}\n\n"
    )

bot.send_message(
    message.chat.id,
    text,
    parse_mode="Markdown"
)
```

@bot.message_handler(
func=lambda message: message.text == "🗓 Розклад на тиждень"
)
def send_week_schedule(message):

```
text = "🗓 *Розклад на тиждень:*\n\n"

for day_eng in [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday"
]:

    day_ua = DAYS_UA[day_eng]

    day_schedule = SCHEDULE.get(
        day_eng,
        {}
    )

    text += f"📌 *{day_ua}:*\n"

    if day_schedule:

        for num, subject in day_schedule.items():

            time_info = CALLS.get(num, {})

            text += (
                f"{num} пара "
                f"({time_info.get('start', '')}): "
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

@bot.callback_query_handler(
func=lambda call: call.data.startswith("sub_")
)
def callback_subject(call):

```
sub_name = call.data.replace(
    "sub_",
    ""
)

info_text, markup = get_subject_info(
    sub_name
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

@bot.message_handler(
func=lambda message: message.text == "🧹 Хто чергує завтра?"
)
def random_student(message):

```
temp_msg = bot.send_message(
    message.chat.id,
    "🎲 *Обираємо чергового...*",
    parse_mode="Markdown"
)

time.sleep(2)

chosen = random.choice(
    STUDENTS
)

bot.edit_message_text(
    f"🧹 *Черговий:* {chosen}! 🧽",
    message.chat.id,
    temp_msg.message_id,
    parse_mode="Markdown"
)
```

@bot.message_handler(
func=lambda message: message.text == "👥 Список групи"
)
def send_group_list(message):

```
text = (
    "👥 *Список групи Е-21:*\n\n"
)

for idx, student in enumerate(
    STUDENTS,
    1
):

    text += f"{idx}. {student}\n"

bot.send_message(
    message.chat.id,
    text,
    parse_mode="Markdown"
)
```

def check_and_send_notifications():

```
now = get_kyiv_time()

today = now.strftime("%A")

current_time = now.strftime(
    "%H:%M"
)

day_schedule = SCHEDULE.get(
    today,
    {}
)

for num, subject_name in day_schedule.items():

    call_info = CALLS.get(
        num
    )

    if not call_info:
        continue

    start_time = datetime.strptime(
        call_info["start"],
        "%H:%M"
    )

    notify_time = (
        start_time -
        timedelta(minutes=5)
    ).strftime("%H:%M")

    if current_time == notify_time:

        info_text, markup = get_subject_info(
            subject_name
        )

        if info_text:

            msg = (
                "🔔 *Через 5 хвилин починається пара!*\n\n"
                f"{info_text}"
            )

            for user_id in list(
                subscribed_users
            ):

                try:

                    bot.send_message(
                        user_id,
                        msg,
                        parse_mode="Markdown",
                        reply_markup=markup
                    )

                except Exception as e:

                    print(
                        f"Не вдалося надіслати повідомлення "
                        f"{user_id}: {e}"
                    )
```

scheduler = BackgroundScheduler()

scheduler.add_job(
check_and_send_notifications,
"interval",
minutes=1
)

scheduler.start()

if **name** == "**main**":

```
port = int(
    os.environ.get(
        "PORT",
        5000
    )
)

app.run(
    host="0.0.0.0",
    port=port
)
```
