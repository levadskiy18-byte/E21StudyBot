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
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

SUBSCRIBERS_FILE = "subscribers.json"

STUDENTS = [
    "Болтенков Кирило", "Будко Микола", "Буцьківський Антон", "Веклич Олександр",
    "Воротніков Микола", "Гунбін Дмитро", "Дрінь Дмитро", "Желєзняк Владислав",
    "Задорожний Іван", "Кабанець Олексій", "Кищак Михайло", "Козаков Платон",
    "Конова Альбіна", "Корінєв Андрій", "Кравцов Олександр", "Кривозуб Олександр",
    "Лазаренко Віталій", "Лахмієнко Микола", "Левадний Дмитро", "Левадський Олександр",
    "Літовщик Владислав", "Ломака Артем", "Макеєв Максим", "Мухортов Антон",
    "Остапенко Максим", "Перепелиця Артур", "Плахотній Станіслав", "Порошин Єгор",
    "Репринцев Владислав", "Семак Іван", "Скидан Юрій", "Суржко Валерій",
    "Сябро Лев", "Танцюра Даріна", "Тертишник Василь", "Тюпа Євген"
]

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
    "англ": "Англійська мова",
    "английский": "Англійська мова",
    "био": "Біологія і Екологія",
    "биология": "Біологія і Екологія",
    "право": "Правознавство",
    "правоведение": "Правознавство",
    "история": "Історія 11 класс",
    "історія": "Історія 11 класс",
    "материалы": "Конструкційні та електротехнічні матеріали",
    "матеріали": "Конструкційні та електротехнічні матеріали",
    "кэм": "Конструкційні та електротехнічні матеріали"
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

def get_subject_info(subject_name):
    data = SUBJECTS.get(subject_name)
    if not data:
        return None, None
    text = f"📚 *{subject_name}*\n👨‍🏫 Выкладач: {data['teacher']}"
    markup = types.InlineKeyboardMarkup()
    if data.get("zoom"):
        markup.add(types.InlineKeyboardButton("🎥 Zoom", url=data["zoom"]))
    if data.get("classroom"):
        markup.add(types.InlineKeyboardButton("📚 Google Classroom", url=data["classroom"]))
    return text, markup

def get_kyiv_time():
    kyiv_tz = timezone(timedelta(hours=3))
    return datetime.now(kyiv_tz)

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
    markup.row("📅 Сегодня", "🔮 Завтра", "🗓 На неделю")
    markup.row("📝 Домашка (Classroom)", "⏰ Звонки")
    markup.row("🧹 Кто дежурит завтра?", "👥 Список группы")
    markup.row("📚 Предметы", "👨‍🏫 Преподаватели", "🔔 Уведомления")
    bot.send_message(
        message.chat.id,
        "Привет! Я бот группы Е-21.\nИспользуй меню ниже или напиши название предмета!",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: message.text == "🔔 Уведомления")
def toggle_notifications(message):
    user_id = message.chat.id
    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        save_subscribers(subscribed_users)
        bot.send_message(user_id, "🔕 Уведомления выключены.")
    else:
        subscribed_users.add(user_id)
        save_subscribers(subscribed_users)
        bot.send_message(user_id, "🔔 Уведомления включены!")

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["звонки", "дзвінки", "расписание звонков", "розклад дзвінків"]))
def send_calls(message):
    text = "⏰ *Розклад дзвінків:*\n\n"
    for num, times in CALLS.items():
        text += f"{num} пара: {times['start']} - {times['end']}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["дежур", "чергур", "отвеча", "відповіда", "кто", "хто"]))
def random_student(message):
    # Анимация: сначала отправляем сообщение о рандоме
    temp_msg = bot.send_message(message.chat.id, "🎲 *Выбираем дежурного на завтра...* 🎰", parse_mode="Markdown")
    time.sleep(2)
    
    chosen = random.choice(STUDENTS)
    # Редактируем сообщение, выводя итоговый результат
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=temp_msg.message_id,
        text=f"🧹 *Дежурный на завтра:* {chosen}! 🧽✨",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["список", "групп", "групи"]))
def send_group_list(message):
    text = "👥 *Cписок группы Е-21 (36 студентов):*\n\n"
    for idx, student in enumerate(STUDENTS, 1):
        text += f"{idx}. {student}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["домашка", "classroom", "классрум"]))
def send_homework_links(message):
    markup = types.InlineKeyboardMarkup()
    for name, data in SUBJECTS.items():
        if data.get("classroom"):
            markup.add(types.InlineKeyboardButton(f"📖 {name}", url=data["classroom"]))
    bot.send_message(message.chat.id, "📝 *Выбери предмет, чтобы открыть Google Classroom:*", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "📚 Предметы")
def send_subjects(message):
    markup = types.InlineKeyboardMarkup()
    for name in SUBJECTS.keys():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"sub_{name}"))
    bot.send_message(message.chat.id, "Обери предмет:", reply_markup=markup)

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["преподавател", "викладач", "учител", "вчител"]))
def send_teachers(message):
    text = "👨‍🏫 *Список викладачів:*\n\n"
    for name, data in SUBJECTS.items():
        text += f"• *{name}*: {data['teacher']}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["сегодня", "сьогодні"]))
def send_today_schedule(message):
    now = get_kyiv_time()
    today = now.strftime("%A")
    day_ua = DAYS_UA.get(today, today)
    
    day_schedule = SCHEDULE.get(today, {})
    if not day_schedule:
        bot.send_message(message.chat.id, f"📅 *Расписание на сегодня ({day_ua}):*\nСьогодні пар немає! 🎉", parse_mode="Markdown")
        return
    
    text = f"📅 *Расписание на сегодня ({day_ua}):*\n\n"
    for num, subject in day_schedule.items():
        time_info = CALLS.get(num, {})
        time_str = f"({time_info.get('start')} - {time_info.get('end')})" if time_info else ""
        text += f"*{num}. {subject}* {time_str}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["завтра"]))
def send_tomorrow_schedule(message):
    tomorrow_dt = get_kyiv_time() + timedelta(days=1)
    tomorrow = tomorrow_dt.strftime("%A")
    day_ua = DAYS_UA.get(tomorrow, tomorrow)
    
    day_schedule = SCHEDULE.get(tomorrow, {})
    if not day_schedule:
        bot.send_message(message.chat.id, f"🔮 *Расписание на завтра ({day_ua}):*\nЗавтра пар немає! 🎉", parse_mode="Markdown")
        return
    
    text = f"🔮 *Расписание на завтра ({day_ua}):*\n\n"
    for num, subject in day_schedule.items():
        time_info = CALLS.get(num, {})
        time_str = f"({time_info.get('start')} - {time_info.get('end')})" if time_info else ""
        text += f"*{num}. {subject}* {time_str}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: any(x in message.text.lower() for x in ["неделю", "тиждень"]))
def send_week_schedule(message):
    text = "🗓 *Розклад на тиждень:*\n\n"
    for day_eng, day_ua in DAYS_UA.items():
        if day_eng in SCHEDULE and SCHEDULE[day_eng]:
            text += f"📌 *{day_ua}:*\n"
            for num, subject in SCHEDULE[day_eng].items():
                text += f"  {num}. {subject}\n"
            text += "\n"
    if text == "🗓 *Розклад на тиждень:*\n\n":
        text += "Розклад порожній."
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("sub_"))
def callback_subject(call):
    sub_name = call.data.replace("sub_", "")
    info_text, markup = get_subject_info(sub_name)
    if info_text:
        bot.send_message(call.message.chat.id, info_text, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_custom_text(message):
    clean_text = message.text.strip().lower()
    
    if clean_text in ["сколько", "пара", "перерыв"]:
        now = get_kyiv_time()
        now_minutes = now.hour * 60 + now.minute
        for num, times in CALLS.items():
            sh, sm = map(int, times["start"].split(":"))
            eh, em = map(int, times["end"].split(":"))
            start_m = sh * 60 + sm
            end_m = eh * 60 + em
            if start_m <= now_minutes < end_m:
                rem = end_m - now_minutes
                bot.send_message(message.chat.id, f"⏳ Сейчас идёт *{num} пара*. До конца осталось *{rem} мин*.", parse_mode="Markdown")
                return
        bot.send_message(message.chat.id, "☕️ Сейчас нет пар или идет перерыв!", parse_mode="Markdown")
        return

    matched = ALIASES.get(clean_text)
    if not matched:
        for key, full in ALIASES.items():
            if key in clean_text:
                matched = full
                break
                
    if matched:
        info_text, markup = get_subject_info(matched)
        if info_text:
            bot.send_message(message.chat.id, info_text, parse_mode="Markdown", reply_markup=markup)
            return

    bot.send_message(message.chat.id, "Я не понял запрос. Напиши предмет (например: 'укр', 'матем') или используй меню.")

def check_and_send_notifications():
    now = get_kyiv_time()
    today = now.strftime("%A")
    current_time = now.strftime("%H:%M")

    day_schedule = SCHEDULE.get(today, {})
    for num, subject_name in day_schedule.items():
        call_info = CALLS.get(num)
        if call_info and call_info["start"] == current_time:
            info_text, markup = get_subject_info(subject_name)
            if info_text:
                msg = f"🔔 *Пара начинается!*\n\n{info_text}"
                for user_id in list(subscribed_users):
                    try:
                        bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=markup)
                    except Exception:
                        pass

scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_notifications, "interval", minutes=1)
scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
