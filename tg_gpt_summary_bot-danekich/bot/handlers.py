# bot/handlers.py

import logging
import asyncio
from datetime import datetime, timedelta, time
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from bot.states import UserStates, PaymentStates
from bot.keyboards import get_inline_main_keyboard, get_inline_keyboard
from data.storage import user_data
from services.aggregator import (
    app,
    get_messages_from_channel,
    restart_scheduler_for_user
)
from services.gpt_service import gpt

level_names = {
    0: "Без подписки",
    1: "1й уровень",
    2: "2й уровень"
}
logger = logging.getLogger(__name__)

# =========== Глобальные объекты (НЕ МЕНЯЛИ) ===========
# (В реальной практике лучше их импортировать из config.py)
API_TOKEN = '7900077305:AAGUvBf1cs76p9F1CmXrFq4yRl-1LTQQtGk'


# Бот, Dispatcher и т.д. желательно создавать в main.py,
# но здесь мы оставляем всё, как у вас в примере, чтоб было "точь-в-точь".


#
# Класс GPTAnswer вынесен в services/gpt_service.py
# Там же создаётся объект gpt = GPTAnswer()
#


#
# ============================
#  Хендлеры
# ============================
#
# Состояния для FSM

def initialize_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            'level': 0,
            'channels': [],
            'email': '',
            'tags': [],
            'settings': {
                'daily_summary': True,
                'notifications': True,
                'summary_time': time(9, 0)
            }
        }


def parse_time_input(time_str: str):
    if ':' in time_str:
        hours, minutes = map(int, time_str.split(':'))
    else:
        hours = int(time_str)
        minutes = 0

    if not (0 <= hours < 24 and 0 <= minutes < 60):
        raise ValueError

    return time(hours, minutes)


def register_handlers(dp):
    # Обработчик команды /payment
    @dp.message(Command('payment'))
    async def cmd_payment(message: types.Message):
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="Кнопка 1"), types.KeyboardButton(text="Кнопка 2")],
                [types.KeyboardButton(text="Кнопка 3")]
            ],
            resize_keyboard=True
        )

        await message.answer("Вы хотите оплатить подписку?", reply_markup=keyboard)
        await PaymentStates.CONFIRM_SUBSCRIPTION.set()

    # Обработчик выбора уровня подписки
    @dp.message(PaymentStates.CONFIRM_SUBSCRIPTION)
    async def process_subscription_level(message: types.Message, state: FSMContext):
        if message.text not in ["Уровень 1", "Уровень 2"]:
            await message.answer("Пожалуйста, выберите один из предложенных вариантов.")
            return

        await state.update_data(subscription_level=message.text)

        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(types.KeyboardButton("Да"))
        keyboard.add(types.KeyboardButton("Нет"))

        await message.answer(f"Вы выбрали {message.text}. Вы уверены?", reply_markup=keyboard)
        await PaymentStates.ENTER_EMAIL.set()

    # Обработчик подтверждения подписки
    @dp.message(PaymentStates.ENTER_EMAIL)
    async def process_confirmation(message: types.Message, state: FSMContext):
        if message.text.lower() == 'нет':
            await message.answer("Оплата отменена.", reply_markup=get_inline_main_keyboard()())
            await state.clear()
            return
        elif message.text.lower() != 'да':
            await message.answer("Пожалуйста, ответьте 'Да' или 'Нет'.")
            return

        await message.answer("Пожалуйста, введите вашу почту:")
        await PaymentStates.PAYMENT_LINK_SENT.set()  # Переходим в состояние PAYMENT_LINK_SENT

    # Обработчик ввода почты
    @dp.message(PaymentStates.PAYMENT_LINK_SENT)
    async def process_email(message: types.Message, state: FSMContext):
        email = message.text
        # Здесь можно добавить проверку валидности email

        data = await state.get_data()
        subscription_level = data.get('subscription_level', 'Неизвестный уровень')

        # Здесь должна быть логика генерации ссылки на оплату
        payment_link = "https://example.com/payment"  # Замените на реальную ссылку

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("Ссылка на оплату", url=payment_link))
        keyboard.add(types.InlineKeyboardButton("Закрыть сообщения об оплате", callback_data="close_payment"))

        await message.answer(
            f"На почту {email} пришла ссылка по которой надо оплатить подписку {subscription_level}.\n"
            f"Ссылка: {payment_link}",
            reply_markup=keyboard
        )

        await state.clear()

    # Обработчик кнопки "Закрыть сообщения об оплате"
    @dp.callback_query(lambda c: c.data == 'close_payment')
    async def process_close_payment(callback_query: types.CallbackQuery):
        await callback_query.message.delete()
        await callback_query.answer("Сообщения об оплате закрыты.")

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if user_id not in user_data:
            user_data[user_id] = {
                'level': 0,
                'channels': [],
                'email': '',
                'tags': [],
                'settings': {
                    'daily_summary': True,
                    'notifications': True,
                    'summary_time': time(9, 0)
                }
            }
            await message.answer(
                "Привет!\nЯ – бот summary_bot.\nЯ делаю саммари сообщений каналов, помогаю тебе быть в курсе и экономить время.",
                reply_markup=get_inline_keyboard(
                    ("Как это работает?", "how_it_works")
                )
            )
            await state.set_state(UserStates.waiting_for_first_action)
        else:
            await message.answer(
                f"Бот работает, приятной работы!\nУровень вашей подписки: {level_names[user_data[user_id]['level']]}",
                reply_markup=get_inline_main_keyboard())

        @dp.callback_query(F.data == "how_it_works")
        async def how_it_works(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.edit_text(
                "Как это работает?\n"
                "1. Ты скидываешь мне интересующие тебя каналы.\n"
                "2. Я делаю саммари - краткий пересказ сообщений из этих каналов.\n"
                "3. Раз в сутки я присылаю тебе это саммари.",
                reply_markup=get_inline_keyboard(
                    ("В чем польза?", "benefit")
                )
            )

        @dp.callback_query(F.data == "benefit")
        async def benefit(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.edit_text(
                "В чем польза?\n"
                "1. Ты будешь уверен в том, что ничего не пропустишь.\n"
                "2. Ты не будешь тратить время на неинтересные сообщения.\n"
                "3. Информация из всех каналов в одном месте.",
                reply_markup=get_inline_keyboard(
                    ("Как это выглядит?", "how_it_looks")
                )
            )

        @dp.callback_query(F.data == "how_it_looks")
        async def how_it_looks(callback: types.CallbackQuery, state: FSMContext):
            await callback.message.edit_text(
                "Лучше один раз увидеть, чем сто раз... хм... прочитать.\n"
                "Давай покажу тебе саммари новостного канала @vcnews (пример канала).",
                reply_markup=get_inline_keyboard(
                    ("Давай", "show_example")
                )
            )

        @dp.callback_query(F.data == "show_example")
        async def show_example(callback: types.CallbackQuery, state: FSMContext):
            chat = await app.get_chat("@vcnews")
            idc = chat.id
            messages = await get_messages_from_channel(idc, 2)
            messages_text = ''
            for i, msg in enumerate(messages):
                messages_text += f"Пост {i}: "+msg['text']+"\n"
            gpt_summary = await gpt.get_best_answer(messages_text[:4000])
            print(messages)
            print(messages_text)
            # Пример генерации саммари
            example_channel = "@vcnews"
            summary = "📰 *Пример саммари для канала @vcnews*\n\n"
            # summary += "1. Пример заголовка #1 - [Ссылка на оригинальное сообщение](https://t.me/vcnews/1)\n"
            # summary += "2. Пример заголовка #2 - [Ссылка на оригинальное сообщение](https://t.me/vcnews/2)\n"
            summary += gpt_summary
            await callback.message.edit_text(summary, reply_markup=get_inline_keyboard(
                ("Давай настроим бота", "setup_bot")
            ))

    @dp.callback_query(F.data == "setup_bot")
    async def setup_bot(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.edit_text(
            "Теперь настроим бота под тебя.\n"
            "Чтобы добавить канал, просто перешли мне сообщение из этого канала.\n"
            "Важно: канал должен быть открытым, иначе я не смогу на него подписаться.\n"
            "Давай, пересылай, я жду."
        )
        await state.set_state(UserStates.waiting_for_channel_start)

    @dp.message(UserStates.waiting_for_channel_start)
    async def add_channel_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        if message.forward_from_chat and message.forward_from_chat.type == 'channel':
            channel = {
                'id': message.forward_from_chat.id,
                'username': message.forward_from_chat.username,
                'title': message.forward_from_chat.title
            }
        else:
            await message.answer(
                "Не получилось добавить, канал – не найден. Перешли мне сообщение из открытого канала.")
            return

        if user_id in user_data:
            user_data[user_id]['channels'].append(channel)

        await message.answer(f"Результат:\n{channel['title']} добавлен в список каналов.")
        await message.answer(
            "Теперь давай настроим время рассылки.\nВо сколько ты хочешь получать саммари?\nНапиши удобное время в формате ЧЧ:мм")

        await state.set_state(UserStates.waiting_for_time)

    @dp.message(UserStates.waiting_for_time)
    async def set_summary_time(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        time_str = message.text.strip()

        try:
            if ':' in time_str:
                hours, minutes = map(int, time_str.split(':'))
            else:
                hours = int(time_str)
                minutes = 0

            if not (0 <= hours < 24 and 0 <= minutes < 60):
                raise ValueError

            user_data[user_id]['settings']['summary_time'] = time(hours, minutes)

            await message.answer(
                f"Ок. А сейчас у тебя который час?\nТоже пришли в формате ЧЧ:мм"
            )
            await state.set_state(UserStates.waiting_for_time_start)

        except (ValueError, AttributeError):
            await message.answer("Пожалуйста, введите время в правильном формате (например, 09:00 или 18:30):")

    @dp.message(UserStates.waiting_for_time_start)
    async def set_user_time(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        time_str = message.text.strip()
        try:
            if ':' in time_str:
                hours, minutes = map(int, time_str.split(':'))
            else:
                hours = int(time_str)
                minutes = 0

            if not (0 <= hours < 24 and 0 <= minutes < 60):
                raise ValueError

            await message.answer(
                "Время отправки ежедневного саммари успешно установлена!\n"
                f"Установленное время: {user_data[user_id]['settings']['summary_time']}",
                reply_markup=get_inline_main_keyboard()
            )
            await state.clear()

        except (ValueError, AttributeError):
            await message.answer("Пожалуйста, введите время в правильном формате (например, 09:00 или 18:30):")

    @dp.callback_query(F.data == "my_channels")
    async def show_user_channels(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        if user_id in user_data:
            if not user_data[user_id]['channels']:
                await callback.message.answer("Вы пока не добавили ни одного канала.",
                                              reply_markup=get_inline_main_keyboard())
                return
        else:
            user_data[user_id] = {
                'level': 0,
                'channels': [],
                'email': '',
                'tags': [],
                'settings': {
                    'daily_summary': True,
                    'notifications': True,
                    'summary_time': time(9, 0)
                }
            }
            await callback.message.answer("Вы пока не добавили ни одного канала.",
                                          reply_markup=get_inline_main_keyboard())
            return

        channels = user_data[user_id]['channels']
        response = "Ваши каналы:\n\n" + "\n".join(
            f"{i + 1}. {ch['title']} (@{ch['username']})"
            for i, ch in enumerate(channels[:3])
        )
        if len(channels) > 3:
            response += "\n\nВы можете отслеживать только 3 канала. Удалите один, чтобы добавить новый."
        await callback.message.answer(response, reply_markup=get_inline_main_keyboard())

    @dp.callback_query(F.data == "add_channels")
    async def add_channel_start_callback(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        if user_id in user_data:
            if len(user_data[user_id]['channels']) == 3 and user_data[user_id]['level'] < 1:
                await callback.message.answer(
                    "Вы уже отслеживаете максимальное количество каналов (3). Удалите один, чтобы добавить новый, либо приобретите подписку по команде /pay, что бы получить больше функций",
                    reply_markup=get_inline_main_keyboard()
                )
                return
            if len(user_data[user_id]['channels']) == 10 and user_data[user_id]['level'] < 2:
                await callback.message.answer(
                    "Вы уже отслеживаете максимальное количество каналов (10). Удалите один, чтобы добавить новый, либо повысьте уровень подписки по команде /pay, что бы получить большое количество каналов",
                    reply_markup=get_inline_main_keyboard()
                )
                return
            if len(user_data[user_id]['channels']) >= 50 and user_data[user_id]['level'] < 3:
                await callback.message.answer(
                    "Вы уже отслеживаете максимальное количество каналов (50). Удалите один, чтобы добавить новый.",
                    reply_markup=get_inline_main_keyboard()
                )
                return
        else:
            user_data[user_id] = {
                'level': 0,
                'channels': [],
                'email': '',
                'tags': [],
                'settings': {
                    'daily_summary': True,
                    'notifications': True,
                    'summary_time': time(9, 0)
                }
            }
        await state.set_state(UserStates.waiting_for_channel)
        await callback.message.answer(
            "Пришлите мне username канала (например, @channel_name) или перешлите любое сообщение из канала.",
            reply_markup=get_inline_main_keyboard()
        )

    @dp.message(UserStates.waiting_for_channel)
    async def add_channel_finish(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        # Пересланное сообщение
        if message.forward_from_chat and message.forward_from_chat.type == 'channel':
            channel = {
                'id': message.forward_from_chat.id,
                'username': message.forward_from_chat.username,
                'title': message.forward_from_chat.title
            }
        elif message.text and message.text.startswith('@'):
            channel = {
                'id': None,
                'username': message.text[1:].lower(),
                'title': message.text
            }
        else:
            await message.answer("Пожалуйста, пришлите username канала или перешлите сообщение из канала.")
            return

        if user_id in user_data:
            if any(c['username'] == channel['username'] for c in user_data[user_id]['channels']):
                await message.answer("Вы уже подписаны на этот канал.", reply_markup=get_inline_main_keyboard())
                await state.clear()
                return

        user_data[user_id]['channels'].append(channel)
        await state.clear()

        await message.answer(
            f"Канал {channel['title']} успешно добавлен!\n"
            "Хотите добавить теги для этого канала?",
            reply_markup=get_inline_main_keyboard()
        )

    def kbrd():
        builder = InlineKeyboardBuilder()
        builder.button(text="Добавить теги", callback_data="add_tags")
        builder.button(text="Удалить теги", callback_data="delete_tags")
        builder.button(text="Назад", callback_data="back")

        builder.adjust(3)
        return builder.as_markup()

    @dp.callback_query(F.data == "delete_tags")
    async def delete_tags(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        initialize_user_data(user_id)

        if not user_data[user_id]['tags']:
            await callback.answer("У вас нет тегов для удаления", show_alert=True)
            return

        # Создаем клавиатуру с тегами для удаления
        builder = InlineKeyboardBuilder()
        for tag in user_data[user_id]['tags']:
            builder.button(text=tag, callback_data=f"remove_tag_{tag}")

        builder.button(text="Назад", callback_data="back_to_tags")
        builder.adjust(1)  # По одному тегу в строке

        await callback.message.edit_text(
            "Выберите тег, который хотите удалить:",
            reply_markup=builder.as_markup()
        )
        await state.set_state(UserStates.waiting_for_tag_to_delete)

    @dp.callback_query(F.data.startswith("remove_tag_"), UserStates.waiting_for_tag_to_delete)
    async def process_tag_removal(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        tag_to_remove = callback.data.replace("remove_tag_", "")
        if not user_data[user_id]['tags']:
            await callback.answer("У вас нет тегов для удаления", reply_markup=get_inline_main_keyboard())
            return
        await state.set_state(UserStates.waiting_for_tag_to_delete)
        if tag_to_remove in user_data[user_id]['tags']:
            user_data[user_id]['tags'].remove(tag_to_remove)
            # Создаем клавиатуру с тегами для удаления
            builder = InlineKeyboardBuilder()
            if user_data[user_id]['tags']:
                for tag in user_data[user_id]['tags']:
                    builder.button(text=tag, callback_data=f"remove_tag_{tag}")
                builder.button(text="Назад", callback_data="back_to_tags")
                builder.adjust(1)  # По одному тегу в строке
                await callback.message.edit_text(
                    f"Тег '{tag_to_remove}' успешно удален!\nВыберите тег, который хотите удалить:",
                    reply_markup=builder.as_markup(
                ))
            else:
                await callback.message.edit_text(
                    f"Тег '{tag_to_remove}' успешно удален!\nВыберите тег, который хотите удалить:",
                    reply_markup=builder.as_markup(
                ))
        else:
            await callback.answer("Этот тег уже был удален", show_alert=True)
        await state.clear()


    @dp.callback_query(F.data == "back_to_tags", UserStates.waiting_for_tag_to_delete)
    async def back_to_tags_menu(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await show_user_tags(callback)


    @dp.callback_query(F.data == "my_tags")
    async def show_user_tags(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        initialize_user_data(user_id)

        tags = user_data[user_id]['tags']
        if not tags:
            await callback.message.answer("Вы пока не добавили ни одного тега.\nХотите добавить?",
                                          reply_markup=kbrd())
        else:
            await callback.message.answer(f"Ваши теги для саммари:\n\n#{' #'.join(tags)}\nХотите добавить ещё?",
                                          reply_markup=kbrd())

    @dp.callback_query(F.data == "add_tags")
    async def add_tags(callback: types.CallbackQuery, state: FSMContext):
        await callback.message.answer(
            "Отправьте теги в любом формате как вы хотите, можете черз запятую, можете через пробел, либо рассказать что вас интересует.")
        await state.set_state(UserStates.waiting_for_tags)

    @dp.message(UserStates.waiting_for_tags)
    async def wait_for_tags(message: types.Message):
        user_id = message.from_user.id
        tags = user_data[user_id]['tags']
        user_data[user_id]['tags'].append(message.text)
        await message.answer(f"Ваши теги для саммари:\n\n#{' #'.join(tags)}\nХотите добавить ещё?",
                                          reply_markup=kbrd())

    @dp.callback_query(F.data == "back")
    async def get_back_to_tags(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.answer("Вы вышли из тегов", reply_markup=get_inline_main_keyboard())

    @dp.callback_query(F.data == "get_summary")
    async def get_summary(callback: types.CallbackQuery):
        user_id = callback.from_user.id
        initialize_user_data(user_id)

        if not user_data[user_id]['channels']:
            await callback.message.answer("Вы пока не добавили ни одного канала.")
            return

        await callback.message.answer("Собираю последние новости...")
        summary = "📰 *Сводка новостей за последние 24 часа*\n\n"

        for channel in user_data[user_id]['channels'][:3]:
            try:
                messages = await get_messages_from_channel(channel['id'], 2)
                if messages:
                    messages_text = "\n".join([msg.text or "" for msg in messages if hasattr(msg, 'text') and msg.text])
                    if messages_text:
                        gpt_summary = await gpt.get_best_answer(messages_text[:4000])
                        summary += f"*{channel['title']}* (@{channel['username']})\n{gpt_summary or 'Не удалось сгенерировать сводку'}\n\n"
                    else:
                        summary += f"*{channel['title']}* (@{channel['username']})\nНет текстовых сообщений для анализа\n\n"
                else:
                    summary += f"*{channel['title']}* (@{channel['username']})\nНет новых сообщений\n\n"
            except Exception as e:
                logging.error(f"Error processing channel {channel['title']}: {e}")
                summary += f"*{channel['title']}* (@{channel['username']})\nОшибка при обработке канала\n\n"

        await callback.message.answer(summary, reply_markup=get_inline_main_keyboard())

    @dp.callback_query(F.data == "delete_channel")
    async def get_delete_channels(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        initialize_user_data(user_id)

        if not user_data[user_id]['channels']:
            await callback.message.answer("У вас нет добавленных каналов!")
            return

        builder = InlineKeyboardBuilder()
        for channel in user_data[user_id]['channels']:
            builder.button(text=channel['title'], callback_data=f"delete_{channel['id']}")
        builder.button(text="Назад", callback_data="cancel_delete")
        builder.adjust(1)

        await callback.message.answer("Выберите канал, который вы хотите удалить:", reply_markup=builder.as_markup())
        await state.set_state(UserStates.waiting_for_delete)

    @dp.callback_query(F.data.startswith("cancel_delete"), UserStates.waiting_for_delete)
    async def delete_channel_cancel(callback: types.CallbackQuery, state: FSMContext):
        await state.clear()
        await callback.message.answer("Отмена удаления", reply_markup=get_inline_main_keyboard())

    @dp.callback_query(F.data.startswith("delete_"), UserStates.waiting_for_delete)
    async def delete_channel_finish(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        channel_id = int(callback.data.split("_")[1])
        initialize_user_data(user_id)

        channel_to_delete = next((c for c in user_data[user_id]['channels'] if c['id'] == channel_id), None)
        if channel_to_delete is None:
            await callback.message.answer("Произошла ошибка: канал не найден.")
        else:
            user_data[user_id]['channels'].remove(channel_to_delete)
            await callback.message.answer(f"Канал {channel_to_delete['title']} был успешно удален из вашего списка.",
                                          reply_markup=get_inline_main_keyboard())
        await state.clear()
        await callback.answer()

    @dp.callback_query(F.data == "set_time")
    async def set_summary_time_start(callback: types.CallbackQuery, state: FSMContext):
        user_id = callback.from_user.id
        initialize_user_data(user_id)

        await state.set_state(UserStates.waiting_for_time)
        await callback.message.answer(
            "Введите время, когда вы хотите получать ежедневную сводку (например, 09:00 или 18:30):",
            reply_markup=types.ReplyKeyboardRemove())

    @dp.message(UserStates.waiting_for_time)
    async def set_summary_time_finish(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        try:
            user_time = parse_time_input(message.text.strip())
            user_data[user_id]['settings']['summary_time'] = user_time

            await message.answer(f"Время ежедневной сводки установлено на {user_time.strftime('%H:%M')}",
                                 reply_markup=get_inline_main_keyboard())
            await state.clear()
            await restart_scheduler_for_user(user_id)
        except ValueError:
            await message.answer("Пожалуйста, введите время в правильном формате (например, 09:00 или 18:30):")

    @dp.message(UserStates.waiting_for_time_start)
    async def set_summary_time_finish_again(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        try:
            user_time = parse_time_input(message.text.strip())
            user_data[user_id]['settings']['summary_time'] = user_time

            await message.answer(f"Время ежедневной сводки установлено на {user_time.strftime('%H:%M')}",
                                 reply_markup=get_inline_main_keyboard())
            await state.clear()
            await restart_scheduler_for_user(user_id)
            await message.answer("Ок. А сейчас у тебя который час? Тоже пришли в формате ЧЧ:мм")
        except ValueError:
            await message.answer("Пожалуйста, введите время в правильном формате (например, 09:00 или 18:30):")

    @dp.message(UserStates.waiting_for_channel_start)
    async def add_channel_finish_start(message: types.Message, state: FSMContext):
        user_id = message.from_user.id
        initialize_user_data(user_id)

        if message.forward_from_chat and message.forward_from_chat.type == 'channel':
            channel = {
                'id': message.forward_from_chat.id,
                'username': message.forward_from_chat.username,
                'title': message.forward_from_chat.title
            }
        elif message.text and message.text.startswith('@'):
            channel = {
                'id': None,
                'username': message.text[1:].lower(),
                'title': message.text
            }
        else:
            await message.answer(
                "Пожалуйста, пришлите username канала (например, @channel_name) или перешлите сообщение из канала.")
            return

        if any(c['username'] == channel['username'] for c in user_data[user_id]['channels']):
            await message.answer("Вы уже подписаны на этот канал.", reply_markup=get_inline_main_keyboard())
        else:
            user_data[user_id]['channels'].append(channel)
            await message.answer(f"Результат: \n{channel['title']} успешно добавлен!\n")
            await message.answer("Теперь давай настроим время рассылки.\nВо сколько ты хочешь получать саммари?\n"
                                 "Напиши удобное время в формате ЧЧ:мм\nНапример, 10:30")
            await state.set_state(UserStates.waiting_for_time_start)

        await state.clear()
