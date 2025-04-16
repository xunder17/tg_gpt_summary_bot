import logging
import asyncio
from datetime import datetime, timedelta, time
from pyrogram import Client
from pyrogram.errors import ChannelPrivate, UsernameNotOccupied

from config import api_id, api_hash
from data.storage import user_data
from services.gpt_service import gpt

# Настраиваем логгирование
logging.basicConfig(level=logging.INFO)

# Инициализируем Pyrogram-клиент
app = Client("my_bot", api_id=api_id, api_hash=api_hash)


async def start_pyrogram():
    """Запуск Pyrogram-клиента, если он ещё не запущен."""
    if not app.is_connected:
        await app.start()


async def get_messages_from_channel(channel_id: int, days: int):
    """
    Получение сообщений из канала за последние `days` дней.
    Пытается подключиться к каналу, если доступа нет.
    """
    cutoff_date = datetime.now() - timedelta(days=days)

    async def collect_messages():
        messages = []
        async for message in app.get_chat_history(channel_id):
            if message.date < cutoff_date:
                break
            media = bool(message.caption or message.video)
            messages.append({
                "id": message.id,
                "date": message.date,
                "text": message.text or message.caption or "",
                "has_media": media,
                "media_type": ('video' if message.video else 'photo') if media else ""
            })
        return messages

    try:
        return await collect_messages()

    except (ChannelPrivate, UsernameNotOccupied):
        try:
            await app.join_chat(channel_id)
            return await collect_messages()
        except Exception as join_error:
            logging.error(f"Не удалось присоединиться к каналу {channel_id}: {join_error}")
            return None


async def restart_scheduler_for_user(user_id: int):
    """Логика перезапуска расписания пользователя (заглушка)."""
    pass


async def send_daily_summary(user_id: int, bot):
    """
    Отправка ежедневной сводки пользователю на основе последних сообщений из каналов.
    """
    user_channels = user_data.get(user_id, {}).get("channels", [])
    if not user_channels:
        return

    summary = "📰 *Ежедневная сводка новостей*\n\n"

    for channel in user_channels[:3]:  # Ограничение — первые 3 канала
        try:
            messages = await get_messages_from_channel(channel["id"], days=2)
            if messages:
                text_blocks = [msg["text"] for msg in messages if msg["text"]]
                combined_text = "\n".join(text_blocks)[:4000]  # GPT ограничение

                gpt_summary = await gpt.get_best_answer(combined_text) if combined_text else None
                summary += f"*{channel['title']}* (@{channel['username']})\n"
                summary += f"{gpt_summary or 'Нет данных для анализа'}\n\n"
            else:
                summary += f"*{channel['title']}* (@{channel['username']})\n"
                summary += "Нет новых сообщений\n\n"

        except Exception as e:
            logging.error(f"Ошибка при обработке канала {channel['title']}: {e}")
            summary += f"*{channel['title']}* (@{channel['username']})\nОшибка при обработке\n\n"

    try:
        await bot.send_message(user_id, summary)
    except Exception as e:
        logging.error(f"Ошибка при отправке сводки пользователю {user_id}: {e}")


async def scheduler(bot):
    """
    Планировщик, проверяющий время и отправляющий сводки, если оно совпадает с заданным.
    """
    while True:
        now = datetime.now()
        for user_id, data in user_data.items():
            if not data.get('settings', {}).get('daily_summary', True):
                continue

            summary_time = data['settings'].get('summary_time', time(9, 0))
            if now.hour == summary_time.hour and now.minute == summary_time.minute:
                await send_daily_summary(user_id, bot)

        await asyncio.sleep(60)
