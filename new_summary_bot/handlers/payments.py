from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from datetime import datetime, timedelta

from config import PAYMENT_PROVIDER_TOKEN, STANDARD_PRICE, PRO_PRICE
from inline import (
    get_payments_main,
    get_payment_email_inline,
    get_payment_after_email_inline
)
from states import PaymentEmailState
from database import async_session
from models import User

router = Router()

@router.message(Command("payments"))
async def cmd_payments(message: Message):
    """
    Команда /payments: Выдаём меню выбора тарифа.
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar()
        if not user:
            await message.answer("Сначала /start.")
            return

        if user.tariff == "free":
            text = (
                "Сейчас ты на бесплатном тарифе.\n"
                "Тебе доступно саммари с 3 каналов.\n"
                "Посмотри, что есть на других тарифах."
            )
        elif user.tariff == "standard":
            text = "У тебя тариф Standard (до 20 каналов). Хочешь перейти на PRO?"
        elif user.tariff == "pro":
            text = "У тебя уже тариф PRO!"
        else:
            text = "Сейчас ты на бесплатном тарифе. Посмотри, что есть на других тарифах."

    await message.answer(text, reply_markup=get_payments_main())

@router.callback_query(F.data == "close_payment")
async def close_payment_cb(call: CallbackQuery):
    """
    Закрыть меню оплат.
    """
    await call.message.delete()

@router.callback_query(F.data == "back_to_payments_main")
async def back_to_payments_main_cb(call: CallbackQuery):
    """
    Вернуться в главное меню оплат (выбор тарифа).
    """
    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == call.from_user.id)
        )
        user = result.scalar()
        if user.tariff == "free":
            text = (
                "Сейчас ты на бесплатном тарифе.\n"
                "Тебе доступно саммари с 3 каналов.\n"
                "Посмотри, что есть на других тарифах."
            )
        elif user.tariff == "standard":
            text = "У тебя тариф Standard (до 20 каналов). Хочешь перейти на PRO?"
        elif user.tariff == "pro":
            text = "У тебя уже тариф PRO!"
        else:
            text = "Посмотри, что есть на других тарифах."

    await call.message.edit_text(text, reply_markup=get_payments_main())

@router.callback_query(F.data == "pay_standard_select")
async def pay_standard_select_cb(call: CallbackQuery, state: FSMContext):
    """
    Пользователь выбрал купить Standard-тариф.
    """
    text = (
        "Укажи свою почту для отправки чека.\n"
        "Присылая почту, ты соглашаешься с политикой конфиденциальности."
    )
    await call.message.edit_text(text, reply_markup=get_payment_email_inline())
    await state.set_state(PaymentEmailState.waiting_for_email)

@router.callback_query(F.data == "pay_pro_select")
async def pay_pro_select_cb(call: CallbackQuery, state: FSMContext):
    """
    Пользователь выбрал купить PRO-тариф.
    Для упрощения – сразу выставляем счёт (можно делать аналогично Standard, если нужна почта).
    """
    title = "Подписка PRO"
    description = (
        "Тариф PRO даёт возможность обрабатывать до 40 каналов. "
        "Ежемесячная оплата, можно отменить в любой момент."
    )
    prices = [
        LabeledPrice(label="PRO (1 мес.)", amount=PRO_PRICE * 100)
    ]
    payload_data = "pro_sub"

    await call.message.edit_text("Сформирован счёт. Сейчас появится кнопка 'Pay'.")
    await call.message.answer_invoice(
        title=title,
        description=description,
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
        payload=payload_data,
        start_parameter="start-pro"
    )

@router.message(PaymentEmailState.waiting_for_email)
async def user_email_input_standard(message: Message, state: FSMContext):
    """
    Получаем почту от пользователя для тарифа Standard.
    """
    email_text = message.text
    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar()
        # user.email = email_text  # для хранения
        session.add(user)
        await session.commit()

    # После ввода почты – предлагаем оплату.
    await message.answer(
        f"Тариф Standard: {STANDARD_PRICE} руб/мес.\n"
        f"Почта для чека: {email_text}\n"
        "Готов перейти к оплате?",
        reply_markup=get_payment_after_email_inline()
    )
    await state.clear()

@router.callback_query(F.data == "pay_email_replace_standard")
async def pay_email_replace_standard_cb(call: CallbackQuery, state: FSMContext):
    text = (
        "Укажи новую почту.\n"
        "Присылая почту, ты соглашаешься с политикой конфиденциальности."
    )
    await call.message.edit_text(text)
    await state.set_state(PaymentEmailState.waiting_for_email)

@router.callback_query(F.data == "pay_invoice_standard")
async def pay_invoice_standard_cb(call: CallbackQuery):
    """
    Выставляем инвойс на Standard.
    """
    title = "Подписка Standard"
    description = (
        "Тариф Standard даёт возможность обрабатывать до 20 каналов. "
        "Ежемесячная оплата, можно отменить в любой момент."
    )
    prices = [
        LabeledPrice(label="Standard (1 мес.)", amount=STANDARD_PRICE * 100)
    ]
    payload_data = "standard_sub"

    await call.message.edit_text("Сформирован счёт. Сейчас появится кнопка 'Pay'.")
    await call.message.answer_invoice(
        title=title,
        description=description,
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="RUB",
        prices=prices,
        payload=payload_data,
        start_parameter="start-standard"
    )

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_q: PreCheckoutQuery):
    """
    Обрабатываем предчек. Если payload не наш, отказываем.
    """
    if pre_checkout_q.invoice_payload not in ["standard_sub", "pro_sub"]:
        await pre_checkout_q.answer(ok=False, error_message="Неизвестный тип платежа.")
        return
    await pre_checkout_q.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_message(message: Message):
    """
    После успешной оплаты. Меняем тариф в БД и уведомляем пользователя.
    """
    payment_info = message.successful_payment.to_python()
    payload = payment_info["invoice_payload"]
    chat_id = message.chat.id

    new_tariff = "free"
    if payload == "standard_sub":
        new_tariff = "standard"
    elif payload == "pro_sub":
        new_tariff = "pro"

    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == chat_id))
        user = result.scalar()
        if user:
            user.tariff = new_tariff
            user.subscription_until = datetime.utcnow() + timedelta(days=30)
            session.add(user)
            await session.commit()

    await message.answer(
        f"Оплата прошла успешно!\n"
        f"Теперь у тебя тариф: {new_tariff}.\n"
        "Спасибо за оплату!"
    )
