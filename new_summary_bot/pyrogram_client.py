from pyrogram import Client, errors
from config import API_ID, API_HASH

# UserBot сессия: авторизация по номеру телефона
# При первом запуске спросит телефон, код
pyro_app = Client(
    name="pyro_session_user",
    api_id=API_ID,
    api_hash=API_HASH
)
async def start_pyrogram():
    """
    Проверяем, запущен ли Pyrogram, если нет - стартуем его.
    """
    if not pyro_app.is_connected:
        await pyro_app.start()
async def subscribe_to_channel(channel: str) -> bool:
    """
    Присоединяемся к публичному каналу/группе (например, '@channel').
    Возвращаем True, если успешно.
    """
    await start_pyrogram()
    try:
        await pyro_app.join_chat(channel)
    except errors.RPCError as e:
        print(f"Не удалось подписаться на {channel}: {e}")
        return False
    except Exception as e:
        print(f"Ошибка при подписке на {channel}: {e}")
        return False
    return True

async def fetch_channel_history(channel: str, limit: int = 50):
    """
    Получаем последние N сообщений. Возвращаем список объектов Pyrogram Message.
    """
    await start_pyrogram()
    messages_data = []
    try:
        async for msg in pyro_app.get_chat_history(channel, limit=limit):
            messages_data.append(msg)
    except Exception as e:
        print(f"Ошибка при получении сообщений из {channel}: {e}")
    return messages_data
