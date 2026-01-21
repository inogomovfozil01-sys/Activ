import json
import re
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ---------- LOAD CONFIG ----------
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

TOKEN = config["token"]
ADMINS = config["admins"]

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# ---------- STATE ----------
def load_state():
    with open("state.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_state(data):
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def reset_state():
    data = {
        "active": False,
        "list": [],
        "statuses": {},
        "submitted_users": [],
        "admin_state": None
    }
    save_state(data)
    return data

def is_admin(user_id):
    return user_id in ADMINS

def format_list(data):
    text = ""
    for i, link in enumerate(data["list"], start=1):
        status = data["statuses"].get(str(i), "")
        text += f"{status}{i}. {link}\n\n"
    return text

# ---------- KEYBOARD ----------
admin_kb = ReplyKeyboardMarkup(resize_keyboard=True)
admin_kb.add(KeyboardButton("Завершить поток"))

# ---------- COMMANDS ----------
@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer(
        "Привет.\n"
        "Для отчета: Готово 12\n"
        "Для выходного: Выходной 12"
    )

@dp.message_handler(commands=["help"])
async def help_cmd(message: types.Message):
    await message.answer(
        "Форматы:\n"
        "Готово 12 – сдать отчет\n"
        "Выходной 12 – выходной\n"
        "Если нет потока → бот скажет."
    )

# ---------- ADMIN: START FLOW ----------
@dp.message_handler(lambda m: is_admin(m.from_user.id) and not load_state()["active"])
async def admin_send_list(message: types.Message):
    links = re.findall(r'https?://t\.me/\S+', message.text)
    if not links:
        return

    data = reset_state()
    data["active"] = True
    data["list"] = links
    save_state(data)

    await message.answer(
        "Поток запущен:\n\n" + format_list(data),
        reply_markup=admin_kb
    )

# ---------- ADMIN: FINISH FLOW ----------
@dp.message_handler(lambda m: m.text == "Завершить поток" and is_admin(m.from_user.id))
async def finish_flow(message: types.Message):
    data = load_state()

    if not data["active"]:
        await message.answer("Нет активного потока.")
        return

    for i in range(1, len(data["list"]) + 1):
        if str(i) not in data["statuses"]:
            data["statuses"][str(i)] = "❌ "

    data["active"] = False
    save_state(data)

    await message.answer("Поток завершён:\n\n" + format_list(data))

# ---------- USERS ----------
@dp.message_handler()
async def user_handler(message: types.Message):
    data = load_state()

    if not data["active"]:
        await message.answer("На данный момент нету потока.")
        return

    text = message.text.lower()
    numbers = re.findall(r'\d+', text)
    if not numbers:
        return

    num = numbers[0]

    if num not in map(str, range(1, len(data["list"]) + 1)):
        return

    user_id = message.from_user.id

    if user_id in data["submitted_users"]:
        await message.answer("Ты уже отправлял отчет.")
        return

    # ВЫХОДНОЙ
    if "выход" in text:
        data["statuses"][num] = "{Выходной} "
        data["submitted_users"].append(user_id)
        save_state(data)

        await message.answer("Тебе поставлен {Выходной}.")
        for admin in ADMINS:
            await bot.send_message(admin, format_list(data))
        return

    # ГОТОВО
    if "готов" in text:
        data["statuses"][num] = "✅ "
        data["submitted_users"].append(user_id)
        save_state(data)

        await message.answer("Отчет принят. Засчитано.")
        for admin in ADMINS:
            await bot.send_message(admin, format_list(data))
        return


# ---------- START ----------
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
