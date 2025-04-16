from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import Command
from sqlalchemy import select
from inline import get_chat_cancel_inline
from states import ChatState
from database import async_session
from models import User, MessageToAdmin
from config import ADMIN_ID

router = Router()

@router.message(Command("chat"))
async def cmd_chat(message: Message, state: ChatState):
    """
    Команда /chat: Пользователь начинает писать сообщение администратору.
    """
    text = "Напишите сообщение администратору:"
    await message.answer(text, reply_markup=get_chat_cancel_inline())
    await state.set_state(ChatState.waiting_for_user_message)

@router.message(ChatState.waiting_for_user_message)
async def user_message_for_admin(message: Message, state: ChatState):
    """
    Принимаем сообщение пользователя и отправляем админу.
    Сохраняем текст в таблицу MessageToAdmin для истории.
    """
    user_text = message.text
    async with async_session() as session:
        result_user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result_user.scalar()
        if user:
            new_msg = MessageToAdmin(user_id=user.id, text=user_text)
            session.add(new_msg)
            await session.commit()

    # Отправляем админу (если ADMIN_ID задан и он не совпадает с самим пользователем)
    if ADMIN_ID and (ADMIN_ID != message.from_user.id):
        await message.bot.send_message(
            ADMIN_ID,
            f"Сообщение от пользователя {message.from_user.id}:\n{user_text}"
        )

    await message.answer("Ваше сообщение отправлено! Администратор скоро свяжется с вами!")
    await state.clear()

@router.callback_query(ChatState.waiting_for_user_message, F.data == "chat_cancel")
async def chat_cancel_cb(call: CallbackQuery, state: ChatState):
    """
    Если пользователь нажал кнопку 'Отмена' в процессе написания сообщения администратору.
    """
    await state.clear()
    await call.message.edit_text("Отменено")
