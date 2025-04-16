from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

def get_start_inline_1():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Как это работает?", callback_data="how_it_works"))
    return builder.as_markup()

def get_start_inline_2():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="В чем польза?", callback_data="benefits"))
    return builder.as_markup()

def get_start_inline_3():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Как это выглядит?", callback_data="example_view"))
    return builder.as_markup()

def get_start_inline_4():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Давай", callback_data="show_example_summary"))
    return builder.as_markup()

def get_finish_setup_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Завершить", callback_data="finish_setup"))
    return builder.as_markup()

def get_settings_main():
    builder = InlineKeyboardBuilder()
    builder.button(text="Настроить каналы", callback_data="settings_channels")
    builder.button(text="Настроить фильтры", callback_data="settings_filters")
    builder.button(text="Настроить время рассылки", callback_data="settings_sending_time")
    builder.button(text="Закрыть", callback_data="close_settings")
    builder.adjust(1)
    return builder.as_markup()

def get_settings_channels():
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить каналы", callback_data="add_channels")
    builder.button(text="Удалить каналы", callback_data="delete_channels")
    builder.button(text="< Назад", callback_data="back_to_settings_main")
    builder.adjust(1)
    return builder.as_markup()

def get_add_channels_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Готово", callback_data="add_channels_done"))
    return builder.as_markup()

def get_delete_channels_inline(channel_list):
    builder = InlineKeyboardBuilder()
    for ch in channel_list:
        builder.row(InlineKeyboardButton(text=ch.channel_tag, callback_data=f"delch_{ch.id}"))
    builder.row(InlineKeyboardButton(text="Готово", callback_data="delete_channels_done"))
    return builder.as_markup()

def get_settings_filters_empty():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Добавить темы", callback_data="add_topics"))
    builder.row(InlineKeyboardButton(text="< Назад", callback_data="back_to_settings_main"))
    return builder.as_markup()

def get_add_topics_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Готово", callback_data="add_topics_done"))
    return builder.as_markup()

def get_topics_confirmation_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, добавить", callback_data="topics_confirm_yes")
    builder.button(text="Нет, попробовать еще раз", callback_data="topics_confirm_no")
    builder.button(text="< Назад", callback_data="topics_back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_added_topics_inline(topics):
    builder = InlineKeyboardBuilder()
    builder.button(text="Добавить темы", callback_data="add_topics_again")
    builder.button(text="Редактировать список", callback_data="edit_topics")
    builder.button(text="< Назад", callback_data="back_to_settings_main")
    builder.adjust(1)
    return builder.as_markup()

def get_edit_topics_inline(topics):
    builder = InlineKeyboardBuilder()
    for t in topics:
        builder.row(InlineKeyboardButton(text=t.topic_name, callback_data=f"deltopic_{t.id}"))
    builder.row(InlineKeyboardButton(text="Готово", callback_data="topics_edit_done"))
    return builder.as_markup()

def get_settings_time_inline(current_time):
    builder = InlineKeyboardBuilder()
    builder.button(text="Отменить рассылку", callback_data="cancel_schedule")
    builder.button(text="Задать другое время", callback_data="set_schedule_time_again")
    builder.button(text="< Назад", callback_data="back_to_settings_main")
    builder.adjust(1)
    return builder.as_markup()

def get_cancel_schedule_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="Задать другое время", callback_data="set_schedule_time_again")
    builder.button(text="< Назад", callback_data="back_to_settings_main")
    builder.adjust(1)
    return builder.as_markup()

def get_payments_main():
    builder = InlineKeyboardBuilder()
    builder.button(text="Стандартный", callback_data="pay_standard_select")
    builder.button(text="PRO", callback_data="pay_pro_select")
    builder.button(text="Закрыть", callback_data="close_payment")
    builder.adjust(1)
    return builder.as_markup()

def get_chat_cancel_inline():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Отмена", callback_data="chat_cancel"))
    return builder.as_markup()

def get_payment_email_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data="back_to_payments_main")
    builder.adjust(1)
    return builder.as_markup()

def get_payment_after_email_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="Оплатить", callback_data="pay_invoice_standard")
    builder.button(text="Заменить почту", callback_data="pay_email_replace_standard")
    builder.button(text="Назад", callback_data="back_to_payments_main")
    builder.adjust(1)
    return builder.as_markup()

def get_retry_inline():
    builder = InlineKeyboardBuilder()
    builder.button(text="Повторить", callback_data="retry_summary")
    builder.button(text="Сделать укороченную версию", callback_data="short_summary")
    return builder.as_markup()
