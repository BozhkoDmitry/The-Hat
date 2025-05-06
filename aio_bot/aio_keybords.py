from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from texts import Commands, CallbackData

RESIZE = True
ONE_TIME = False

start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/' + Commands.START_COMMAND)],
    ],
    resize_keyboard=RESIZE,
    one_time_keyboard=ONE_TIME,
)

add_characters_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Commands.ADD_CHARACTERS_COMMAND)],
    ],
    resize_keyboard=RESIZE,
    one_time_keyboard=ONE_TIME,
)

join_characters_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Commands.JOIN_CHARACTERS_COMMAND)],
    ],
    resize_keyboard=RESIZE,
    one_time_keyboard=ONE_TIME,
)

close_room_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Commands.CLOSE_ROOM_COMMAND)],
    ],
    resize_keyboard=RESIZE,
    one_time_keyboard=ONE_TIME,
)


play_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Commands.PLAYERS_ARE_READY_COMMAND)],
    ],
    resize_keyboard=RESIZE,
    one_time_keyboard=ONE_TIME,
)

start_round_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=Commands.MAKE_THE_MOVE_COMMAND)],
    ],
    resize_keyboard=RESIZE,
    one_time_keyboard=ONE_TIME,
)


exit_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='/' + Commands.EXIT_COMMAND)],
    ],
    resize_keyboard=RESIZE,
    one_time_keyboard=ONE_TIME,
)

exit_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Выйти из прошлой игры', callback_data='exit'
            )
        ]
    ]
)

character_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Следующий пресонаж', callback_data=CallbackData.NEXT_CHARACTER_DATA
            )
        ]
    ]
)

new_keyboard_inline = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text='Создать новую комнату', callback_data=CallbackData.NEW_ROOM_DATA
            )
        ],
        [
            InlineKeyboardButton(
                text='Войти в комнату', callback_data=CallbackData.ENTER_ROOM_DATA
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
