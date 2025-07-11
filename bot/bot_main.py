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
from admin.admin_main import timers_log_page
from database import save_menu_to_db, get_menu_from_db, save_timer_log_to_db, save_user_to_db

BOT_TOKEN = "8172830780:AAFfWHaBsCeFe7I7gdQCdS-uKy37Gx-PM1Q"
BOT_STATUS_FILE = "admin/bot_status.json"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# === Функция для получения меню из базы данных ===
async def load_menu():
    # Получаем меню из базы данных
    return await get_menu_from_db()

def write_bot_status(running: bool):
    try:
        with open(BOT_STATUS_FILE, "w", encoding="utf-8") as f:  # type: ignore
            json.dump({"running": running}, f)
    except Exception:
        pass

# === Лог таймеров ===
async def load_timers_log():
    try:
        timers_log = await timers_log_page()

        # Получаем меню для проверки актуальных таймеров
        menu_data = await load_menu()

        # Фильтруем записи в логе, исключая завершённые таймеры
        filtered_timers = [
            timer for timer in timers_log
            if "button_delays" in menu_data.get(timer["menu_key"], {}).get("timers", {})
            and timer["button_text"] in menu_data[timer["menu_key"]]["timers"]["button_delays"]
        ]
        
        return filtered_timers
    except Exception:
        return []

async def save_timers_log(data):
    try:
        await save_timer_log_to_db(data)
    except Exception:
        pass

async def is_button_active(button, button_delays):
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
    menu = await get_menu_from_db(menu_key)
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

# Обработчик команды /start
@router.message(Command("start"))
async def handle_start(message: types.Message):
    await send_menu(message.chat.id, "main", message)

# Обработчик callback-запросов
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

# Пример сохранения нового меню в базу данных
@router.message(Command("save_menu"))
async def save_sample_menu(message: types.Message):
    menu_key = "main"
    text = "Добро пожаловать в меню!"
    buttons = [
        {"text": "Кнопка 1", "callback": "callback1"},
        {"text": "Кнопка 2", "callback": "callback2"}
    ]
    photo = None
    button_groups = [1, 1]
    timers = {}

    # Сохраняем меню в БД
    await save_menu_to_db(menu_key, text, buttons, photo, button_groups, timers)
    await message.answer("Меню сохранено в базу данных!")

# Пример добавления таймера в базу данных
@router.message(Command("save_timer_log"))
async def save_timer_log(message: types.Message):
    timer_id = str(uuid.uuid4())
    menu_key = "main"
    button_text = "Кнопка 1"
    timer_time = datetime.now()
    created_at = datetime.now()

    await save_timer_log_to_db(timer_id, menu_key, button_text, timer_time, created_at)
    await message.answer("Таймер добавлен в базу данных!")

# Пример добавления пользователя в базу данных
@router.message(Command("save_user"))
async def save_user(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    groups = []
    menu_access = ["main"]
    is_blocked = False

    await save_user_to_db(user_id, name, groups, menu_access, is_blocked)
    await message.answer(f"Пользователь {name} добавлен в базу данных!")

# Запуск бота
async def start_bot():
    write_bot_status(True)
    dp.include_router(router)
    try:
        await dp.start_polling(bot)
    finally:
        write_bot_status(False)

if __name__ == "__main__":
    import asyncio
    asyncio.run(start_bot())
