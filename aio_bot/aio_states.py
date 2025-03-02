from aiogram.fsm.state import StatesGroup, State


class Reg(StatesGroup):
    name = State()
    number_of_characters = State()
    room_id = State()
    character = State()
    position = State()
    round_duration = State()
