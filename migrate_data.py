import json
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
import asyncio

# ========================= Настройки =======================
DATABASE_URL = "postgresql+asyncpg://valkyriefx:Q123456789@192.168.0.4:5432/tg_bot"
menu_path = "admin/menu_data.json"
timers_log_path = "admin/timers_log.json"
users_data_path = "admin/users_data.json"

# ========================== Модели ========================

Base = declarative_base()

class Menu(Base):
    __tablename__ = "menus"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    menu_key = Column(String, unique=True, index=True, nullable=False)
    text = Column(Text)
    buttons = Column(JSON)
    photo = Column(String, nullable=True)
    button_groups = Column(JSON)
    timers = Column(JSON)

class TimersLog(Base):
    __tablename__ = "timers_log"
    
    id = Column(String, primary_key=True)
    menu_key = Column(String)
    button_text = Column(String)
    timer_time = Column(DateTime)
    created_at = Column(DateTime)

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True)
    name = Column(String)
    groups = Column(JSON)
    menu_access = Column(JSON)
    is_blocked = Column(Boolean)

# ========================== Чтение данных из JSON ====================

def load_json(file_path):
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

menu_data = load_json(menu_path)
timers_log_data = load_json(timers_log_path)
users_data = load_json(users_data_path)

# ========================== Функции для записи в БД ====================

async def insert_menu(session, menu_data):
    for menu_key, menu in menu_data.items():
        new_menu = Menu(
            menu_key=menu_key,
            text=menu.get("text"),
            buttons=menu.get("buttons", []),
            photo=menu.get("photo"),
            button_groups=menu.get("button_groups", []),
            timers=menu.get("timers", {}),
        )
        session.add(new_menu)
    await session.commit()

async def insert_timers_log(session, timers_log_data):
    for entry in timers_log_data:
        new_log = TimersLog(
            id=entry["id"],
            menu_key=entry["menu_key"],
            button_text=entry["button_text"],
            timer_time=entry["timer_time"],
            created_at=entry["created_at"],
        )
        session.add(new_log)
    await session.commit()

async def insert_users_data(session, users_data):
    for user in users_data["users"]:
        new_user = User(
            user_id=user["user_id"],
            name=user["name"],
            groups=user["groups"],
            menu_access=user["menu_access"],
            is_blocked=user["is_blocked"],
        )
        session.add(new_user)
    await session.commit()

# ========================== Основная функция ========================

async def main():
    # Создание асинхронного соединения с базой данных
    engine = create_async_engine(DATABASE_URL, echo=True)
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Создаем таблицы в базе данных
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Переносим данные в БД
        await insert_menu(session, menu_data)
        await insert_timers_log(session, timers_log_data)
        await insert_users_data(session, users_data)

if __name__ == "__main__":
    asyncio.run(main())
