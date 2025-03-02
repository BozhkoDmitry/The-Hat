from aiogram.types import (InlineKeyboardButton, InlineKeyboardMarkup,
                           KeyboardButton, ReplyKeyboardMarkup)
from aiogram.utils.keyboard import ReplyKeyboardBuilder

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
        [KeyboardButton(text='/start_adding_characters')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

join_characters_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/join_characters')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

close_room_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/close_room')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

set_position_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/set_position')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

play_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/play')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

start_round_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/start_round')],
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)

next_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/next')],
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

markup_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text='button1', callback_data='button1')]
    ]
)

cars = ['Tesla', 'bmw', 'Toyota']


async def inline_cars():
    keybord = ReplyKeyboardBuilder()
    for car in cars:
        keybord.add(KeyboardButton(text=car))
    return keybord.adjust(2).as_markup()
