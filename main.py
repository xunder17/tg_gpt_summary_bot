import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import bot_token, logger
from bot.handlers import register_handlers
from services.aggregator import start_pyrogram, scheduler

async def main():
    # Создаем объект бота с парсингом HTML
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем все обработчики (хендлеры) в диспетчере
    register_handlers(dp)

    # Запускаем Pyrogram и планировщик параллельно
    asyncio.create_task(start_pyrogram())
    asyncio.create_task(scheduler(bot))

    # Запускаем поллинг (слушатель событий)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logger.info("Запуск бота...")
    asyncio.run(main())
