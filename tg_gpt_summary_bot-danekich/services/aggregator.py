import logging
import asyncio
from datetime import datetime, timedelta, time
from pyrogram import Client
from pyrogram.errors import ChannelPrivate, UsernameNotOccupied

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
    print(channel_id)
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        processed_messages = []

        async for message in app.get_chat_history(channel_id):
            if message.date < cutoff_date:
                break

            message_data = {
                "id": message.id,
                "date": message.date,
                "text": message.text or message.caption or "",
                "has_media": False,
                "media_type": None
            }

            # Проверяем наличие медиа
            if message.photo:
                message_data.update({
                    "has_media": True,
                    "media_type": "photo",
                    "media_id": message.photo.file_id
                })
            elif message.video:
                message_data.update({
                    "has_media": True,
                    "media_type": "video",
                    "media_id": message.video.file_id
                })
            # Можно добавить обработку других типов медиа (документы, голосовые и т.д.)

            processed_messages.append(message_data)
        print(1)
        return processed_messages

    except (ChannelPrivate, UsernameNotOccupied) as e:
        try:
            await app.join_chat(channel_id)

            cutoff_date = datetime.now() - timedelta(days=days)
            processed_messages = []

            async for message in app.get_chat_history(channel_id):
                if message.date < cutoff_date:
                    break

                message_data = {
                    "id": message.id,
                    "date": message.date,
                    "text": message.text or message.caption or "",
                    "has_media": False,
                    "media_type": None
                }

                if message.photo:
                    message_data.update({
                        "has_media": True,
                        "media_type": "photo",
                        "media_id": message.photo.file_id
                    })
                elif message.video:
                    message_data.update({
                        "has_media": True,
                        "media_type": "video",
                        "media_id": message.video.file_id
                    })

                processed_messages.append(message_data)
            print(2)
            # await app.leave_chat(channel_id)
            return processed_messages

        except Exception as join_error:
            print(f"Failed to join channel {channel_id}: {join_error}")
            return None


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
