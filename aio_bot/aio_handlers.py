import asyncio
import os

import aio_keybords as kb
from aio_states import Reg
from aiogram import Bot, Router, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from dotenv import load_dotenv
from game_classes import Player, Room
from logger import get_logger

load_dotenv()

TOKEN = os.getenv('TOKEN')

bot = Bot(token=TOKEN)

router = Router()

logger = get_logger(__name__)


async def send_message(chat_id, text, reply_markup=None):
    await bot.send_message(
        chat_id=chat_id, text=text, reply_markup=reply_markup
    )


def get_player_id_by(callback: CallbackQuery = None, message: Message = None):
    return callback.message.chat.id if callback else message.from_user.id if message else None


def get_player_by_id(player_id: int = None):
    return Player.PLAYERS.get(player_id) if player_id else None


def get_room_by(room_id: int = None):
    return Room.ROOMS.get(room_id) if room_id else None


def create_player_with(callback: CallbackQuery = None, message: Message = None, player_id: int = None):
    player_id = player_id or get_player_id_by(callback, message)

    if not get_player_by_id(player_id=player_id):
        player = Player(player_id)
        Player.PLAYERS[player.id_number] = player
        return player


async def remove_player_by(callback: CallbackQuery = None, message: Message = None, player_id: int = None):
    player_id = player_id or get_player_id_by(callback, message)
    outcast: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=outcast.room_id) if outcast else None

    if not outcast:
        await send_message(
            text='Вы ещё не зарегестрировались в игре',
            reply_markup=kb.start_keyboard
        )
        return

    if outcast.is_playing:
        logger.info('player can not leave when playing')
        await send_message(
            outcast.id_number,
            text=outcast.Messages.FINISH_ROUND
        )
        return

    if outcast.is_gamemaster and room and len(room.players) > 1:
        logger.debug('gamemaster is leaving non-empty room')
        for player in room.players:
            if player != outcast:
                new_gamemaster: Player = player
                logger.info('new gamemaster appointed')
                break

        room.gamemaster = new_gamemaster.id_number
        new_gamemaster.is_gamemaster = True

    kick_player = True
    new_gamemaster_message = None
    refresh_positions = False
    people_left_in_open_room = False
    not_all_people_chose_positions = False

    if not room:
        logger.debug('player leaves before entering the room')
        kick_player = False

    elif len(room.players) == 1:
        logger.debug('the last player left, room is destroyed')
        del room.ROOMS[room.id_number]
        kick_player = False

    elif room.open and outcast.is_gamemaster:
        logger.debug('gamemaster leaves before closing the room')

        new_gamemaster_message = (
            'Вы теперь ведущий. Закройте комнату когда все '
            'игроки присоединятся к ней'
        )

        people_left_in_open_room = True

    elif not room.characters_united:
        logger.debug('player leaves before shuffling characters')

        if outcast in room.unready_players:
            logger.info('player leaves before adding their characters')
            room.unready_players.remove(outcast)

        if outcast.is_gamemaster:
            logger.debug('gamemaster left without shuffling characters')
            new_gamemaster_message = (
                'Вы теперь ведущий. Когда все игроки и вы в том '
                'числе закончат добавлять персонажей нажмите на '
                'кнопку "Смешать персонажей". Она появится, '
                'когда все игроки введут своих персонажей. '
                'Сейчас продолжайте вписывать своих персонажей, '
                'если ещё не успели записать всех'
            )

    elif not room.players_ready:
        logger.debug('player leaves while choosing position')
        kick_player = False

        if outcast.has_order:
            logger.debug('gamemaster chose position and left')
            room.availible_positions.append(outcast.position)
            outcast.has_order = False

        if outcast.is_gamemaster:
            logger.debug('gamemaster leaves while choosing position')

            new_gamemaster_message = (
                'Вы теперь ведущий. Когда все игроки '
                'выберут позиции нажмите кнопку Игроки готовы \n'
                'Игроки не выбравшие позицию будут дисквалифицированы'
            )
            not_all_people_chose_positions = True

    elif room.players_ready:
        logger.info('player leaves during the game')
        kick_player = True
        refresh_positions = True
        if outcast.position == room.current_player_position:
            logger.info(f'{outcast.position} : {room.current_player_position}')
            guesser: Player = room.get_next_player(outcast)
            await send_message(
                guesser.id_number,
                text=(
                    'Ваш напарник покинул игру в свой ход. '
                    'Теперь ваша очередь ходить'
                ),
                reply_markup=kb.start_round_keyboard
            )
            room.end_round()

    outcast.is_gamemaster = False

    await send_message(
        outcast.id_number,
        reply_markup=kb.start_keyboard,
        text=outcast.Messages.GAME_EXITED
    )
    del outcast.PLAYERS[outcast.id_number]

    if kick_player:
        logger.info('player will be kicked form the room')
        room.players.remove(outcast)
        if refresh_positions:
            logger.info('positions will be refreshed')
            room.refresh_players_positions()
            for player in room.players:
                logger.info(
                    f'{player.position}{room.current_player_position}'
                )

    if new_gamemaster_message:
        logger.info('informing new gamemaster')

        await send_message(
            new_gamemaster.id_number,
            text=new_gamemaster_message
        )

        if people_left_in_open_room:
            logger.info('informing about people in lobby')
            open_room_names = [player.name for player in room.players]
            await send_message(
                new_gamemaster.id_number,
                text=(
                    'Список игроков в комнате: \n'
                    f"{', '.join(open_room_names)}"
                ),
                reply_markup=kb.close_room_keyboard
            )

        elif not_all_people_chose_positions:
            logger.info('informing about people choosing position')
            position_names = [
                player.name for player in room.players if player.has_order
            ]
            await send_message(
                new_gamemaster.id_number,
                text=(
                    'Список игроков с позициями: \n'
                    f"{', '.join(position_names)}"
                ),
                reply_markup=kb.play_keyboard
            )


def create_room(gamemaster: Player):
    room = Room(gamemaster.id_number)
    gamemaster.room_id = room.id_number
    gamemaster.is_gamemaster = True
    room.players.append(gamemaster)
    room.ROOMS[room.id_number] = room
    return room


async def end_round(
        room: Room,
        player: Player,
        times_up=False,
        first_message=None
):
    guesser: Player = room.get_next_player(player)

    if first_message:
        await bot.delete_message(
            chat_id=first_message.chat.id,
            message_id=first_message.message_id,
        )

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

    if times_up:
        await send_message(
            player.id_number,
            text='Время вышло'
        )

    await send_message(
        player.id_number,
        text=(
            'Количество заработаных очков в этот раз: '
            f'{player.round_score}'
        )
    )

    if player != guesser:
        if times_up:
            await send_message(
                guesser.id_number,
                text='Время вышло'
            )
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
    room.end_round()


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


@router.message(CommandStart())
async def start(message: Message):
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

    if not (player and room):
        await message.answer(
            text='Добро пожаловать в игру "Шляпа"',
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(
            text=Player.Messages.CREATE_OR_ENTER_ROOM,
            reply_markup=kb.new_keyboard_inline
        )
        return None

    await message.answer(
        text=Player.Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )


@router.callback_query(F.data == 'new_room')
async def new_room_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    gamemaster: Player = create_player_with(callback=callback)
    await callback.answer('')
    if gamemaster:
        create_room(gamemaster)
        await callback.message.delete()
        await callback.message.answer(
            text='Вы вошли в игру'
        )
        await callback.message.answer(
            text=gamemaster.Messages.ENTER_YOUR_NAME
        )
        await state.set_state(Reg.name)
        return None

    await callback.message.answer(
        text=Player.Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )


@router.callback_query(F.data == 'enter_room')
async def enter_room_callback(callback: CallbackQuery, state: FSMContext):
    player: Player = create_player_with(callback=callback)
    await callback.answer('')
    if player:
        await state.set_state(Reg.name)
        await callback.message.delete()
        await callback.message.answer(
            text='Вы вошли в игру'
        )
        await callback.message.answer(
            text=player.Messages.ENTER_YOUR_NAME
        )
        return None

    await callback.message.answer(
        text=Player.Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )


@router.message(Reg.name)
async def add_name(message: Message, state: FSMContext):
    await state.clear()
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)

    if not message.text:
        await message.answer(
            text='Пожалуйтса запишите своё имя текстом'
        )
        await state.set_state(Reg.name)
        return None

    if message.text == '/exit':
        await remove_player_by(message=message)
        return None

    player.name = message.text

    if player.is_gamemaster:
        await message.answer(
            text=player.Messages.ENTER_NUMBER_OF_CHARACTERS,
        )
        await state.set_state(Reg.number_of_characters)
        return None

    await message.answer(
        text=player.Messages.ENTER_ROOM_ID,
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Reg.room_id)


@router.message(Reg.room_id)
async def add_room_id(message: Message, state: FSMContext):
    await state.clear()
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    result = player.check_room_id(message)

    if message.text == '/exit':
        await remove_player_by(message=message)
        return None

    if result == player.Messages.OK:
        room_id = int(message.text)
        room: Room = get_room_by(room_id=room_id)

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


@router.message(Reg.number_of_characters)
async def add_number_of_charaters(message: Message, state: FSMContext):
    await state.clear()
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None
    result = player.check_number_of_characters(message)

    if message.text == '/exit':
        await remove_player_by(message=message)
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


@router.message(F.text == 'Закрыть комнату 🚪')
async def close_room(message: Message, state: FSMContext):
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

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
                reply_markup=kb.add_characters_keyboard
        )
        return None

    room.close()
    for player in room.players:
        if not player.is_gamemaster:
            await send_message(
                player.id_number,
                text=(
                    'Количесво персонажей на эту игру - '
                    f'{room.number_of_characters}.'
                )
            )
        await send_message(
            chat_id=player.id_number,
            text=player.Messages.ADD_CHARACTERS,
            reply_markup=kb.add_characters_keyboard
        )


@router.message(F.text == 'Добавить персонажей ➕')
async def start_adding_characters(message: Message, state: FSMContext):
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

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
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

    if not message.text:
        await message.answer(
            text='Персонажа можно записать только текстом'
        )
        await state.set_state(Reg.character)
        return None

    if message.text == '/exit':
        await remove_player_by(message=message)
        return None

    if message.text == 'Смешать персонажей 🔁':
        await message.answer(
            text=(
                'Выполните это действие когда закончите '
                'вводить свох персонажей'
            )
        )
        await state.set_state(Reg.character)
        return None

    character = message.text
    if not player.can_add_more_characters(room):
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
                text='Все игроки ввели своих персонажей',
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


@router.message(F.text == 'Смешать персонажей 🔁')
async def join_characters(message: Message, state: FSMContext):
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

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

    if room.unready_players:
        await message.answer(
            text=(
                'Не все игроки успели добавить своих персонажей. '
                'Попробуйте ещё раз когда все будут готовы'
            ),
            reply_markup=kb.join_characters_keyboard
        )
        return None

    room.characters_united = True

    room.set_availible_positions()

    logger.info(f'availible positions {room.availible_positions}')

    for new_player in room.players:
        new_player: Player
        room.characters.extend(new_player.characters)
        new_player.characters.clear()
        logger.info('characters successfully shuffled')
        await send_message(
            new_player.id_number,
            text=new_player.Messages.CHARACTERS_JOINED
        )
        await send_message(
            new_player.id_number,
            reply_markup=await kb.positions_inline(room.availible_positions),
            text='Выберете номер в очереди'
        )

    await message.answer(
        text=(
            'Когда все игроки выберут номер в очереди, '
            'нажмите кнопку игроки готовы. Игроки не выбравшие '
            'номер в очереди будут дисквалифицированны'
        ),
        reply_markup=kb.play_keyboard
    )


@router.message(F.text == 'Игроки готовы')
async def play(message: Message, state: FSMContext):
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

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

    extra_players = False
    if room.availible_positions:
        extra_players = True
        logger.info('some positions are not chosen')
        if len(room.players) == len(room.availible_positions):
            logger.info('none of the players chose position')
            await message.answer(
                text=(
                    'нельзя начинать игру пока ни один из '
                    'игроков не выбрал номер в очреди'
                )
            )
            return None

        for player in room.players:
            if not player.has_order:
                room.players.remove(player)
                if player.is_gamemaster:
                    logger.debug('gamemaster didnt choose position and left')
                    new_gamemaster: Player = room.players[0]
                    logger.debug(f'{new_gamemaster.name}')
                    room.gamemaster = new_gamemaster.id_number
                    new_gamemaster.is_gamemaster = True

        room.availible_positions.clear()
        room.refresh_players_positions()

    logger.info('all positions are chosen')
    room.players_ready = True

    for player in room.players:
        if extra_players:
            await send_message(
                player.id_number,
                reply_markup=ReplyKeyboardRemove(),
                text=(
                    'Некоторые игроки не выбрали порядок в очереди '
                    'и были дисквалифицированны \n'
                    f'Ваша новая позиция {player.position+1}'
                )
            )
        await send_message(
            player.id_number,
            text=(
                'Вы загадываете слова игроку '
                f'{room.get_next_player(player).name} \n'
                'Слова отгадываете слова игрока '
                f'{room.get_previous_player(player).name}'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        if room.check_players_order(player):
            await send_message(
                player.id_number,
                reply_markup=kb.start_round_keyboard,
                text=player.Messages.FIRST_PLAYER_MOVE
            )


@router.message(F.text == 'Начать раунд')
async def start_round(message: Message, state: FSMContext):
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

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

    if not room.players_ready:
        await message.answer(
            text='Ведущий должен объявить что все игроки готовы'
        )
        return None

    if not room.check_players_order(player):
        await message.answer(
            text=player.Messages.WAIT_FOR_YOUR_TURN
        )
        return None

    await message.answer(
        text='Раунд начался',
        reply_markup=ReplyKeyboardRemove()
    )
    room.start_round()

    first_message = None
    while True:

        # if not await get_player_by(message=message):
        #     await message.answer(
        #         text='Вы принудительно завершили игру'
        #     )

        if room.times_up() or not room.characters:
            if not room.characters:
                room.reset_characters()
            await end_round(
                player=player, room=room,
                times_up=room.times_up(),
                first_message=first_message
            )
            break

        if not player.current_character:
            character = room.get_character()
            player.current_character = character
            if not first_message:
                first_message = await bot.send_message(
                    player.id_number,
                    reply_markup=kb.character_inline,
                    text=f'Объясните персонажа {character}'
                )
            else:
                await bot.edit_message_text(
                    chat_id=first_message.chat.id,
                    message_id=first_message.message_id,
                    reply_markup=kb.character_inline,
                    text=f'Объясните персонажа {character}'
                )

        await asyncio.sleep(0.2)


@router.callback_query(F.data == 'next_character')
async def next_character(callback: CallbackQuery, state: FSMContext):
    await callback.answer('')
    player_id = get_player_id_by(callback=callback)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

    if not room or not player:
        if not player:
            await callback.message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await callback.message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if not room.check_players_order(player):
        await callback.message.answer(
            text=player.Messages.WAIT_FOR_YOUR_TURN
        )
        return None

    if not player.is_playing:
        await callback.message.answer(
            text=player.Messages.START_ROUND,
            reply_markup=kb.start_round_keyboard
        )

    room.next_character()


@router.message(Command('exit'))
async def exit(message: Message):
    await remove_player_by(message=message)


@router.callback_query(F.data.startswith('position_'))
async def choose_guesser(callback: CallbackQuery, state: FSMContext):
    position = int(callback.data.split('_')[-1])
    player_id = get_player_id_by(callback=callback)
    player: Player = get_player_by_id(player_id=player_id)
    room: Room = get_room_by(room_id=player.room_id) if player else None

    if not room or not player:
        if not player:
            await callback.message.answer(
                text=Player.Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return None
        await callback.message.answer(
            text=player.Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return None

    if player.has_order:
        await callback.answer('Вы уже имеете номер в очереди', show_alert=True)
        return None

    if position not in room.availible_positions:
        await callback.answer(
            'Эта позиция уже выбрана', show_alert=True
        )
        await callback.message.edit_reply_markup(
            reply_markup=await kb.positions_inline(
                room.availible_positions
            )
        )
        return None

    await callback.answer('')
    player.set_position(position)
    room.availible_positions.remove(position)
    room.set_players_position(player)
    await callback.message.answer(
        text=f'ваш номер в очереди {position}'
    )
    await callback.message.delete()
