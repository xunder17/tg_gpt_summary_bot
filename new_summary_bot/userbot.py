import asyncio
import logging
from pyrogram import filters
from pyrogram_client import pyro_app
from database import init_db, async_session
from models import Post
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pyro_app.on_message(filters.chat_type.channels)
async def channel_message_handler(client, msg):
    """
    Приходит сообщение в канале. 
    Мы сохраняем его в таблицу Post.
    
    - user_id = 0 (по умолчанию) — если хотим в будущем распределить посты к конкретным user-аккаунтам, надо доработать.
    - Сохраняем реальную ссылку (если канал публичный, msg.chat.username не пуст).
    """
    try:
        channel_username = msg.chat.username or ""
        message_id = msg.id
        date_utc = msg.date
        text_content = None

        if msg.text:
            text_content = msg.text.strip()
        elif msg.caption:
            text_content = msg.caption.strip()

        if text_content:
            link_ = ""
            if channel_username:
                link_ = f"https://t.me/{channel_username}/{message_id}"

            async with async_session() as session:
                new_post = Post(
                    user_id=0,  
                    channel_tag=f"@{channel_username}" if channel_username else str(msg.chat.id),
                    text=text_content,
                    link=link_,
                    date=date_utc
                )
                session.add(new_post)
                await session.commit()
                logger.info(f"[UserBot] Сохранили сообщение @{channel_username}, ID={message_id}")
    except Exception as e:
        logger.error(f"Ошибка в userbot: {e}")

async def userbot_main():
    """
    Основная корутина запуска «userbot».
    При первом запуске попросит телефон + код (в консоли).
    Подготовка фундамента для «нескольких аккаунтов»:
    - если захотите, можете тут запускать несколько Client(...) в цикле.
    """
    await init_db()
    await pyro_app.start()
    logger.info("[UserBot] Запущен как пользователь (по телефону). Ожидание сообщений...")

    while True:
        await asyncio.sleep(10)

def run_userbot():
    asyncio.run(userbot_main())

if __name__ == "__main__":
    run_userbot()
