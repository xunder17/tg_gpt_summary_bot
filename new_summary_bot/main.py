import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from config import BOT_TOKEN
from database import init_db
from handlers.start import router as start_router
from handlers.summary import router as summary_router
from handlers.settings import router as settings_router
from handlers.payments import router as payments_router
from handlers.chat import router as chat_router
from schedulers import setup_scheduler
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

async def on_startup(bot: Bot):
    await init_db()
    # Удаляем вызов setup_scheduler отсюда — перенесем его в main()
    commands = [
        BotCommand(command="start", description="Начало работы"),
        BotCommand(command="summary", description="Получить саммари за сутки"),
        BotCommand(command="settings", description="Настройки"),
        BotCommand(command="payments", description="Оплата тарифов"),
        BotCommand(command="chat", description="Написать администратору"),
    ]
    await bot.set_my_commands(commands)

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=MemoryStorage())

    # Роутеры
    dp.include_router(chat_router)
    dp.include_router(payments_router)
    dp.include_router(start_router)
    dp.include_router(summary_router)
    dp.include_router(settings_router)

    # Настройка БД и команд
    await on_startup(bot)

    # Запуск планировщика (передаём текущий event loop)
    setup_scheduler(asyncio.get_event_loop())

    # Запуск бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
