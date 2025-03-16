from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder


new_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/new_room')],
        [KeyboardButton(text='/enter_room')]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder='Choose button'
)

start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/start')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

add_characters_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Добавить персонажей ➕')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

join_characters_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Смешать персонажей 🔁')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

close_room_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Закрыть комнату 🚪')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

set_position_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Выбрать напарника')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

play_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Игроки готовы')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

start_round_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Начать раунд')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)


exit_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/exit')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

character_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Следующий пресонаж', callback_data='next_character'
            )
        ]
    ]
)

new_keyboard_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Создать новую комнату', callback_data='new_room'
            )
        ],
        [
            InlineKeyboardButton(
                text='Войти в комнату', callback_data='enter_room'
            )
        ]
    ]
)


async def positions_inline(availible_positions):
    keyboard = InlineKeyboardBuilder()
    for position in availible_positions:
        keyboard.add(
            InlineKeyboardButton(
                text=str(position),
                callback_data=f'position_{position}'
            )
        )
    return keyboard.adjust(3).as_markup()
