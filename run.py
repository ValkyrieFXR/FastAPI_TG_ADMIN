import asyncio
import admin.admin_main
import bot.bot_main

async def main():
    # Запускаем одновременно и бота и админку
    await asyncio.gather(
        admin.admin_main.start_admin(),
        bot.bot_main.start_bot()
    )

if __name__ == "__main__":
    asyncio.run(main())