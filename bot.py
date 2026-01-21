import json
import re
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN = config["token"]
ADMINS = config["admins"]
DATA_FILE = "data.json"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

def default_data():
    return {
        "active": False,
        "list": [],
        "statuses": {},
        "submitted_users": [],
        "admin_state": None
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
            icon = "🌙"
        elif final and not status:
            icon = "❌"
        lines.append(f"{icon} {i}. {item}".strip())
    return "\n\n".join(lines)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Создать новый список")],
        [KeyboardButton(text="📋 Показать текущий список")],
        [KeyboardButton(text="🛠 Изменить статус")],
        [KeyboardButton(text="❌ Удалить пункт")],
        [KeyboardButton(text="📤 Выдать итоговый список")],
        [KeyboardButton(text="🔒 Закончить поток")],
        [KeyboardButton(text="🧹 Полный сброс")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def start(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Админ-панель активна", reply_markup=admin_kb)
    else:
        await message.answer(
            "Отправляй:\n"
            "Готово <номер>\n"
            "Выходной <номер>\n\n"
            "Пример:\nГотово 1"
        )

@dp.message(F.from_user.id.in_(ADMINS))
async def admin_handler(message: Message):
    data = load_data()
    text = message.text.strip()

    if text == "➕ Создать новый список":
        data.update(default_data())
        data["active"] = True
        save_data(data)
        await message.answer("Отправь список пунктов, каждый с новой строки")
        return

    if text == "📋 Показать текущий список":
        await message.answer(render_list(data) or "Список пуст")
        return

    if text == "📤 Выдать итоговый список":
        await message.answer(render_list(data, final=True) or "Список пуст")
        return

    if text == "🔒 Закончить поток":
        data["active"] = False
        save_data(data)
        await message.answer("Поток закрыт.\n\n" + (render_list(data, final=True) or "Список пуст"))
        return

    if text == "🧹 Полный сброс":
        data = default_data()
        save_data(data)
        await message.answer("Система полностью сброшена")
        return

    if text == "❌ Удалить пункт":
        data["admin_state"] = "delete"
        save_data(data)
        await message.answer("Отправь номер пункта для удаления")
        return

    if text == "🛠 Изменить статус":
        data["admin_state"] = "set_status"
        save_data(data)
        await message.answer("Формат:\nномер ready/off\nПример:\n2 ready")
        return

    state = data.get("admin_state")

    if data["active"] and not data["list"]:
        items = [x.strip() for x in message.text.split("\n") if x.strip()]
        data["list"] = items
        data["admin_state"] = None
        save_data(data)
        await message.answer("Список создан:\n\n" + render_list(data))
        return

    if state == "delete":
        if text.isdigit():
            num = int(text)
            if 1 <= num <= len(data["list"]):
                data["list"].pop(num - 1)
                data["statuses"].pop(str(num), None)
                data["admin_state"] = None
                save_data(data)
                await message.answer("Пункт удалён")
        return

    if state == "set_status":
        parts = text.split()
        if len(parts) == 2:
            num, st = parts
            if num.isdigit() and st in ["ready", "off"]:
                data["statuses"][num] = st
                data["admin_state"] = None
                save_data(data)
                await message.answer("Статус обновлён")
        return

@dp.message()
async def user_handler(message: Message):
    data = load_data()
    text = message.text.lower()
    uid = message.from_user.id

    if not data["active"]:
        return

    if uid in data["submitted_users"]:
        await message.answer("Ты уже отправлял статус")
        return

    match = re.search(r"\d+", text)
    if not match:
        return

    num = int(match.group())
    if not (1 <= num <= len(data["list"])):
        return

    if "готов" in text:
        data["statuses"][str(num)] = "ready"
    elif "выход" in text:
        data["statuses"][str(num)] = "off"
    else:
        return

    data["submitted_users"].append(uid)
    save_data(data)
    await message.answer("Принято ✅")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
