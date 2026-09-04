import os
import json
import threading
from datetime import datetime, date, timedelta

import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

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

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не найден BOT_TOKEN в Environment Variables")

ADMIN_ID = 857901222
GROUP_CHAT_URL = "https://t.me/+GaN9ZTAYn_01ODRi"
DONATE_URL = "https://send.monobank.ua/jar/5r7iFcvzb7"

KYIV = "Europe/Kyiv"

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
scheduler = BackgroundScheduler(timezone=KYIV)
app = Flask(__name__)

USERS_FILE = "users.json"
SUBSCRIBERS_FILE = "subscribers.json"

known_users = set()
subscribed_users = set()
pending_complaints = {}
pending_admin_replies = {}
pending_announcement = set()


def load_ids(filename):
    try:
        if not os.path.exists(filename):
            return set()

        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {int(x) for x in data}

    except Exception:
        return set()


def save_ids(filename, values):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(
            sorted(values),
            f,
            ensure_ascii=False,
            indent=2,
        )


known_users = load_ids(USERS_FILE)
subscribed_users = load_ids(SUBSCRIBERS_FILE)


def remember_user(user_id):
    known_users.add(user_id)
    save_ids(USERS_FILE, known_users)


def set_subscription(user_id, enabled):
    if enabled:
        subscribed_users.add(user_id)
    else:
        subscribed_users.discard(user_id)

    save_ids(SUBSCRIBERS_FILE, subscribed_users)


def main_menu(user_id):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.row("📅 Сьогодні", "🔮 Завтра")
    keyboard.row("🗓 Цей тиждень", "🔮 Наступний тиждень")
    keyboard.row("📚 Предмети", "👨‍🏫 Викладачі")
    keyboard.row("🎥 Zoom", "📝 Google Classroom")
    keyboard.row("⏰ Розклад дзвінків")
    keyboard.row("🧹 Хто чергує завтра?", "👥 Список групи")
    keyboard.row("💬 Чат групи Е-21")
    keyboard.row("🥤 Кинь монету адміну на Кока-Колу")
    keyboard.row("🚨 БОТ НЕ ПРАЦЮЄ!!!")

    if user_id in subscribed_users:
        keyboard.row("🔔 Вимкнути сповіщення")
    else:
        keyboard.row("🔔 Увімкнути сповіщення")

    if user_id == ADMIN_ID:
        keyboard.row("📢 Оголошення")

    return keyboard


def format_date(d):
    weekdays = [
        "Понеділок",
        "Вівторок",
        "Середа",
        "Четвер",
        "П’ятниця",
        "Субота",
        "Неділя",
    ]

    return f"{weekdays[d.weekday()]}, {d.strftime('%d.%m.%Y')}"


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_call_time(date_obj, pair_num):
    """
    Час пар.

    Єдине нестандартне правило:
    ПОНЕДІЛОК — 1 пара починається о 08:45.

    Вівторок, середа, четвер і п'ятниця:
    1 пара починається о 08:00.

    Інші пари беруться з CALLS.
    """

    pair_num = str(pair_num)

    # Тільки понеділок: 1 пара о 08:45
    if date_obj.weekday() == 0 and pair_num == "1":
        return "08:45", "09:35"

    call = CALLS.get(pair_num)

    if not call:
        return None, None

    return call["start"], call["end"]


def get_schedule_for_date(date_obj):
    current_start = parse_date(CURRENT_WEEK_START)
    current_end = parse_date(CURRENT_WEEK_END)

    next_start = parse_date(NEXT_WEEK_START)
    next_end = parse_date(NEXT_WEEK_END)

    weekday_names = {
        0: "Monday",
        1: "Tuesday",
        2: "Wednesday",
        3: "Thursday",
        4: "Friday",
        5: "Saturday",
        6: "Sunday",
    }

    weekday = weekday_names[date_obj.weekday()]

    if current_start <= date_obj <= current_end:
        return CURRENT_SCHEDULE.get(weekday, {})

    if next_start <= date_obj <= next_end:
        return NEXT_SCHEDULE.get(weekday, {})

    return {}


def get_week_data_for_date(date_obj):
    current_start = parse_date(CURRENT_WEEK_START)
    current_end = parse_date(CURRENT_WEEK_END)

    next_start = parse_date(NEXT_WEEK_START)
    next_end = parse_date(NEXT_WEEK_END)

    if current_start <= date_obj <= current_end:
        return CURRENT_SCHEDULE, current_start, current_end

    if next_start <= date_obj <= next_end:
        return NEXT_SCHEDULE, next_start, next_end

    return None, None, None


def get_next_week_data(date_obj):
    current_start = parse_date(CURRENT_WEEK_START)
    current_end = parse_date(CURRENT_WEEK_END)

    next_start = parse_date(NEXT_WEEK_START)
    next_end = parse_date(NEXT_WEEK_END)

    # Поки йде тиждень 31.08–04.09,
    # наступний — 07.09–11.09
    if current_start <= date_obj <= current_end:
        return NEXT_SCHEDULE, next_start, next_end

    # Коли вже настав 07.09–11.09,
    # наступний тиждень ще не завантажений
    if next_start <= date_obj <= next_end:
        return None, None, None

    return None, None, None


def find_subject_info(subject_name):
    if subject_name in SUBJECTS:
        return SUBJECTS[subject_name]

    normalized = str(subject_name).strip().lower()

    for name, info in SUBJECTS.items():
        if name.strip().lower() == normalized:
            return info

    return None


def schedule_text_for_day(date_obj):
    schedule = get_schedule_for_date(date_obj)

    if not schedule:
        return (
            f"📅 *{format_date(date_obj)}*\n\n"
            "Пар цього дня немає або розклад ще не завантажено."
        )

    lines = [
        f"📅 *{format_date(date_obj)}*",
        "",
    ]

    sorted_items = sorted(
        schedule.items(),
        key=lambda item: int(item[0]) if str(item[0]).isdigit() else 999,
    )

    for pair_num, subject in sorted_items:
        start, end = get_call_time(
            date_obj,
            str(pair_num),
        )

        if start and end:
            time_text = f"{start}–{end}"
        else:
            time_text = "час не вказано"

        info = find_subject_info(subject)

        lines.append(
            f"*{pair_num} пара* · {time_text}"
        )
        lines.append(
            f"📚 {subject}"
        )

        if info:
            teacher = info.get("teacher", "")

            if teacher:
                lines.append(
                    f"👨‍🏫 {teacher}"
                )

        lines.append("")

    return "\n".join(lines).rstrip()


def schedule_buttons(date_obj):
    schedule = get_schedule_for_date(date_obj)

    markup = types.InlineKeyboardMarkup()

    sorted_items = sorted(
        schedule.items(),
        key=lambda item: int(item[0]) if str(item[0]).isdigit() else 999,
    )

    for pair_num, subject in sorted_items:
        info = find_subject_info(subject)

        if not info:
            continue

        zoom = info.get("zoom", "")
        classroom = info.get("classroom", "")

        buttons = []

        if zoom:
            buttons.append(
                types.InlineKeyboardButton(
                    "🎥 Zoom",
                    url=zoom,
                )
            )

        if classroom:
            buttons.append(
                types.InlineKeyboardButton(
                    "📝 Classroom",
                    url=classroom,
                )
            )

        if buttons:
            markup.row(*buttons)

    if markup.keyboard:
        return markup

    return None


def send_day_schedule(chat_id, date_obj):
    text = schedule_text_for_day(date_obj)
    markup = schedule_buttons(date_obj)

    if markup:
        bot.send_message(
            chat_id,
            text,
            reply_markup=markup,
        )
    else:
        bot.send_message(
            chat_id,
            text,
        )


def send_week(
    chat_id,
    schedule_data,
    start_date,
    end_date,
    title,
):
    if not schedule_data or not start_date or not end_date:
        bot.send_message(
            chat_id,
            "📭 Розклад на цей тиждень ще не завантажений.",
        )
        return

    bot.send_message(
        chat_id,
        f"🗓 *{title}*\n"
        f"{start_date.strftime('%d.%m.%Y')} — "
        f"{end_date.strftime('%d.%m.%Y')}",
    )

    current = start_date

    while current <= end_date:
        send_day_schedule(
            chat_id,
            current,
        )

        current += timedelta(days=1)


def duty_tomorrow():
    return (
        "🧹 Інформація про чергування "
        "ще не налаштована."
    )


@bot.message_handler(commands=["start"])
def start_handler(message):
    remember_user(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,
        "👋 *Вітаю в боті групи Е-21!*\n\n"
        "Тут можна переглянути розклад, викладачів, "
        "посилання на Zoom та Classroom, отримувати "
        "нагадування про пари та користуватися "
        "іншими функціями.",
        reply_markup=main_menu(
            message.from_user.id
        ),
    )


@bot.message_handler(
    func=lambda message: message.text == "📅 Сьогодні"
)
def today_handler(message):
    remember_user(
        message.from_user.id
    )

    send_day_schedule(
        message.chat.id,
        date.today(),
    )


@bot.message_handler(
    func=lambda message: message.text == "🔮 Завтра"
)
def tomorrow_handler(message):
    remember_user(
        message.from_user.id
    )

    send_day_schedule(
        message.chat.id,
        date.today() + timedelta(days=1),
    )


@bot.message_handler(
    func=lambda message: message.text == "🗓 Цей тиждень"
)
def current_week_handler(message):
    remember_user(
        message.from_user.id
    )

    data, start_date, end_date = get_week_data_for_date(
        date.today()
    )

    if not data:
        bot.send_message(
            message.chat.id,
            "📭 Розклад поточного тижня "
            "ще не завантажений.",
        )
        return

    send_week(
        message.chat.id,
        data,
        start_date,
        end_date,
        "Розклад поточного тижня",
    )


@bot.message_handler(
    func=lambda message: message.text == "🔮 Наступний тиждень"
)
def next_week_handler(message):
    remember_user(
        message.from_user.id
    )

    data, start_date, end_date = get_next_week_data(
        date.today()
    )

    if not data:
        bot.send_message(
            message.chat.id,
            "📭 Розклад наступного тижня "
            "ще не завантажений.",
        )
        return

    send_week(
        message.chat.id,
        data,
        start_date,
        end_date,
        "Розклад наступного тижня",
    )


@bot.message_handler(
    func=lambda message: message.text == "⏰ Розклад дзвінків"
)
def calls_handler(message):
    remember_user(
        message.from_user.id
    )

    lines = [
        "⏰ *Розклад дзвінків*",
        "",
        "*1 пара:* 08:00–09:35",
        "ℹ️ У понеділок 1-а пара починається о 08:45.",
        "",
    ]

    for pair_num, call in CALLS.items():
        if str(pair_num) == "1":
            continue

        lines.append(
            f"*{pair_num} пара:* "
            f"{call['start']}–{call['end']}"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines),
    )


@bot.message_handler(
    func=lambda message: message.text == "📚 Предмети"
)
def subjects_handler(message):
    remember_user(
        message.from_user.id
    )

    if not SUBJECTS:
        bot.send_message(
            message.chat.id,
            "📭 Предмети ще не налаштовані.",
        )
        return

    lines = [
        "📚 *Предмети:*",
        "",
    ]

    for name, info in SUBJECTS.items():
        teacher = info.get(
            "teacher",
            "Не вказано",
        )

        lines.append(
            f"• *{name}* — {teacher}"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines),
    )


@bot.message_handler(
    func=lambda message: message.text == "👨‍🏫 Викладачі"
)
def teachers_handler(message):
    remember_user(
        message.from_user.id
    )

    lines = [
        "👨‍🏫 *Викладачі:*",
        "",
    ]

    for subject, info in SUBJECTS.items():
        teacher = info.get(
            "teacher",
            "Не вказано",
        )

        lines.append(
            f"📚 {subject}"
        )
        lines.append(
            f"👨‍🏫 {teacher}"
        )
        lines.append("")

    bot.send_message(
        message.chat.id,
        "\n".join(lines).rstrip(),
    )


@bot.message_handler(
    func=lambda message: message.text == "🎥 Zoom"
)
def zoom_handler(message):
    remember_user(
        message.from_user.id
    )

    markup = types.InlineKeyboardMarkup()

    for subject, info in SUBJECTS.items():
        zoom = info.get("zoom", "")

        if zoom:
            markup.add(
                types.InlineKeyboardButton(
                    subject,
                    url=zoom,
                )
            )

    if not markup.keyboard:
        bot.send_message(
            message.chat.id,
            "📭 Посилання Zoom ще не додані.",
        )
        return

    bot.send_message(
        message.chat.id,
        "🎥 *Zoom*\n\n"
        "Обери потрібний предмет:",
        reply_markup=markup,
    )


@bot.message_handler(
    func=lambda message: message.text == "📝 Google Classroom"
)
def classroom_handler(message):
    remember_user(
        message.from_user.id
    )

    markup = types.InlineKeyboardMarkup()

    for subject, info in SUBJECTS.items():
        classroom = info.get(
            "classroom",
            "",
        )

        if classroom:
            markup.add(
                types.InlineKeyboardButton(
                    subject,
                    url=classroom,
                )
            )

    if not markup.keyboard:
        bot.send_message(
            message.chat.id,
            "📭 Посилання Google Classroom "
            "ще не додані.",
        )
        return

    bot.send_message(
        message.chat.id,
        "📝 *Google Classroom*\n\n"
        "Обери потрібний предмет:",
        reply_markup=markup,
    )


@bot.message_handler(
    func=lambda message: message.text == "👥 Список групи"
)
def group_list_handler(message):
    remember_user(
        message.from_user.id
    )

    try:
        from data import STUDENTS
    except ImportError:
        STUDENTS = []

    if not STUDENTS:
        bot.send_message(
            message.chat.id,
            "📭 Список групи ще не доданий "
            "у data.py.",
        )
        return

    lines = [
        "👥 *Група Е-21*",
        "",
    ]

    for index, student in enumerate(
        STUDENTS,
        start=1,
    ):
        lines.append(
            f"{index}. {student}"
        )

    bot.send_message(
        message.chat.id,
        "\n".join(lines),
    )


@bot.message_handler(
    func=lambda message: message.text == "💬 Чат групи Е-21"
)
def group_chat_handler(message):
    remember_user(
        message.from_user.id
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "💬 Відкрити чат групи",
            url=GROUP_CHAT_URL,
        )
    )

    bot.send_message(
        message.chat.id,
        "💬 *Чат групи Е-21*",
        reply_markup=markup,
    )


@bot.message_handler(
    func=lambda message: message.text
    == "🥤 Кинь монету адміну на Кока-Колу"
)
def donate_handler(message):
    remember_user(
        message.from_user.id
    )

    markup = types.InlineKeyboardMarkup()

    markup.add(
        types.InlineKeyboardButton(
            "🥤 Закинути на Кока-Колу",
            url=DONATE_URL,
        )
    )

    bot.send_message(
        message.chat.id,
        "🥤 Якщо хочеш пригостити "
        "адміна Кока-Колою 😎",
        reply_markup=markup,
    )


@bot.message_handler(
    func=lambda message: message.text
    == "🧹 Хто чергує завтра?"
)
def duty_handler(message):
    remember_user(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,
        duty_tomorrow(),
    )


@bot.message_handler(
    func=lambda message: message.text
    in [
        "🔔 Увімкнути сповіщення",
        "🔔 Вимкнути сповіщення",
    ]
)
def notifications_handler(message):
    remember_user(
        message.from_user.id
    )

    user_id = message.from_user.id

    if user_id in subscribed_users:
        set_subscription(
            user_id,
            False,
        )

        text = (
            "🔕 Сповіщення вимкнено."
        )

    else:
        set_subscription(
            user_id,
            True,
        )

        text = (
            "🔔 Сповіщення увімкнено!\n\n"
            "Я надсилатиму нагадування "
            "за 10 хвилин до пари та "
            "повідомлення в момент її початку."
        )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu(user_id),
    )


@bot.message_handler(
    func=lambda message: message.text
    == "🚨 БОТ НЕ ПРАЦЮЄ!!!"
)
def complaint_start_handler(message):
    remember_user(
        message.from_user.id
    )

    pending_complaints[
        message.from_user.id
    ] = True

    bot.send_message(
        message.chat.id,
        "🚨 Опиши проблему одним повідомленням.\n"
        "Я передам її адміну.",
    )


@bot.message_handler(
    func=lambda message:
        message.from_user.id == ADMIN_ID
        and message.text == "📢 Оголошення"
)
def announcement_start_handler(message):
    remember_user(
        message.from_user.id
    )

    pending_announcement.add(
        message.from_user.id
    )

    bot.send_message(
        message.chat.id,
        "📢 Напиши текст оголошення "
        "одним повідомленням.\n"
        "Після цього я розішлю його "
        "користувачам бота.",
    )


@bot.message_handler(
    func=lambda message:
        message.from_user.id == ADMIN_ID
        and message.from_user.id in pending_admin_replies
)
def admin_reply_handler(message):
    user_id = pending_admin_replies.pop(
        message.from_user.id,
        None,
    )

    if not user_id:
        return

    try:
        bot.send_message(
            user_id,
            "✉️ *Відповідь адміністратора:*\n\n"
            + message.text,
        )

        bot.send_message(
            message.chat.id,
            "✅ Відповідь користувачу відправлена.",
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            "❌ Не вдалося відправити "
            f"відповідь: `{e}`",
        )


@bot.message_handler(
    func=lambda message:
        message.from_user.id in pending_complaints
)
def complaint_message_handler(message):
    user_id = message.from_user.id

    pending_complaints.pop(
        user_id,
        None,
    )

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "немає username"
    )

    full_name = " ".join(
        x
        for x in [
            message.from_user.first_name,
            message.from_user.last_name,
        ]
        if x
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
            callback_data=f"reply:{user_id}",
        )
    )

    try:
        bot.send_message(
            ADMIN_ID,
            text,
            reply_markup=markup,
        )

        bot.send_message(
            message.chat.id,
            "✅ Проблему передано адміну. "
            "Він отримає твоє повідомлення.",
            reply_markup=main_menu(user_id),
        )

    except Exception as e:
        bot.send_message(
            message.chat.id,
            "❌ Не вдалося передати "
            f"проблему адміну: `{e}`",
        )


@bot.message_handler(
    func=lambda message:
        message.from_user.id == ADMIN_ID
        and message.from_user.id in pending_announcement
)
def announcement_message_handler(message):
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

    announcement = (
        "📢 *Оголошення*\n\n"
        + message.text
    )

    sent = 0
    failed = 0

    for user_id in recipients:
        try:
            bot.send_message(
                user_id,
                announcement,
            )

            sent += 1

        except Exception:
            failed += 1

    bot.send_message(
        message.chat.id,
        f"✅ Оголошення розіслано.\n\n"
        f"📨 Надіслано: {sent}\n"
        f"❌ Не доставлено: {failed}",
    )


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("reply:")
)
def reply_button_handler(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(
            call.id,
            "Немає доступу.",
        )
        return

    try:
        user_id = int(
            call.data.split(":", 1)[1]
        )

    except (ValueError, IndexError):
        bot.answer_callback_query(
            call.id,
            "Помилковий ID користувача.",
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
        f"✉️ Напиши відповідь "
        f"користувачу `{user_id}` "
        "одним повідомленням.",
    )


def send_pair_notification(
    pair_num,
    subject,
    date_obj,
    start_time,
    kind,
):
    info = find_subject_info(
        subject
    )

    for user_id in list(
        subscribed_users
    ):
        try:
            if kind == "before":
                text = (
                    "🔔 *Через 10 хвилин "
                    "починається пара!*\n\n"
                    f"🔢 Пара: *{pair_num}*\n"
                    f"📚 {subject}\n"
                    f"🕐 Початок: *{start_time}*"
                )
            else:
                text = (
                    "▶️ *Пара почалася!*\n\n"
                    f"🔢 Пара: *{pair_num}*\n"
                    f"📚 {subject}\n"
                    f"🕐 Початок: *{start_time}*"
                )

            markup = types.InlineKeyboardMarkup()

            if info:
                zoom = info.get(
                    "zoom",
                    "",
                )

                classroom = info.get(
                    "classroom",
                    "",
                )

                buttons = []

                if zoom:
                    buttons.append(
                        types.InlineKeyboardButton(
                            "🎥 Zoom",
                            url=zoom,
                        )
                    )

                if classroom:
                    buttons.append(
                        types.InlineKeyboardButton(
                            "📝 Classroom",
                            url=classroom,
                        )
                    )

                if buttons:
                    markup.row(
                        *buttons
                    )

            if markup.keyboard:
                bot.send_message(
                    user_id,
                    text,
                    reply_markup=markup,
                )
            else:
                bot.send_message(
                    user_id,
                    text,
                )

        except Exception:
            set_subscription(
                user_id,
                False,
            )


def notification_job():
    now = datetime.now()
    current_date = now.date()

    schedule = get_schedule_for_date(
        current_date
    )

    if not schedule:
        return

    for pair_num, subject in schedule.items():
        start_time, end_time = get_call_time(
            current_date,
            str(pair_num),
        )

        if not start_time:
            continue

        try:
            hour, minute = map(
                int,
                start_time.split(":"),
            )

        except ValueError:
            continue

        start_dt = now.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )

        diff_seconds = (
            start_dt - now
        ).total_seconds()

        # За 10 хвилин до пари
        if 570 <= diff_seconds <= 630:
            send_pair_notification(
                pair_num,
                subject,
                current_date,
                start_time,
                "before",
            )

        # У момент початку пари
        elif -30 <= diff_seconds <= 30:
            send_pair_notification(
                pair_num,
                subject,
                current_date,
                start_time,
                "start",
            )


@bot.message_handler(
    func=lambda message: True
)
def fallback_handler(message):
    remember_user(
        message.from_user.id
    )

    text = (
        message.text or ""
    ).strip()

    if not text:
        return

    results = []

    for subject, info in SUBJECTS.items():
        if text.lower() in subject.lower():
            results.append(
                (subject, info)
            )

    if results:
        subject, info = results[0]

        response = (
            f"📚 *{subject}*\n\n"
            f"👨‍🏫 {info.get('teacher', 'Не вказано')}"
        )

        markup = types.InlineKeyboardMarkup()

        zoom = info.get(
            "zoom",
            "",
        )

        classroom = info.get(
            "classroom",
            "",
        )

        if zoom:
            markup.add(
                types.InlineKeyboardButton(
                    "🎥 Zoom",
                    url=zoom,
                )
            )

        if classroom:
            markup.add(
                types.InlineKeyboardButton(
                    "📝 Google Classroom",
                    url=classroom,
                )
            )

        if markup.keyboard:
            bot.send_message(
                message.chat.id,
                response,
                reply_markup=markup,
            )
        else:
            bot.send_message(
                message.chat.id,
                response,
            )

        return

    bot.send_message(
        message.chat.id,
        "🤔 Не зовсім зрозумів запит.\n"
        "Скористайся кнопками меню.",
        reply_markup=main_menu(
            message.from_user.id
        ),
    )


@app.route("/")
def index():
    return "E21StudyBot is running!"


@app.route("/health")
def health():
    return "OK"


def run_web():
    port = int(
        os.getenv(
            "PORT",
            "10000",
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
    )


def start_bot():
    while True:
        try:
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=30,
                skip_pending=True,
            )

        except Exception as e:
            print(
                f"Polling error: {e}"
            )


if __name__ == "__main__":
    scheduler.add_job(
        notification_job,
        "interval",
        seconds=30,
        id="pair_notifications",
        replace_existing=True,
        max_instances=1,
    )

    scheduler.start()

    threading.Thread(
        target=start_bot,
        daemon=True,
    ).start()

    run_web()
```
