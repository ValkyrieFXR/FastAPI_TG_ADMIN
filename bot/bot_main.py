import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types, Router
import aiogram
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
import os
import uuid  # Для id в логе, если потребуется

BOT_TOKEN = "8172830780:AAFfWHaBsCeFe7I7gdQCdS-uKy37Gx-PM1Q"
BOT_STATUS_FILE = "admin/bot_status.json"
menu_path = "admin/menu_data.json"
timers_log_path = "admin/timers_log.json"  # Путь к логу таймеров

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

def load_menu():
    with open(menu_path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_bot_status(running: bool):
    try:
        with open(BOT_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"running": running}, f)
    except Exception:
        pass

# === Лог таймеров ===
def load_timers_log():
    if not os.path.exists(timers_log_path):
        return []
    try:
        with open(timers_log_path, "r", encoding="utf-8") as f:
            timers_log = json.load(f)

            # Получаем меню для проверки актуальных таймеров
            menu_data = load_menu()

            # Фильтруем записи в логе, исключая завершённые таймеры
            filtered_timers = [
                timer for timer in timers_log
                if "button_delays" in menu_data.get(timer["menu_key"], {}).get("timers", {})
                and timer["button_text"] in menu_data[timer["menu_key"]]["timers"]["button_delays"]
            ]
            
            return filtered_timers
    except Exception:
        return []

def save_timers_log(data):
    try:
        with open(timers_log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def is_button_active(button, button_delays):
    now = datetime.now()
    delay = button_delays.get(button["text"])
    if delay:
        try:
            delay_time = datetime.fromisoformat(delay)
            if now < delay_time:
                return "В ожидании"
            else:
                return "Активна"
        except Exception:
            return "Активна"
    return "Активна"

def get_keyboard(buttons, groups=None):
    keyboard = []
    row = []

    for btn, group in zip(buttons, groups or [1] * len(buttons)):
        if isinstance(btn, list):
            row_buttons = []
            for b in btn:
                if b.get("url"):
                    row_buttons.append(InlineKeyboardButton(text=b["text"], url=b["url"]))
                else:
                    row_buttons.append(InlineKeyboardButton(text=b["text"], callback_data=b.get("callback", "noop")))
            keyboard.append(row_buttons)
            row = []
        else:
            if btn.get("url"):
                tg_btn = InlineKeyboardButton(text=btn["text"], url=btn["url"])
            else:
                tg_btn = InlineKeyboardButton(text=btn["text"], callback_data=btn.get("callback", "noop"))

            if group == 2:
                row.append(tg_btn)
                if len(row) == 2:
                    keyboard.append(row)
                    row = []
            else:
                if row:
                    keyboard.append(row)
                    row = []
                keyboard.append([tg_btn])

    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def send_menu(chat_id, menu_key, message: types.Message = None):
    menu_data = load_menu()
    menu = menu_data.get(menu_key)
    if not menu:
        text = "Меню не найдено."
        if message:
            try:
                await bot.edit_message_text(text, chat_id, message.message_id)  # редактируем текст
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message can't be edited" in str(e):
                    # Если сообщение не может быть отредактировано, отправляем новое
                    await bot.send_message(chat_id, text)
                else:
                    raise e  # Пробрасываем другие ошибки
        else:
            await bot.send_message(chat_id, text)
        return

    now = datetime.now()
    timers = menu.get("timers", {})
    menu_start = timers.get("menu_start")
    if menu_start:
        try:
            menu_start_time = datetime.fromisoformat(menu_start)
            if now < menu_start_time:
                await bot.send_message(chat_id, "Меню пока недоступно. Попробуйте позже.")
                return
        except Exception:
            pass

    buttons = menu.get("buttons", [])
    groups = menu.get("button_groups", [1] * len(buttons))
    button_delays = timers.get("button_delays", {})

    def is_visible(b):
        text = b.get("text")
        if not text:
            return True
        delay = button_delays.get(text)
        if not delay:
            return True
        try:
            delay_time = datetime.fromisoformat(delay)
            return now >= delay_time
        except Exception:
            return True

    visible_buttons = []
    visible_groups = []

    for btn_group, group_size in zip(buttons, groups):
        if isinstance(btn_group, list):
            filtered = [b for b in btn_group if is_visible(b)]
            if filtered:
                visible_buttons.append(filtered)
                visible_groups.append(2)
        else:
            if is_visible(btn_group):
                visible_buttons.append(btn_group)
                visible_groups.append(group_size)

    markup = get_keyboard(visible_buttons, visible_groups)

    # Отправляем фото, если оно есть
    if menu.get("photo"):
        if message:
            try:
                await bot.edit_message_media(media=types.InputMediaPhoto(menu["photo"], caption=menu["text"]), chat_id=chat_id, message_id=message.message_id, reply_markup=markup)
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message can't be edited" in str(e):
                    await bot.send_photo(chat_id, photo=menu["photo"], caption=menu["text"], reply_markup=markup)
                else:
                    raise e
        else:
            await bot.send_photo(chat_id, photo=menu["photo"], caption=menu["text"], reply_markup=markup)
    else:
        if message:
            try:
                await bot.edit_message_text(menu["text"], chat_id=chat_id, message_id=message.message_id, reply_markup=markup)
            except aiogram.exceptions.TelegramBadRequest as e:
                if "message can't be edited" in str(e):
                    await bot.send_message(chat_id, menu["text"], reply_markup=markup)
                else:
                    raise e
        else:
            await bot.send_message(chat_id, menu["text"], reply_markup=markup)

@router.message(Command("start"))
async def handle_start(message: types.Message):
    await send_menu(message.chat.id, "main", message)


@router.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    await callback.answer()
    await send_menu(callback.message.chat.id, callback.data, callback.message)


@router.message()
async def handle_message(message: types.Message):
    # Пропускаем обработку, если это не команда "start"
    if message.text.lower() != "/start":
        return
    await send_menu(message.chat.id, "main", message)



async def start_bot():
    write_bot_status(True)
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        write_bot_status(False)
