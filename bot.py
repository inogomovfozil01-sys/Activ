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
        elif final and not status:
            icon = "❌"

        line = f"{icon} {i}. {item}".strip()
        lines.append(line)

    return "\n\n".join(lines)


async def update_list_message(data):
    if not data["list_message_id"]:
        return

    text = render_list(data)
    await bot.edit_message_text(
        chat_id=data["list_chat_id"],
        message_id=data["list_message_id"],
        text=text
    )


admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Новый список")],
        [KeyboardButton(text="📋 Показать список")],
        [KeyboardButton(text="📤 Завершить поток")],
        [KeyboardButton(text="🧹 Полный сброс")]
    ],
    resize_keyboard=True
)


@dp.message(Command("start"))
async def start(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Админ панель активна.", reply_markup=admin_kb)
    else:
        await message.answer(
            "Привет.\n"
            "Отправляй отчёт так:\n\n"
            "Готово 12\n"
            "или\n"
            "Выходной 12\n\n"
            "Если нет активного потока — бот скажет об этом."
        )


@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "Команды:\n"
        "/start – запуск\n"
        "/help – помощь\n\n"
        "Отчёт принимается даже с ошибками в тексте.\n"
        "Главное чтобы был номер."
    )


@dp.message(F.from_user.id.in_(ADMINS))
async def admin_handler(message: Message):
    data = load_data()
    text = message.text.strip()

    if text == "➕ Новый список":
        data = default_data()
        data["active"] = True
        save_data(data)
        await message.answer("Скинь список пунктов. Каждый с новой строки.")
        return

    if text == "📋 Показать список":
        if not data["list"]:
            await message.answer("Список пуст.")
        else:
            await message.answer(render_list(data))
        return

    if text == "🧹 Полный сброс":
        data = default_data()
        save_data(data)
        await message.answer("Полный сброс выполнен.")
        return

    if text == "📤 Завершить поток":
        data["active"] = False

        # Ставим ❌ тем кто не сдал
        for i in range(1, len(data["list"]) + 1):
            if str(i) not in data["statuses"]:
                data["statuses"][str(i)] = "fail"

        save_data(data)

        await update_list_message(data)

        # Рассылка тем кто не сдал
        for uid in data["submitted_users"]:
            pass

        await message.answer("Поток завершён.\n\n" + render_list(data, final=True))
        return

    # если админ скинул список
    if data["active"] and not data["list"]:
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # убираем 1. , 2. , и тд
            line = re.sub(r"^\d+\.\s*", "", line)
            items.append(line)

        data["list"] = items
        save_data(data)

        msg = await message.answer(render_list(data))
        data["list_message_id"] = msg.message_id
        data["list_chat_id"] = msg.chat.id
        save_data(data)
        return


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

    if "выход" in text:
        data["statuses"][str(num)] = "off"
        await message.answer("Отмечено как {Выходной}.")
    else:
        # любое другое сообщение с номером считаем готово
        data["statuses"][str(num)] = "ready"
        await message.answer("Ты сдал отчёт. ✅")

    data["submitted_users"].append(uid)
    save_data(data)

    await update_list_message(data)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
