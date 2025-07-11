import os
from sqlalchemy import create_engine, Column, Integer, String, Text, JSON, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from datetime import datetime

# Загружаем строку подключения из переменных окружения
DATABASE_URL = "postgresql+asyncpg://valkyriefx:Q123456789@192.168.0.4:5432/tg_bot"

# Создание асинхронного подключения
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()

# Модели базы данных

class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True)
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

# Функция для создания таблиц в базе данных
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Функции для работы с базой данных

async def get_menu_from_db(menu_key: str):
    async with SessionLocal() as session:
        result = await session.execute(select(Menu).filter(Menu.menu_key == menu_key))
        menu = result.scalar_one_or_none()
        return menu

async def save_menu_to_db(menu_key: str, text: str, buttons: list, photo: str, button_groups: list, timers: dict):
    async with SessionLocal() as session:
        menu = await get_menu_from_db(menu_key)
        if not menu:
            menu = Menu(
                menu_key=menu_key,
                text=text,
                buttons=buttons,
                photo=photo,
                button_groups=button_groups,
                timers=timers
            )
            session.add(menu)
        else:
            menu.text = text
            menu.buttons = buttons
            menu.photo = photo
            menu.button_groups = button_groups
            menu.timers = timers
        
        await session.commit()

# Запись логов таймеров в базу данных
async def save_timer_log_to_db(timer_id: str, menu_key: str, button_text: str, timer_time: datetime, created_at: datetime):
    async with SessionLocal() as session:
        log = TimersLog(
            id=timer_id,
            menu_key=menu_key,
            button_text=button_text,
            timer_time=timer_time,
            created_at=created_at
        )
        session.add(log)
        await session.commit()

# Запись пользователей в базу данных
async def save_user_to_db(user_id: int, name: str, groups: list, menu_access: list, is_blocked: bool):
    async with SessionLocal() as session:
        user = await session.execute(select(User).filter(User.user_id == user_id))
        user = user.scalar_one_or_none()

        if not user:
            user = User(
                user_id=user_id,
                name=name,
                groups=groups,
                menu_access=menu_access,
                is_blocked=is_blocked
            )
            session.add(user)
        else:
            user.name = name
            user.groups = groups
            user.menu_access = menu_access
            user.is_blocked = is_blocked

        await session.commit()
