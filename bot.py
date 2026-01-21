import json
import re
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

logging.basicConfig(level=logging.INFO)

DATA_FILE = "data.json"

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN = config["token"]
ADMINS = config["admins"]

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def default_data():
    return {
        "active": False,
        "list": [],
        "statuses": {},
        "submitted_users": [],
        "admin_state": None,
        "list_message_id": None,
        "list_chat_id": None
    }

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        data = default_data()
        save_data(data)
        return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_admin(uid):
    return uid in ADMINS

def render_list(data, final=False):
    lines = []
    for i, item in enumerate(data["list"], 1):
        status = data["statuses"].get(str(i))
        icon = ""
        if status == "ready":
            icon = "✅"
        elif status == "off":
            icon = "{Выходной}"
        elif status == "fail" or (final and not status):
            icon = "❌"
        lines.append(f"{icon} {i}. {item}".strip())
    return "\n\n".join(lines)

async def update_list_message(data):
    if not data["list_message_id"]:
        return
    await bot.edit_message_text(
        chat_id=data["list_chat_id"],
        message_id=data["list_message_id"],
        text=render_list(data)
    )

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📋 Показать список")],
        [KeyboardButton(text="📤 Завершить поток")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Админ панель активна.", reply_markup=admin_kb)
    else:
        await message.answer(
            "Отправляй отчёт вот пример для сдачи отчетов:\n"
            "Готово 12\n"
            "или\n"
            "Выходной 12"
        )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Пример отчёта:\n"
        "Готово 5\n"
        "Выходной 7\n\n"
        "Если нет активного потока, бот сообщит об этом."
    )

@dp.message(F.from_user.id.in_(ADMINS))
async def admin_handler(message: Message):
    data = load_data()
    text = message.text.strip()

    if text == "📋 Показать список":
        if not data["list"]:
            await message.answer("Сейчас нет активного списка.")
        else:
            await message.answer(render_list(data))
        return

    if text == "📤 Завершить поток":
        data["active"] = False
        for i in range(1, len(data["list"]) + 1):
            if str(i) not in data["statuses"]:
                data["statuses"][str(i)] = "fail"
        save_data(data)
        await update_list_message(data)
        await message.answer("Итоговый результат:\n\n" + render_list(data, final=True))
        return

    items = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+\.\s*", "", line)
        items.append(line)

    if not items:
        return

    data = default_data()
    data["active"] = True
    data["list"] = items
    save_data(data)

    msg = await message.answer(render_list(data))
    data["list_message_id"] = msg.message_id
    data["list_chat_id"] = msg.chat.id
    save_data(data)

@dp.message()
async def user_handler(message: Message):
    data = load_data()
    text = message.text.lower()
    uid = message.from_user.id

    if not data["active"]:
        await message.answer("На данный момент нету потока.")
        return

    if uid in data["submitted_users"]:
        await message.answer("Ты уже отправлял отчёт.")
        return

    match = re.search(r"\d+", text)
    if not match:
        return

    num = int(match.group())
    if not (1 <= num <= len(data["list"])):
        return

    if str(num) in data["statuses"]:
        await message.answer("Этот номер уже подтверждён другим пользователем.")
        return

    if "выход" in text:
        data["statuses"][str(num)] = "off"
        await message.answer("Здраствуйте, отчет сдан вы получили Выходной.")
    else:
        data["statuses"][str(num)] = "ready"
        await message.answer("Здраствуйте, вы сдали отчет.")

    data["submitted_users"].append(uid)
    save_data(data)
    await update_list_message(data)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

