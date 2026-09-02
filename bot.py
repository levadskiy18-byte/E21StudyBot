import os
import datetime
import threading
from flask import Flask
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from data import SUBJECTS, CALLS, SCHEDULE

# Запуск веб-сервера для Render
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Получаем токен из настроек сервера
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Список пользователей, включивших уведомления
subscribed_users = set()

# Перевод дней недели
DAYS_TRANSLATE = {
    "Monday": "Понеділок",
    "Tuesday": "Вівторок",
    "Wednesday": "Середа",
    "Thursday": "Четвер",
    "Friday": "П'ятниця",
    "Saturday": "Субота",
    "Sunday": "Неділя"
}

DAYS_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Главное меню
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("📅 Расписание на сегодня")
    btn2 = types.KeyboardButton("🗓 Расписание на неделю")
    btn3 = types.KeyboardButton("⏰ Расписание звонков")
    btn4 = types.KeyboardButton("📚 Предметы")
    btn5 = types.KeyboardButton("👨‍🏫 Преподаватели")
    btn6 = types.KeyboardButton("🔔 Включить/выключить уведомления")
    markup.row(btn1, btn2)
    markup.row(btn3)
    markup.row(btn4, btn5)
    markup.row(btn6)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        f"Привіт, {message.from_user.first_name}!\n"
        f"Це бот для студентів групи Е-21 🎓\n\n"
        f"Обери потрібний пункт меню нижче:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    text = message.text
    chat_id = message.chat.id

    if text == "📅 Расписание на сегодня":
        today_en = datetime.datetime.now().strftime("%A")
        today_ua = DAYS_TRANSLATE.get(today_en, today_en)
        
        if today_en not in SCHEDULE or not SCHEDULE[today_en]:
            bot.send_message(chat_id, f"📅 **Сьогодні ({today_ua}) пар немає!** 🎉", parse_mode="Markdown")
            return
        
        response = f"📅 **Розклад на сьогодні ({today_ua}):**\n\n"
        for lesson_num, subj_name in SCHEDULE[today_en].items():
            call = CALLS.get(lesson_num, {"start": "", "end": ""})
            response += f"{lesson_num}️⃣ пара ({call['start']} - {call['end']}): **{subj_name}**\n"
        
        bot.send_message(chat_id, response, parse_mode="Markdown")

    elif text == "🗓 Расписание на неделю":
        response = "🗓 **Розклад на тиждень:**\n\n"
        for day in DAYS_ORDER:
            day_ua = DAYS_TRANSLATE.get(day, day)
            response += f"📌 **{day_ua}:**\n"
            if day in SCHEDULE and SCHEDULE[day]:
                for lesson_num, subj_name in SCHEDULE[day].items():
                    call = CALLS.get(lesson_num, {"start": "", "end": ""})
                    response += f"  {lesson_num}️⃣ пара ({call['start']}-{call['end']}): {subj_name}\n"
            else:
                response += "  Пар немає\n"
            response += "\n"
        bot.send_message(chat_id, response, parse_mode="Markdown")

    elif text == "⏰ Расписание звонков":
        response = "⏰ **Розклад дзвінків (пар):**\n\n"
        for num, times in CALLS.items():
            response += f"{num}️⃣ пара: {times['start']} — {times['end']}\n"
        bot.send_message(chat_id, response, parse_mode="Markdown")

    elif text == "📚 Предметы":
        response = "📚 **Список предметів:**\n\n"
        for subj, info in SUBJECTS.items():
            response += f"🔹 **{subj}**\n"
            if info.get("classroom"):
                response += f"  • Classroom: {info['classroom']}\n"
            if info.get("zoom"):
                response += f"  • Zoom: {info['zoom']}\n"
            response += "\n"
        bot.send_message(chat_id, response, parse_mode="Markdown", disable_web_page_preview=True)

    elif text == "👨‍🏫 Преподаватели":
        response = "👨‍🏫 **Викладачі:**\n\n"
        for subj, info in SUBJECTS.items():
            teacher = info.get("teacher", "Не вказано")
            response += f"• **{subj}**: {teacher}\n"
        bot.send_message(chat_id, response, parse_mode="Markdown")

    elif text == "🔔 Включить/выключить уведомления":
        if chat_id in subscribed_users:
            subscribed_users.remove(chat_id)
            bot.send_message(chat_id, "🔕 Ви вимкнули сповіщення про пари.")
        else:
            subscribed_users.add(chat_id)
            bot.send_message(chat_id, "🔔 Ви увімкнули сповіщення! Бот нагадуватиме про пару за 5 хвилин до початку.")

# Проверка времени и отправка уведомлений
def check_and_send_notifications():
    now = datetime.datetime.now()
    today_en = now.strftime("%A")
    current_time = now.strftime("%H:%M")

    if today_en not in SCHEDULE:
        return

    for lesson_num, subj_name in SCHEDULE[today_en].items():
        if lesson_num in CALLS:
            start_str = CALLS[lesson_num]["start"]
            start_dt = datetime.datetime.strptime(start_str, "%H:%M")
            notify_dt = start_dt - datetime.timedelta(minutes=5)
            notify_time_str = notify_dt.strftime("%H:%M")

            if current_time == notify_time_str:
                subj_info = SUBJECTS.get(subj_name, {})
                teacher = subj_info.get("teacher", "Не вказано")
                
                text = (
                    f"🔔 **Через 5 хвилин починається пара!**\n\n"
                    f"📚 **{subj_name}**\n"
                    f"👨‍🏫 **Викладач:** {teacher}"
                )
                
                markup = types.InlineKeyboardMarkup()
                if subj_info.get("zoom"):
                    markup.add(types.InlineKeyboardButton("🎥 Zoom", url=subj_info["zoom"]))
                if subj_info.get("classroom") and subj_info["classroom"].startswith("http"):
                    markup.add(types.InlineKeyboardButton("📚 Google Classroom", url=subj_info["classroom"]))

                for user_id in subscribed_users:
                    try:
                        bot.send_message(user_id, text, reply_markup=markup, parse_mode="Markdown")
                    except Exception:
                        pass

# Запуск фонового планировщика
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_notifications, 'interval', seconds=30)
scheduler.start()

if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    bot.polling(none_stop=True)
