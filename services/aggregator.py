import logging
import asyncio
from datetime import datetime, timedelta, time
from pyrogram import Client

from config import api_id, api_hash
from data.storage import user_data
from services.gpt_service import gpt

# Инициализируем Pyrogram-клиент
app = Client("my_bot", api_id=api_id, api_hash=api_hash)


async def start_pyrogram():
    """
    Проверяем, запущен ли Pyrogram, если нет - стартуем его.
    """
    if not app.is_connected:
        await app.start()


async def get_messages_from_channel(channel_id: int, days: int):
    """
    Получаем историю сообщений канала за последние `days` дней.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    messages = []
    async for message in app.get_chat_history(channel_id):
        if message.date >= cutoff_date:
            messages.append(message)
        else:
            break
    return messages


async def restart_scheduler_for_user(user_id: int):
    """
    Сюда можно добавить логику перезапуска персонального расписания,
    если пользователь поменял время.
    """
    pass


async def send_daily_summary(user_id: int, bot):
    """
    Шлёт ежедневную сводку пользователю user_id, проходясь по его каналам.
    """
    if user_id not in user_data or not user_data[user_id]['channels']:
        return

    try:
        summary = "📰 *Ежедневная сводка новостей*\n\n"

        for channel in user_data[user_id]['channels'][:3]:
            try:
                messages = await get_messages_from_channel(channel['id'], 2)
                if messages:
                    messages_text = "\n".join([m.text or "" for m in messages if hasattr(m, 'text') and m.text])
                    if messages_text:
                        gpt_summary = await gpt.get_best_answer(messages_text[:4000])
                        summary += f"*{channel['title']}* (@{channel['username']})\n"
                        summary += f"{gpt_summary or 'Не удалось сгенерировать сводку'}\n\n"
                    else:
                        summary += f"*{channel['title']}* (@{channel['username']})\n"
                        summary += "Нет текстовых сообщений для анализа\n\n"
                else:
                    summary += f"*{channel['title']}* (@{channel['username']})\n"
                    summary += "Нет новых сообщений\n\n"
            except Exception as e:
                logging.error(f"Error processing channel {channel['title']}: {e}")
                summary += f"*{channel['title']}* (@{channel['username']})\nОшибка при обработке канала\n\n"

        await bot.send_message(user_id, summary)

    except Exception as e:
        logging.error(f"Error sending daily summary to user {user_id}: {e}")


async def scheduler(bot):
    """
    Планировщик, который каждые 60 секунд сверяется со временем из user_data.
    Если текущее время совпадает с time(HH, MM), отсылаем ежедневную сводку.
    """
    while True:
        now = datetime.now()
        for user_id, data in user_data.items():
            if not data['settings'].get('daily_summary', True):
                continue

            summary_time = data['settings'].get('summary_time', time(9, 0))
            if now.hour == summary_time.hour and now.minute == summary_time.minute:
                await send_daily_summary(user_id, bot)

        await asyncio.sleep(60)
