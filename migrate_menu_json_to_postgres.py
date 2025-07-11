import json
import asyncio
from database import async_session, engine
from models import Menu
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from database import Base

MENU_JSON_PATH = "admin/menu_data.json"

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def migrate():
    try:
        with open(MENU_JSON_PATH, "r", encoding="utf-8") as f:
            menu_data = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка при чтении JSON: {e}")
        return

    async with async_session() as session:
        for key, value in menu_data.items():
            menu = await session.get(Menu, key)
            if not menu:
                menu = Menu(key=key)
                session.add(menu)

            menu.text = value.get("text")
            menu.buttons = value.get("buttons", [])
            menu.button_groups = value.get("button_groups", [])
            menu.photo = value.get("photo")
            menu.timers = value.get("timers", {})

        try:
            await session.commit()
            print("✅ Меню успешно перенесено в базу данных.")
        except SQLAlchemyError as e:
            await session.rollback()
            print(f"❌ Ошибка при сохранении в БД: {e}")

async def main():
    await create_tables()
    await migrate()

if __name__ == "__main__":
    asyncio.run(main())
