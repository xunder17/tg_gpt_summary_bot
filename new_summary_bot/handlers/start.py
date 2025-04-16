import re
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from states import StartDialog
from inline import (
    get_start_inline_1,
    get_start_inline_2,
    get_start_inline_3,
    get_start_inline_4,
    get_finish_setup_inline
)
from models import User, Channel, Post
from database import async_session
from pyrogram_client import subscribe_to_channel, fetch_channel_history
from services.gpt_summary import generate_summary

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """
    Обработчик команды /start. 
    Начинается приветственное взаимодействие с пользователем,
    а также создаём запись в таблице User, если её нет.
    """
    text = (
        "Привет!\n"
        "Я – бот summary_bot.\n"
        "Я делаю саммари сообщений каналов, помогаю тебе быть в курсе и экономить время."
    )
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        existing_user = result.scalar()
        if not existing_user:
            new_user = User(telegram_id=message.from_user.id)
            session.add(new_user)
            await session.commit()

    await message.answer(text, reply_markup=get_start_inline_1())
    await state.set_state(StartDialog.waiting_for_show_example)


@router.callback_query(StartDialog.waiting_for_show_example, F.data == "how_it_works")
async def how_it_works_cb(call: CallbackQuery):
    """
    Ответ на нажатие кнопки «Как это работает?»
    """
    text = (
        "Как это работает?\n\n"
        "1. Ты скидываешь мне интересующие тебя каналы.\n"
        "2. Я делаю саммари – краткий пересказ сообщений из этих каналов.\n"
        "3. Раз в сутки я присылаю тебе это саммари."
    )
    await call.message.edit_text(text, reply_markup=get_start_inline_2())

@router.callback_query(StartDialog.waiting_for_show_example, F.data == "benefits")
async def benefits_cb(call: CallbackQuery):
    """
    Ответ на нажатие кнопки «В чем польза?»
    """
    text = (
        "В чем польза?\n\n"
        "1. Ты будешь уверен в том, что ничего не пропустишь.\n"
        "2. Ты не будешь тратить время на неинтересные сообщения.\n"
        "3. Информация из всех каналов в одном месте."
    )
    await call.message.edit_text(text, reply_markup=get_start_inline_3())

@router.callback_query(StartDialog.waiting_for_show_example, F.data == "example_view")
async def example_view_cb(call: CallbackQuery):
    """
    Ответ на нажатие кнопки «Как это выглядит?»
    """
    text = (
        "Лучше один раз увидеть, чем сто раз... хм... прочитать.\n\n"
        "Давай покажу тебе саммари новостного канала @vcnews (пример канала)"
    )
    await call.message.edit_text(text, reply_markup=get_start_inline_4())

@router.callback_query(StartDialog.waiting_for_show_example, F.data == "show_example_summary")
async def show_example_summary_cb(call: CallbackQuery, state: FSMContext):
    """
    Ответ на нажатие кнопки «Давай» (показать пример саммари канала @vcnews).
    Использует Pyrogram для чтения канала, затем gpt_summary.generate_summary.
    """
    now_utc = datetime.utcnow()
    # Пробуем взять последние ~40 сообщений
    hist = await fetch_channel_history("@vcnews", limit=40)
    if not hist:
        # Если не получилось прочитать (или канал пуст), пропускаем
        await call.message.edit_text(
            "Не удалось прочитать канал @vcnews.\n\n"
            "Теперь настроим бота под тебя.\n"
            "Чтобы добавить канал, просто перешли мне сообщение из этого канала.\n"
            "Важно: канал должен быть открытым.\n"
            "Давай, пересылай, я жду"
        )
        await state.set_state(StartDialog.waiting_for_channel_forward)
        return

    # Отбираем сообщения за последние сутки
    last_day_posts = []
    for msg in hist:
        if msg.date > (now_utc - timedelta(days=1)):
            txt = msg.text or msg.caption or ""
            link = f"https://t.me/vcnews/{msg.id}"
            last_day_posts.append({
                "channel": "@vcnews",
                "text": txt,
                "link": link
            })

    if not last_day_posts:
        # Если нет свежих постов
        await call.message.edit_text(
            "Похоже, что у @vcnews нет свежих постов за последние сутки.\n\n"
            "Теперь настроим бота под тебя.\n"
            "Чтобы добавить канал, просто перешли мне сообщение из этого канала.\n"
            "Важно: канал должен быть открытым.\n"
            "Давай, пересылай, я жду"
        )
        await state.set_state(StartDialog.waiting_for_channel_forward)
        return

    # Генерируем пример саммари
    summary_text = await generate_summary(last_day_posts)
    # Условно считаем, что читать оригинал 60 сек, саммари 15, разница 45
    read_time_original = 60
    read_time_summary = 15
    saved_time = read_time_original - read_time_summary

    final_msg = (
        f"{summary_text}\n\n"
        f"Время на чтение оригинальных сообщений: ~{read_time_original} сек.\n"
        f"Время на чтение саммари: ~{read_time_summary} сек.\n"
        f"Сэкономлено времени: ~{saved_time} сек.\n\n")
    await call.message.reply(final_msg)
    final_msg = (
        "Теперь настроим бота под тебя.\n"
        "Чтобы добавить канал, просто перешли мне сообщение из этого канала.\n"
        "Важно: канал должен быть открытым.\n"
        "Давай, пересылай, я жду"
    )
    await call.message.reply(final_msg)

    await state.set_state(StartDialog.waiting_for_channel_forward)


@router.message(StartDialog.waiting_for_channel_forward)
async def add_channel_from_forward(message: Message, state: FSMContext):
    """
    Шаг, где пользователь пересылает сообщение из канала,
    чтобы добавить канал в список отслеживаемых.
    """
    if not message.forward_from_chat or message.forward_from_chat.type != "channel":
        await message.answer("Перешли сообщение из ПУБЛИЧНОГО канала (есть @username).")
        return

    channel_username = message.forward_from_chat.username
    if not channel_username:
        # У канала нет @username, значит нельзя читать историю Pyrogram
        await message.answer("У канала нет @username. Не могу читать его историю.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == message.from_user.id)
            .options(selectinload(User.channels))
        )
        user = result.scalar()
        if not user:
            # если вдруг user отсутствует (не должно случиться)
            await message.answer("Сначала /start.")
            return

        existing = [ch for ch in user.channels if ch.channel_tag.lower() == f"@{channel_username}".lower()]
        if existing:
            await message.answer(f"Канал @{channel_username} уже добавлен.")
        else:
            new_ch = Channel(user_id=user.id, channel_tag=f"@{channel_username}")
            session.add(new_ch)
            await session.commit()
            await message.answer(f"Результат:\n@{channel_username} добавлен в список каналов.")

    joined_ok = await subscribe_to_channel(f"@{channel_username}")
    if not joined_ok:
        await message.answer(
            f"Не получилось подписаться на @{channel_username}.\n"
            "Возможно, канал приватный.\n"
        )

    # Пробуем прочитать последние ~100 сообщений
    # hist = await fetch_channel_history(f"@{channel_username}", limit=100)
    # if not hist:
    #     await message.answer(
    #         f"Не удалось прочитать старые сообщения @{channel_username}. "
    #         "Возможно, нужны дополнительные права."
    #     )
    #     return
    #
    # now_utc = datetime.utcnow()
    # last_24h_msgs = []
    # for msg in hist:
    #     if msg.date > (now_utc - timedelta(days=1)):
    #         txt_ = msg.text or msg.caption or ""
    #         link_ = f"https://t.me/{channel_username.strip('@')}/{msg.id}"
    #         last_24h_msgs.append((msg.date, txt_, link_))
    #
    # if not last_24h_msgs:
    #     await message.answer("Кажется, за последние сутки в этом канале нет новых сообщений.")
    #     return

    # Сохраняем в Post, привязываем к user.id
    # async with async_session() as session:
    #     for (dt, txt_, link_) in last_24h_msgs:
    #         new_post = Post(
    #             user_id=user.id,
    #             channel_tag=f"@{channel_username}",
    #             text=txt_,
    #             link=link_,
    #             date=dt
    #         )
    #         session.add(new_post)
    #     await session.commit()

    # Генерируем саммари по последним постам
    # posts_for_gpt = []
    # for (dt, txt_, link_) in last_24h_msgs:
    #     posts_for_gpt.append({
    #         "channel": f"@{channel_username}",
    #         "text": txt_,
    #         "link": link_
    #     })
    #
    # summary_text = await generate_summary(posts_for_gpt)
    # # Условный расчёт времени
    # read_time_original = 120
    # read_time_summary = 30
    # saved_time = read_time_original - read_time_summary
    #
    # final_msg = (
    #     f"{summary_text}\n\n"
    #     f"Всего сообщений: {len(posts_for_gpt)}\n"
    #     f"Время на чтение оригинала – {read_time_original} сек.\n"
    #     f"Время на чтение саммари – {read_time_summary} сек.\n"
    #     f"Сэкономлено – {saved_time} сек."
    # )
    # await message.answer(final_msg)

    # Теперь просим настроить время рассылки
    await message.answer(
        "Теперь давай настроим время рассылки.\n"
        "Во сколько ты хочешь получать саммари?\n"
        "Напиши время в формате ЧЧ:мм\n"
        "Например, 10:30"
    )
    await state.set_state(StartDialog.waiting_for_schedule_time)


@router.message(StartDialog.waiting_for_schedule_time)
async def set_schedule_time(message: Message, state: FSMContext):
    """
    Сохраняем ввод «HH:MM».
    """
    if not re.match(r"^([0-1]?\d|2[0-3]):([0-5]\d)$", message.text):
        await message.answer("Неправильный формат времени (ЧЧ:мм). Пример: 09:00")
        return

    schedule_time = message.text.strip()
    await state.update_data(schedule_time=schedule_time)
    await message.answer("Ок. А сейчас у тебя который час? (Тоже в формате ЧЧ:мм)")
    await state.set_state(StartDialog.waiting_for_user_local_time)

@router.message(StartDialog.waiting_for_user_local_time)
async def set_user_local_time(message: Message, state: FSMContext):
    """
    Пользователь присылает текущее локальное время. 
    Можно вычислить смещение offset, если нужно.
    """
    if not re.match(r"^([0-1]?\d|2[0-3]):([0-5]\d)$", message.text):
        await message.answer("Неправильный формат времени (ЧЧ:мм). Пример: 09:00")
        return

    user_local_time = message.text.strip()
    data = await state.get_data()
    schedule_time = data.get("schedule_time")

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar()
        if not user:
            await message.answer("Сначала /start.")
            await state.clear()
            return

        # Допустим, мы здесь не пытаемся точно вычислять offset, 
        # можно в будущем добавить логику.
        # Пока просто сохраняем schedule_time, user_local_time.
        user.schedule_time = schedule_time
        user.user_local_time = user_local_time
        session.add(user)
        await session.commit()

    await message.answer(
        "Супер, настройка завершена.\n\n"
        "Продолжай пересылать мне сообщения из каналов – я их добавлю в твой список.\n"
        "Если у тебя появятся вопросы – пиши в /chat\n"
        "Удачи!",
        reply_markup=get_finish_setup_inline()
    )

@router.callback_query(StartDialog.waiting_for_user_local_time, F.data == "finish_setup")
async def finish_setup_cb(call: CallbackQuery, state: FSMContext):
    """
    Когда пользователь нажимает «Завершить» в конце настройки.
    """
    await state.clear()
    await call.message.answer("Настройка завершена!")
