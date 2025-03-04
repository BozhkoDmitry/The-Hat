import asyncio
import os

import aio_keybords as kb
from aio_states import Reg
from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from dotenv import load_dotenv
from game_classes import Player, Room

load_dotenv()

TOKEN = os.getenv('TOKEN')

bot = Bot(token=TOKEN)

router = Router()


async def send_message(chat_id, text, reply_markup=None):
    await bot.send_message(
        chat_id=chat_id, text=text, reply_markup=reply_markup
    )


async def end_round(room: Room, player: Player, times_up=False):
    guesser: Player = room.get_next_player(player)

    if not times_up:
        for person in room.players:
            person: Player
            await send_message(
                person.id_number,
                text=person.Messages.ALL_CHARACTERS_GUESSED
            )
            await send_message(
                person.id_number,
                text=f'Закончился раунд № {room.round}'
            )
            await send_message(
                person.id_number,
                text=(
                    'Общее количество ваших очков: '
                    f'{person.score}'
                )
            )
        room.next_round()
        if room.last_round():
            await game_over(room=room)
            return None

    await send_message(
        player.id_number,
        reply_markup=ReplyKeyboardRemove(),
        text=(
            'Количество заработаных очков в этот раз: '
            f'{player.round_score}'
        )
    )

    if player != guesser:
        await send_message(
            guesser.id_number,
            text=(
                'Количество заработаных очков в этот раз: '
                f'{player.round_score}'
            )
        )

    await send_message(
        guesser.id_number,
        reply_markup=kb.start_round_keyboard,
        text=guesser.Messages.YOUR_MOVE
    )
    room.end_round(player)


async def game_over(room: Room):
    for player in room.players:
        player: Player
        await send_message(
            player.id_number,
            text=player.Messages.GAME_OVER
        )
        await send_message(
            player.id_number,
            reply_markup=kb.start_keyboard,
            text=(
                'Если хотите сыграть ещё раз введите '
                'команду "/start"'
            )
        )
        del player.PLAYERS[player.id_number]
        del player

    del room.ROOMS[room.id_number]
    del room


async def get_id(message: Message):
    return message.from_user.id


async def get_player_by(message: Message = None, player_id=False):
    if player_id:
        return Player.PLAYERS.get(player_id)
    return Player.PLAYERS.get(await get_id(message))


async def get_room_by(message: Message = None, room_id=False):
    if not room_id:
        player: Player = await get_player_by(message)
        return Room.ROOMS.get(player.room_id) if player else None
    return Room.ROOMS.get(room_id)


async def create_player(message: Message):
    if not await get_player_by(message):
        player = Player(await get_id(message))
        player.PLAYERS[player.id_number] = player
        return player
    return None


async def remove_player(message: Message):
    player: Player = await get_player_by(message)
    room: Room = await get_room_by(message)
    if player:
        if player.is_playing:
            await message.answer(
                text=player.Messages.FINISH_ROUND
            )
            return None
        if room:
            if player.is_gamemaster:
                if not room.number_of_characters:
                    await message.answer(
                        text=(
                            'Вы не можете покинуть комнату пока не установите '
                            'количество загадываемых персонажей'
                        )
                    )
                    return None

                if room.open:
                    await message.answer(
                        text=(
                            'Вы не можете покинуть комнату пока не '
                            'закроете её '
                        )
                    )
                    return None
            room.players.remove(player)

        await message.answer(
            reply_markup=kb.start_keyboard,
            text=player.Messages.GAME_EXITED
        )
        del player.PLAYERS[player.id_number]
        del player
        return None


async def create_room(gamemaster: Player):
    room = Room(gamemaster.id_number)
    gamemaster.room_id = room.id_number
    gamemaster.is_gamemaster = True
    room.players.append(gamemaster)
    room.ROOMS[room.id_number] = room
    return room


@router.message(CommandStart())
async def start(message: Message):
    player: Player = await get_player_by(message)
    room: Room = await get_room_by(message)

    if not (player and room):
        await message.answer(
            text=Player.Messages.CREATE_OR_ENTER_ROOM,
            reply_markup=kb.new_keyboard
        )
        return None

    await message.answer(
        text=Player.Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )


@router.message(Command('enter_room'))
async def enter_room(message: Message, state: FSMContext):
    player: Player = await create_player(message)
    if player:
        await state.set_state(Reg.name)
        await message.answer(
            text=player.Messages.ENTER_YOUR_NAME
        )
        return None

    await message.answer(
        text=Player.Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )


@router.message(Reg.name)
async def add_name(message: Message, state: FSMContext):
    await state.clear()
    player: Player = await get_player_by(message)

    if not message.text:
        await message.answer(
            text='Пожалуйтса запишите своё имя текстом'
        )
        await state.set_state(Reg.name)
        return None

    if message.text == '/exit':
        await remove_player(message)
        return None

    player.name = message.text

    if player.is_gamemaster:
        await message.answer(
            text=player.Messages.ENTER_NUMBER_OF_CHARACTERS
        )
        await state.set_state(Reg.number_of_characters)
        return None

    await message.answer(
        text=player.Messages.ENTER_ROOM_ID
    )
    await state.set_state(Reg.room_id)


@router.message(Reg.room_id)
async def add_room_id(message: Message, state: FSMContext):
    await state.clear()
    player: Player = await get_player_by(message)
    result = player.check_room_id(message)

    if message.text == '/exit':
        await remove_player(message)
        return None

    if result == player.Messages.OK:
        room_id = int(message.text)
        room: Room = await get_room_by(room_id=room_id)

        if not room.open:
            await message.answer(
                text=player.Messages.ROOM_IS_CLOSED
            )
            await state.set_state(Reg.room_id)
            return None

        if player in room.players:
            await message.answer(
                text=player.Messages.ROOM_ENTERED
            )
            return None

        room.players.append(player)
        player.room_id = room_id

        await message.answer(
            text=player.Messages.ROOM_ENTERED
        )
        await send_message(
            chat_id=room.gamemaster,
            text=f'Игрок {player.name} вошёл в комнату'
        )
        return None

    await message.answer(
        text=result
    )
    if result != player.Messages.PLAYER_IS_IMPOSTOR:
        await state.set_state(Reg.room_id)


@router.message(Command('new_room'))
async def new_room(message: Message, state: FSMContext):
    await state.clear()
    gamemaster: Player = await create_player(message)
    if gamemaster:
        await create_room(gamemaster)
        await message.answer(
            text=gamemaster.Messages.ENTER_YOUR_NAME,
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(Reg.name)
        return None

    await message.answer(
        text=Player.Messages.EXIT_PREVIOUS_GAME,
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(Reg.number_of_characters)
async def add_number_of_charaters(message: Message, state: FSMContext):
    await state.clear()
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)
    result = player.check_number_of_characters(message)

    if message.text == '/exit':
        await remove_player(message)
        return None

    if result == player.Messages.OK:
        room.number_of_characters = int(message.text)
        await message.answer(
            text=player.Messages.CLOSE_ROOM
        )
        await message.answer(
            reply_markup=kb.close_room_keyboard,
            text=f'Номер вашей комнаты: {room.id_number}. '
        )
        return None

    await message.answer(
        text=result
    )
    if result != player.Messages.PLAYER_IS_IMPOSTOR:
        await state.set_state(Reg.number_of_characters)


@router.message(Command('close_room'))
async def close_room(message: Message, state: FSMContext):
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)

    if not room or not player:
        if not player:
            await message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if not player.is_gamemaster:
        await message.answer(
                text=player.Messages.PLAYER_IS_IMPOSTOR,
                reply_markup=ReplyKeyboardRemove()
        )
        return None

    if not room.open:
        await message.answer(
                text=player.Messages.ROOM_IS_CLOSED,
                reply_markup=ReplyKeyboardRemove()
        )
        return None

    room.close()
    for player in room.players:
        await send_message(
            chat_id=player.id_number,
            text=player.Messages.ADD_CHARACTERS,
            reply_markup=kb.add_characters_keyboard
        )
        if not player.is_gamemaster:
            await send_message(
                player.id_number,
                text=(
                    'Количесво персонажей на эту игру - '
                    f'{room.number_of_characters}.'
                )
            )


@router.message(Command('start_adding_characters'))
async def start_adding_characters(message: Message, state: FSMContext):
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)

    if not room or not player:
        if not player:
            await message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if room.characters_united:
        await message.answer(
            text=player.Messages.WAIT_FOR_OTHER_PLAYERS
        )
        return None

    if room.open:
        await message.answer(
            text=(
                'Добавлять персонажей можно будет когда комната закроется'
            )
        )

    if not player.characters:
        await message.answer(
            reply_markup=ReplyKeyboardRemove(),
            text=player.Messages.ENTER_FIRST_CHARACTER
        )
        await state.set_state(Reg.character)
        return None


@router.message(Reg.character)
async def add_character(message: Message, state: FSMContext):
    await state.clear()
    player: Player = await get_player_by(message)

    if not message.text:
        await message.answer(
            text='Персонажа можно записать только текстом'
        )
        await state.set_state(Reg.character)
        return None

    if message.text == '/exit':
        await remove_player(message)
        return None

    character = message.text
    if not player.can_add_more_characters(await get_room_by(message)):
        room: Room = await get_room_by(message)
        player.characters.append(character)
        room.unready_players.remove(player)
        await message.answer(
            reply_markup=ReplyKeyboardRemove(),
            text=(
                'Вы добавили всех персонажей: '
                f"{', '.join(player.characters)}"
            )
        )
        if player.is_gamemaster:
            await message.answer(
                text=player.Messages.JOIN_CHARACTERS
            )
        if room.player_is_last():
            await send_message(
                room.gamemaster,
                text='',
                reply_markup=kb.join_characters_keyboard,
            )
        return None

    player.characters.append(character)
    await message.answer(
        reply_markup=ReplyKeyboardRemove(),
        text=(
            'Ведите персонажа № '
            f' {player.next_character_number()}'
        )
    )
    await state.set_state(Reg.character)


@router.message(Command('join_characters'))
async def join_characters(message: Message, state: FSMContext):
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)

    if not room or not player:
        if not player:
            await message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if not player.is_gamemaster:
        await message.answer(
                text=player.Messages.PLAYER_IS_IMPOSTOR,
                reply_markup=ReplyKeyboardRemove()
        )
        return None

    if room.characters_united:
        await message.answer(
            text=player.Messages.WAIT_FOR_OTHER_PLAYERS
        )
        return None

    room.characters_united = True
    room.new_stage()
    position = 1
    for player in room.players:
        room.characters.extend(player.characters)
        player.characters.clear()
        await send_message(
            player.id_number,
            text=player.Messages.CHARACTERS_JOINED
        )
        await send_message(
            player.id_number,
            reply_markup=kb.set_position_keyboard,
            text=player.Messages.ENTER_ORDER
        )
        room.availible_positions.append(position)
        position += 1


@router.message(Command('set_position'))
async def set_position(message: Message, state: FSMContext):
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)

    if not (room and player):
        if not room:
            if not player:
                await message.answer(
                    text=Player.Messages.PLAYER_NOT_REGISTERED,
                    reply_markup=kb.start_keyboard
                )
                return None
            await message.answer(
                text=player.Messages.ROOM_NOT_ENTERED
            )
            await state.set_state(Reg.room_id)
            return None

    if not room.characters_united:
        await message.answer(
            text=player.Messages.WAIT_FOR_OTHER_PLAYERS
        )
        return None

    await message.answer(
        text=player.Messages.ENTER_POSITION
    )
    await state.set_state(Reg.position)


@router.message(Reg.position)
async def add_position(message: Message, state: FSMContext):
    await state.clear()
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)
    result = room.check_position(message)

    if message.text == '/exit':
        await remove_player(message)
        return None

    if result == player.Messages.OK:
        player.set_position(message)
        room.set_players_position(player)
        await message.answer(
            text=player.Messages.READY_TO_PLAY,
            reply_markup=kb.play_keyboard
        )
        return None

    await message.answer(
        text=result,
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        text=(
            'Доступные номера: '
            f'{room.availible_positions}'
        )
    )
    await state.set_state(Reg.position)


@router.message(Command('play'))
async def play(message: Message, state: FSMContext):
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)

    if not room or not player:
        if not player:
            await message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if not player.has_order:
        await message.answer(
            text=player.Messages.PLAYER_NOT_ORDERED,
            reply_markup=kb.set_position_keyboard
        )
        return None

    room.unready_players.remove(player)

    if not room.player_is_last():
        await message.answer(
            text=(
                'Когда все игроки будут готовы вы получите сообщение с '
                'именами игроков, которые будут отгадывать ваши слова '
                'или загадывать свои слова вам'
            )
        )
        return None

    for player in room.players:
        next_player: Player = room.get_next_player(player)
        previous_player: Player = room.get_previous_player(player)
        await send_message(
            player.id_number,
            reply_markup=ReplyKeyboardRemove(),
            text=(
                f'Вы загадываете слова игроку {next_player.name} '
                f'и отгадывате слова игрока {previous_player.name}'
            )
        )
        if room.check_players_order(player):
            await send_message(
                player.id_number,
                reply_markup=kb.start_round_keyboard,
                text=player.Messages.FIRST_PLAYER_MOVE
            )


@router.message(Command('start_round'))
async def start_round(message: Message, state: FSMContext):
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)

    if not room or not player:
        if not player:
            await message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if not room.check_players_order(player):
        await message.answer(
            text=player.Messages.WAIT_FOR_YOUR_TURN
        )
        return None

    room.start_round()

    while True:

        if room.times_up():
            await end_round(player=player, room=room, times_up=True)
            break

        if not room.characters:
            room.reset_charracters()
            await end_round(player=player, room=room)
            break

        if not player.current_character:
            character = room.get_character()
            player.current_character = character
            await message.answer(
                reply_markup=kb.next_keyboard,
                text=f'Объясните персонажа {character}'
            )

        await asyncio.sleep(0.2)


@router.message(Command('next'))
async def character_guessed(message: Message, state: FSMContext):
    room: Room = await get_room_by(message)
    player: Player = await get_player_by(message)

    if not room or not player:
        if not player:
            await message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if not room.check_players_order(player):
        await message.answer(
            text=player.Messages.WAIT_FOR_YOUR_TURN
        )
        return None

    if not player.is_playing:
        await message.answer(
            text=player.Messages.START_ROUND,
            reply_markup=kb.start_round_keyboard
        )

    room.next_character()


@router.message(Command('exit'))
async def exit(message: Message):
    await remove_player(message)
