from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_inline_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Мои каналы", callback_data="my_channels")
    builder.button(text="Добавить канал", callback_data="add_channels")
    builder.button(text="Удалить канал", callback_data="delete_channel")
    builder.button(text="Мои теги", callback_data="my_tags")
    builder.button(text="Получить сводку", callback_data="get_summary")
    builder.button(text="Настроить время сводки", callback_data="set_time")
    builder.adjust(2)
    return builder.as_markup()

def get_inline_keyboard(*args):
    """
    Универсальный генератор инлайн-клавиатуры из пар (text, callback_data)
    """
    builder = InlineKeyboardBuilder()
    for text, callback_data in args:
        builder.button(text=text, callback_data=callback_data)
    builder.adjust(2)  # например, 2 кнопки в ряд
    return builder.as_markup()
