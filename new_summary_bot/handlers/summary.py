import asyncio
from datetime import datetime, timedelta
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import Command
from sqlalchemy import select
from sqlalchemy.orm import selectinload  # <-- добавили!
from database import async_session
from models import User, Post
from services.gpt_summary import generate_summary
from inline import get_retry_inline
from states import SummaryRetryStates
from aiogram.fsm.context import FSMContext
from pyrogram_client import fetch_channel_history

router = Router()

@router.message(Command("summary"))
async def cmd_summary(message: Message, state: FSMContext):
    now_utc = datetime.utcnow()
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .options(selectinload(User.channels))  # <-- вот тут фикс
            .where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("Сначала /start.")
            return

        channels = user.channels

    if not channels:
        await message.answer("У вас не добавлен ни один канал!")
        return

    await message.answer("Готовлю саммари (кластеризация + GPT)...")

    posts_for_gpt = []
    for c in channels:
        messages = await fetch_channel_history(c.channel_tag, limit=50)
        channel_username = c.channel_tag.replace("@", "")

        for p in messages:
            link = f"https://t.me/{channel_username}/{p.id}"
            posts_for_gpt.append({
                "channel": c,
                "text": p.text or "",
                "link": link
            })

    summary_text = await generate_summary(posts_for_gpt, user_themes=None, retries=3)

    if "Не удалось сгенерировать" in summary_text:
        await message.answer(
            f"GPT вернул ошибку: {summary_text}",
            reply_markup=get_retry_inline()
        )
        await state.set_state(SummaryRetryStates.waiting_for_retry_choice)
    else:
        total_chars = sum(len(x["text"]) for x in posts_for_gpt)
        read_time_original = int(total_chars / 1000 * 60)
        read_time_summary = int(len(summary_text) / 1000 * 60)
        saved_time = read_time_original - read_time_summary

        final_msg = (
            f"{summary_text}\n\n"
            f"Всего постов: {len(posts_for_gpt)}\n"
            f"Время на чтение оригинальных сообщений: ~{read_time_original} сек.\n"
            f"Время на чтение саммари: ~{read_time_summary} сек.\n"
            f"Сэкономлено времени: ~{saved_time} сек."
        )
        await message.answer(final_msg)


@router.callback_query(SummaryRetryStates.waiting_for_retry_choice, lambda c: c.data == "retry_summary")
async def retry_summary_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Повторяю попытку сформировать саммари...")
    await cmd_summary(call.message, state)


@router.callback_query(SummaryRetryStates.waiting_for_retry_choice, lambda c: c.data == "short_summary")
async def short_summary_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Сделаем укороченное саммари (только первые 5 сообщений).")

    now_utc = datetime.utcnow()
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == call.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await call.message.answer("Сначала /start.")
            return

        posts_result = await session.execute(
            select(Post).where(
                Post.user_id == user.id,
                Post.date > now_utc - timedelta(days=1)
            )
        )
        posts = posts_result.scalars().all()

    if not posts:
        await call.message.answer("Нет постов всё равно.")
        return

    posts = posts[:5]
    posts_for_gpt = []
    for p in posts:
        posts_for_gpt.append({
            "channel": p.channel_tag,
            "text": p.text or "",
            "link": p.link or ""
        })

    summary_text = await generate_summary(posts_for_gpt, retries=3)
    await call.message.answer(f"Укороченное саммари:\n\n{summary_text}")
