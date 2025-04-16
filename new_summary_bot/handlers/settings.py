from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
import re

from inline import (
    get_settings_main, get_settings_channels,
    get_add_channels_inline, get_delete_channels_inline,
    get_settings_filters_empty, get_add_topics_inline,
    get_topics_confirmation_inline, get_added_topics_inline,
    get_edit_topics_inline, get_settings_time_inline,
    get_cancel_schedule_inline
)
from states import AddChannelsState, DeleteChannelsState, AddTopicsState, EditTopicsState
from database import async_session
from models import User, Channel, Topic
from pyrogram_client import subscribe_to_channel

router = Router()

@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """
    Команда /settings: Показываем главное меню настроек.
    """
    await message.answer("Главное меню настроек", reply_markup=get_settings_main())

@router.callback_query(F.data == "close_settings")
async def close_settings_cb(call: CallbackQuery):
    """
    Кнопка «Закрыть» в настройках.
    """
    await call.message.delete()

@router.callback_query(F.data == "settings_channels")
async def settings_channels_cb(call: CallbackQuery):
    """
    Показ списка каналов, кнопки «Добавить», «Удалить», «Назад».
    """
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == call.from_user.id)
            .options(selectinload(User.channels))
        )
        user = result.scalar()
        channels = user.channels

        if user.tariff == "free":
            allowed = 3
        elif user.tariff == "standard":
            allowed = 20
        elif user.tariff == "pro":
            allowed = 40
        else:
            allowed = 3

    channel_list_text = "\n".join([f"- {ch.channel_tag}" for ch in channels])
    text = (
        f"Вот список твоих каналов:\n"
        f"{channel_list_text}\n\n"
        f"Добавлено каналов: {len(channels)}\n"
        f"Доступно каналов по тарифу: {allowed}"
    )
    await call.message.edit_text(text, reply_markup=get_settings_channels())

@router.callback_query(F.data == "add_channels")
async def add_channels_cb(call: CallbackQuery, state: FSMContext):
    """
    Пользователь хочет добавить новые каналы. 
    Пересылает сообщения из каналов.
    """
    text = (
        "Пересылай мне сообщения из новых каналов, чтобы я добавил их в список.\n"
        "Когда закончишь, нажми 'Готово'."
    )
    await call.message.edit_text(text, reply_markup=get_add_channels_inline())
    await state.set_state(AddChannelsState.waiting_for_new_channels)

@router.message(AddChannelsState.waiting_for_new_channels)
async def new_channels_forward(message: Message):
    """
    Пользователь переслал сообщение из канала. 
    Проверяем публичность, добавляем в БД.
    """
    if not message.forward_from_chat or message.forward_from_chat.type != "channel":
        await message.answer("Не получилось добавить, канал – не найден.\nПопробуй ещё раз.")
        return

    channel_username = message.forward_from_chat.username
    if not channel_username:
        await message.answer("Это закрытый канал или у него нет username. Пропускаю.")
        return

    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == message.from_user.id)
            .options(selectinload(User.channels))
        )
        user = result.scalar()

        # Проверяем лимит тарифного плана
        if user.tariff == "free":
            allowed = 3
        elif user.tariff == "standard":
            allowed = 20
        elif user.tariff == "pro":
            allowed = 40
        else:
            allowed = 3

        if len(user.channels) >= allowed:
            await message.answer(f"У тебя уже {len(user.channels)} каналов, а тариф позволяет максимум {allowed}.")
            return
        
        # Пытаемся подписаться как userbot
        joined_ok = await subscribe_to_channel(f"@{channel_username}")
        if not joined_ok:
            await message.answer(
                f"Не удалось подписаться на @{channel_username}. "
                "Вероятно, канал недоступен. Но всё равно добавлю в список."
            )

        # Проверяем, нет ли уже в списке
        existing_ch = [ch for ch in user.channels if ch.channel_tag == f"@{channel_username}"]
        if existing_ch:
            await message.answer(f"Канал @{channel_username} уже в списке.")
            return

        new_channel = Channel(user_id=user.id, channel_tag=f"@{channel_username}")
        session.add(new_channel)
        await session.commit()

    await message.answer(f"Канал @{channel_username} успешно добавлен!")

@router.callback_query(AddChannelsState.waiting_for_new_channels, F.data == "add_channels_done")
async def add_channels_done_cb(call: CallbackQuery, state: FSMContext):
    """
    Пользователь нажал "Готово" при добавлении каналов.
    """
    await state.clear()
    await call.message.edit_text("Каналы добавлены. Возвращаюсь в меню.")
    await settings_channels_cb(call)

@router.callback_query(F.data == "delete_channels")
async def delete_channels_cb(call: CallbackQuery, state: FSMContext):
    """
    Пользователь хочет удалить каналы. Показываем список, каждый – inline-кнопка.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == call.from_user.id)
            .options(selectinload(User.channels))
        )
        user = result.scalar()
        channels = user.channels

    await call.message.edit_text(
        "Выбери каналы для удаления:",
        reply_markup=get_delete_channels_inline(channels)
    )
    await state.set_state(DeleteChannelsState.waiting_for_delete_choice)

@router.callback_query(DeleteChannelsState.waiting_for_delete_choice, F.data.startswith("delch_"))
async def delete_channels_select(call: CallbackQuery):
    """
    Нажали на конкретный канал, удаляем его.
    """
    channel_id_str = call.data.split("_")[1]
    channel_id = int(channel_id_str)
    async with async_session() as session:
        ch = await session.get(Channel, channel_id)
        if ch:
            name = ch.channel_tag
            await session.delete(ch)
            await session.commit()
            await call.answer(f"Канал {name} удалён")
        else:
            await call.answer("Канал не найден или уже удалён.")
    await delete_channels_cb(call, None)

@router.callback_query(DeleteChannelsState.waiting_for_delete_choice, F.data == "delete_channels_done")
async def delete_channels_done_cb(call: CallbackQuery, state: FSMContext):
    """
    Кнопка 'Готово' при удалении каналов.
    """
    await state.clear()
    await call.message.edit_text("Удаление каналов завершено. Возвращаюсь в меню.")
    await settings_channels_cb(call)

@router.callback_query(F.data == "back_to_settings_main")
async def back_to_settings_main_cb(call: CallbackQuery):
    """
    Вернуться в главное меню настроек.
    """
    await call.message.edit_text("Главное меню настроек", reply_markup=get_settings_main())

# ----- Настройка фильтров / тем -----

@router.callback_query(F.data == "settings_filters")
async def settings_filters_cb(call: CallbackQuery):
    """
    Настроить фильтры. Если тем нет, показываем пустое; иначе – список.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User)
            .where(User.telegram_id == call.from_user.id)
            .options(selectinload(User.topics))
        )
        user = result.scalar()
        topics = user.topics

    if not topics:
        await call.message.edit_text("Список тем пуст", reply_markup=get_settings_filters_empty())
    else:
        topics_text = "\n".join([f" - {t.topic_name}" for t in topics])
        msg = (
            f"Вот список интересующих тебя тем:\n"
            f"{topics_text}\n"
            f"Всего тем: {len(topics)}"
        )
        await call.message.edit_text(msg, reply_markup=get_added_topics_inline(topics))

@router.callback_query(F.data == "add_topics")
async def add_topics_cb(call: CallbackQuery, state: FSMContext):
    """
    Добавление тем (через запятую).
    """
    text = (
        "Перечисли через запятую интересующие тебя темы, например:\n"
        "ИИ, маркетинг, автомобили, работа на удалёнке"
    )
    await call.message.edit_text(text, reply_markup=get_add_topics_inline())
    await state.set_state(AddTopicsState.waiting_for_topics_input)

@router.message(AddTopicsState.waiting_for_topics_input)
async def waiting_for_topics_input(message: Message, state: FSMContext):
    """
    Получаем строку с темами.
    """
    topics_text = message.text.strip()
    if not topics_text:
        await message.answer("Сообщение пустое, попробуй снова.")
        return

    raw_topics = [t.strip() for t in topics_text.split(",") if t.strip()]
    await state.update_data(new_topics=raw_topics)

    preview = "\n".join([f" - {t}" for t in raw_topics])
    await message.answer(
        f"Вот новые темы. Добавить в список?\n{preview}",
        reply_markup=get_topics_confirmation_inline()
    )
    await state.set_state(AddTopicsState.waiting_for_confirmation)

@router.callback_query(AddTopicsState.waiting_for_confirmation, F.data == "topics_confirm_yes")
async def topics_confirm_yes_cb(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    new_topics = data.get("new_topics", [])
    async with async_session() as session:
        result_user = await session.execute(
            select(User)
            .where(User.telegram_id == call.from_user.id)
            .options(selectinload(User.topics))
        )
        user = result_user.scalar()

        for t in new_topics:
            t_obj = Topic(user_id=user.id, topic_name=t)
            session.add(t_obj)
        await session.commit()

    await state.clear()
    await settings_filters_cb(call)

@router.callback_query(AddTopicsState.waiting_for_confirmation, F.data == "topics_confirm_no")
async def topics_confirm_no_cb(call: CallbackQuery, state: FSMContext):
    """
    Пользователь отказался, хочет ввести заново.
    """
    text = "Попробуй снова. Перечисли через запятую интересующие тебя темы."
    await call.message.edit_text(text, reply_markup=get_add_topics_inline())
    await state.set_state(AddTopicsState.waiting_for_topics_input)

@router.callback_query(AddTopicsState.waiting_for_confirmation, F.data == "topics_back_to_main")
async def topics_back_to_main_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await settings_filters_cb(call)

@router.callback_query(F.data == "add_topics_done")
async def add_topics_done_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await settings_filters_cb(call)

@router.callback_query(F.data == "add_topics_again")
async def add_topics_again_cb(call: CallbackQuery, state: FSMContext):
    text = "Перечисли через запятую интересующие тебя темы."
    await call.message.edit_text(text, reply_markup=get_add_topics_inline())
    await state.set_state(AddTopicsState.waiting_for_topics_input)

@router.callback_query(F.data == "edit_topics")
async def edit_topics_cb(call: CallbackQuery, state: FSMContext):
    """
    Удаление тем из списка.
    """
    async with async_session() as session:
        result_user = await session.execute(
            select(User)
            .where(User.telegram_id == call.from_user.id)
            .options(selectinload(User.topics))
        )
        user = result_user.scalar()
        topics = user.topics

    await call.message.edit_text(
        "Нажми на тему, чтобы удалить её:",
        reply_markup=get_edit_topics_inline(topics)
    )
    await state.set_state(EditTopicsState.waiting_for_delete_topic)

@router.callback_query(EditTopicsState.waiting_for_delete_topic, F.data.startswith("deltopic_"))
async def delete_topic_cb(call: CallbackQuery):
    topic_id = int(call.data.split("_")[1])
    async with async_session() as session:
        t_obj = await session.get(Topic, topic_id)
        if t_obj:
            await session.delete(t_obj)
            await session.commit()
            await call.answer(f"Тема {t_obj.topic_name} удалена.")
        else:
            await call.answer("Тема не найдена.")
    await edit_topics_cb(call, None)

@router.callback_query(EditTopicsState.waiting_for_delete_topic, F.data == "topics_edit_done")
async def topics_edit_done_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await settings_filters_cb(call)

# ----- Настройка времени рассылки -----

@router.callback_query(F.data == "settings_sending_time")
async def settings_sending_time_cb(call: CallbackQuery):
    """
    Показываем текущее время, кнопки «Отменить», «Задать другое время», «Назад».
    """
    async with async_session() as session:
        result_user = await session.execute(
            select(User).where(User.telegram_id == call.from_user.id)
        )
        user = result_user.scalar()
        current = user.schedule_time if user.schedule_time else "не задано"

        text = f"Время рассылки – {current}"
    await call.message.edit_text(text, reply_markup=get_settings_time_inline(current))

@router.callback_query(F.data == "cancel_schedule")
async def cancel_schedule_cb(call: CallbackQuery):
    """
    Отменяем рассылку (schedule_time = None).
    """
    async with async_session() as session:
        result_user = await session.execute(
            select(User).where(User.telegram_id == call.from_user.id)
        )
        user = result_user.scalar()
        user.schedule_time = None
        session.add(user)
        await session.commit()
    await call.message.edit_text("Время рассылки не задано", reply_markup=get_cancel_schedule_inline())

@router.callback_query(F.data == "set_schedule_time_again")
async def set_schedule_time_again_cb(call: CallbackQuery):
    """
    Просим ввести новое время.
    """
    await call.message.edit_text(
        "Во сколько ты хочешь получать саммари?\n"
        "Напиши время в формате ЧЧ:мм\n"
        "Например, 10:30"
    )

@router.message(F.text.regexp(r"^([0-1]\d|2[0-3]):([0-5]\d)$"))
async def process_new_schedule_time(message: Message, state: FSMContext):
    """
    Обрабатываем ввод нового времени. Допустим, HH:MM без учета offset.
    """
    new_time = message.text.strip()
    async with async_session() as session:
        res_user = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = res_user.scalar()
        if not user:
            await message.answer("Сначала /start.")
            return

        user.schedule_time = new_time
        session.add(user)
        await session.commit()

    await message.answer(f"Новое время рассылки установлено: {new_time}")

@router.message()
async def catch_other_messages(message: Message):
    """
    Если что-то другое написали, игнорируем или выводим подсказку.
    """
    # await message.answer("Нераспознанная команда. Используй /start, /summary, /settings и т.д.")
    pass
