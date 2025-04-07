import asyncio
import logging

import aio_keybords as kb
from aio_states import Reg
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from bot import bot, on_shutdown, send_message
from game_classes import Player, Room
from texts import Messages, Commands, CallbackData, Flags

router = Router()


logging.basicConfig(
    level=logging.INFO,
    format="%(funcName)s- %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

ADMINS = [413470404]


def is_admin(message: Message):
    return message.from_user.id in ADMINS


def get_player_id_by(callback: CallbackQuery = None, message: Message = None):
    return callback.message.chat.id if callback else message.from_user.id if message else None


def get_player_by_id(player_id):
    return Player.PLAYERS.get(player_id)


def get_room_by(room_id):
    return Room.ROOMS.get(room_id)


def create_player_with(callback: CallbackQuery = None, message: Message = None):
    player_id = get_player_id_by(callback, message)

    if not get_player_by_id(player_id):
        player = Player(player_id)
        Player.PLAYERS[player.id_number] = player
        return player


async def remove_player_by(callback: CallbackQuery = None, message: Message = None):
    """
    Удаляет игрока из комнаты, обрабатывая различные сценарии:
    - Если игрока нет в игре, отправляет сообщение о необходимости регистрации.
    - Если игрок играет, не позволяет выйти.
    - Если выходит ведущий, передает роль другому игроку.
    - Если выходит последний игрок, удаляет комнату.
    - Обрабатывает выход игроков на разных стадиях игры.
    """
    logging.info("Удаление игрока из игры")

    player_id = get_player_id_by(callback, message)
    outcast: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(outcast.room_id) if outcast else None

    kick_player = True
    destroy_room = False
    new_gamemaster_message = None
    refresh_positions = False
    people_left_in_open_room = False
    not_all_people_chose_positions = False
    new_gamemaster = None
    send_shuffle_button = False

    if not outcast:
        logging.info('Игрок выходит до регистрации')
        await message.answer(
            text=Messages.PLAYER_NOT_REGISTERED_YET,
            reply_markup=kb.start_keyboard
        )
        return

    if outcast.is_playing:
        logging.info('Игрок не может выйти во время игры')
        await send_message(
            outcast.id_number,
            text=Messages.FINISH_ROUND
        )
        return

    if outcast.is_gamemaster and room and len(room.players) > 1:
        logging.info('Ведущий выходит из комнаты')
        for player in room.players:
            if player != outcast and player in Player.PLAYERS.values():
                new_gamemaster = player
                logging.info('Назначен новый ведущий')
                break

        if not new_gamemaster:
            logging.info('Не удалось назначить нового ведущего')
            logging.info('Нет ни одного зарегестрированного игрока, комната будет удалена')
            destroy_room = True
        else:
            room.gamemaster = new_gamemaster.id_number
            new_gamemaster.is_gamemaster = True

    if not room:
        logging.info('Игрок выходит до входа в комнату')
        kick_player = False

    elif len(room.players) == 1:
        logging.info('Последний игрок покинул комнату - комната будет удалена')
        destroy_room = True
        kick_player = False

    elif room.open and outcast.is_gamemaster:
        logging.info('Ведущий покидает открытую комнату')
        new_gamemaster_message = Messages.NEW_GAMEMASTER_MESSAGE_FOR_OPEN_ROOM,
        people_left_in_open_room = True

    elif not room.characters_united:
        logging.info('Игрок выходит до перемешивания персонажей')
        if outcast in room.unready_players:
            room.unready_players.remove(outcast)
        if outcast.is_gamemaster and new_gamemaster:
            if room.unready_players:
                logging.info('Ведущий покинул игру до того как все игроки ввели совоих персонажей')
                if new_gamemaster in room.unready_players:
                    new_gamemaster_message = Messages.NEW_GAMEMASTER_MESSAGE_BEFORE_SHUFFLE
                else:
                    new_gamemaster_message = Messages.NEW_GAMEMASTER_MESSAGE_IF_GAMEMASTER_IS_READY
            else:
                logging.info('Ведущий единственный не ввёл всех персонажей и покинул игру')
                new_gamemaster_message = Messages.NEW_GAMEMASTER_MESSAGE_ALL_PLAYERS_ENTERED_CHARACTERS
                send_shuffle_button = True

    elif not room.players_ready:
        logging.info('Игрок выходит во время выбора позиций')
        kick_player = False
        if outcast.has_order:
            room.availible_positions.append(outcast.position)
            outcast.has_order = False
        if outcast.is_gamemaster:
            new_gamemaster_message = Messages.NEW_GAMEMASTER_MESSAGE_DURING_POSITION_CHOICE
            not_all_people_chose_positions = True

    else:
        logging.info('Игрок выходит во время игры')
        refresh_positions = True
        if outcast.position == room.current_player_position:
            guesser: Player = room.get_next_player(outcast)
            await send_message(
                guesser.id_number,
                text=Messages.PARTNER_LEFT_GAME_MESSAGE,
                reply_markup=kb.start_round_keyboard
            )
            room.end_round()

    outcast.is_gamemaster = False
    await send_message(
        outcast.id_number,
        reply_markup=kb.start_keyboard,
        text=Messages.GAME_EXITED
    )
    outcast.PLAYERS.pop(outcast.id_number, None)

    if destroy_room:
        logging.info('Удаление комнаты')
        room.players.clear()
        room.ROOMS.pop(room.id_number, None)
        room.ROOM_LOCKS.pop(room.id_number, None)
        if room.id_number in room.TAKEN_ROOM_NUMBERS:
            room.TAKEN_ROOM_NUMBERS.remove(room.id_number)

    if kick_player and room.id_number in room.ROOM_LOCKS:
        async with room.ROOM_LOCKS[room.id_number]:
            room.players.remove(outcast)
            if refresh_positions:
                room.refresh_players_positions()

    if new_gamemaster and new_gamemaster_message:

        await send_message(
            new_gamemaster.id_number,
            text=new_gamemaster_message,
            reply_markup=kb.join_characters_keyboard if send_shuffle_button else None
        )

        if people_left_in_open_room:
            open_room_names = [player.name for player in room.players]
            await send_message(
                new_gamemaster.id_number,
                text=f'Игроки в комнате: {", ".join(open_room_names)}',
                reply_markup=kb.close_room_keyboard
            )

        elif not_all_people_chose_positions:
            position_names = [player.name for player in room.players if player.has_order]
            await send_message(
                new_gamemaster.id_number,
                text=f'Игроки с позициями: {", ".join(position_names)}',
                reply_markup=kb.play_keyboard
            )


def create_room(gamemaster: Player):
    """
    Создаёт новую игровую комнату и назначает игрока ведущим.

    - Инициализирует объект Room
    - Присваивает игроку ID комнаты и статус ведущего
    - Добавляет ведущего в список игроков комнаты
    - Регистрирует комнату и блокировку в глобальных словарях Room
    """
    room = Room(gamemaster.id_number)
    gamemaster.room_id = room.id_number
    gamemaster.is_gamemaster = True
    room.players.append(gamemaster)
    room.ROOMS[room.id_number] = room
    room.ROOM_LOCKS[room.id_number] = asyncio.Lock()
    logging.info(f"Создана новая комната с ID {room.id_number} для ведущего {gamemaster.id_number}")
    return room


async def end_round(
        room: Room, player: Player,
        last_message: Message = None,
        times_up=False,
):
    """
    Завершает раунд игры:
    - Если время вышло: уведомляет текущего и следующего игрока.
    - Если персонажи угаданы: показывает таблицу лидеров, увеличивает раунд.
    - Проверяет, завершилась ли игра, и, если да, вызывает завершение.
    - Передаёт ход следующему игроку.
    """
    guesser: Player = room.get_next_player(player)

    if times_up:
        times_up_message = f'{Messages.TIMES_UP}{player.round_score}'

        if last_message:
            await bot.edit_message_text(
                chat_id=last_message.chat.id,
                message_id=last_message.message_id,
                text=Messages.UNGUESSED_CHARACTER,
                reply_markup=None
            )
            logging.info(f"Сообщение с неотгаданным персонажем обновлено в чате {last_message.chat.id}")

        await send_message(
            player.id_number,
            text=times_up_message
        )
        logging.info(f"Игроку {player.id_number} отправлено сообщение о завершении по таймеру")

        if player != guesser:
            await send_message(
                guesser.id_number,
                text=times_up_message
            )
            logging.info(f"Следующему игроку {guesser.id_number} также отправлено сообщение о завершении раунда")

    else:
        sorted_players = sorted(
            room.players, key=lambda player: player.score, reverse=True
        )
        logging.info(f"Формируется таблица результатов раунда {room.round} для комнаты {room.id_number}")

        score_board = Messages.TABLE_HEAD + "\n\n".join(
            f"🔹 {i+1} | {player.name} | {player.score}" for i, player in enumerate(sorted_players)
        )

        for person in room.players:
            person: Player
            await send_message(
                person.id_number,
                text=Messages.ALL_CHARACTERS_GUESSED
            )
            await send_message(
                person.id_number,
                text=(
                    f'{Messages.FINISHED_ROUND_NUMBER} {room.round}\n\n'
                    f'{score_board}'
                )
            )

        room.next_round()
        logging.info(f"Переход к следующему раунду — теперь раунд {room.round}")
        if room.last_round():
            logging.info(f"Игра в комнате {room.id_number} завершена")
            await game_over(room)
            return

    await send_message(
        guesser.id_number,
        reply_markup=kb.start_round_keyboard,
        text=Messages.YOUR_MOVE
    )
    logging.info(f"Игроку {guesser.id_number} передан ход")

    room.end_round()
    logging.info(f"Раунд завершён в комнате {room.id_number}")


async def game_over(room: Room):
    """
    Завершает игру в комнате:
    - Уведомляет всех игроков об окончании игры.
    - Очищает игроков и удаляет комнату из всех глобальных структур.
    """

    logging.info(f"Игра в комнате {room.id_number} завершена. Очистка данных...")

    for player in room.players:
        player: Player
        await send_message(
            player.id_number,
            text=Messages.GAME_OVER
        )
        await send_message(
            player.id_number,
            reply_markup=kb.start_keyboard,
            text=Messages.GAME_EXITED
        )
        player.PLAYERS.pop(player.id_number, None)

    room.players.clear()
    room.ROOMS.pop(room.id_number, None)
    room.ROOM_LOCKS.pop(room.id_number, None)
    if room.id_number in room.TAKEN_ROOM_NUMBERS:
        room.TAKEN_ROOM_NUMBERS.remove(room.id_number)


@router.message(CommandStart())
async def start(message: Message):
    """
    Обработчик команды /start.

    Проверяет, существует ли игрок и находится ли он в комнате.
    Если игрока или комнаты нет — отправляет приветственное сообщение
    и предлагает создать или войти в комнату.
    Если игрок уже находится в комнате — просит выйти из предыдущей игры.
    """
    logging.info(f"Пользователь {message.from_user.id} вызвал команду /start")

    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not (player and room):
        await message.answer(
            text=Messages.WELCOME_MESSAGE,
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(
            text=Messages.CREATE_OR_ENTER_ROOM,
            reply_markup=kb.new_keyboard_inline
        )
        return

    await message.answer(
        text=Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )


@router.callback_query(F.data == CallbackData.NEW_ROOM_DATA)
async def new_room_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса при создании новой комнаты.

    Очищает состояние, создаёт игрока и комнату.
    Если всё прошло успешно — запускает игру и запрашивает имя.
    Если не удалось — предлагает выйти из предыдущей игры.
    """

    logging.info(f"Пользователь {callback.from_user.id} создаёт новую комнату")

    await state.clear()
    gamemaster: Player = create_player_with(callback=callback)
    await callback.answer('')
    if gamemaster:
        create_room(gamemaster)
        await callback.message.answer(
            text=Messages.GAME_STARTED
        )
        await callback.message.answer(
            text=Messages.ENTER_YOUR_NAME
        )
        await state.set_state(Reg.name)
        await callback.message.delete()
        logging.info(
            f"Комната успешно создана пользователем {callback.from_user.id}"
        )
        return

    await callback.message.answer(
        text=Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )
    logging.warning(
        f"Пользователь {callback.from_user.id} "
        "не может создать новую комнату — уже участвует в игре"
        )


@router.callback_query(F.data == CallbackData.ENTER_ROOM_DATA)
async def enter_room_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик callback-запроса на вход в существующую комнату.

    Создаёт игрока и переводит его в состояние ввода имени,
    если вход в комнату разрешён. Иначе — предлагает выйти из текущей игры.
    """
    logging.info(f"Пользователь {callback.from_user.id} пытается войти в комнату")

    player: Player = create_player_with(callback=callback)
    await callback.answer('')
    if player:
        await state.set_state(Reg.name)
        await callback.message.answer(
            text=Messages.GAME_STARTED
        )
        await callback.message.answer(
            text=Messages.ENTER_YOUR_NAME
        )
        await callback.message.delete()
        logging.info(f"Игрок {callback.from_user.id} успешно вошёл в комнату")
        return

    await callback.message.answer(
        text=Messages.EXIT_PREVIOUS_GAME,
        reply_markup=kb.exit_keyboard
    )
    logging.warning(
        f"Пользователь {callback.from_user.id} "
        "не может войти в комнату — уже участвует в игре"
    )


@router.message(Reg.name)
async def add_name(message: Message, state: FSMContext):
    """
    Обработчик ввода имени игрока.

    Проверяет корректность имени. Если имя задано, сохраняет его.
    В зависимости от роли (ведущий или игрок) переводит в соответствующее состояние.
    """
    logging.info(f"Пользователь {message.from_user.id} вводит имя")

    await state.clear()
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None

    if not message.text:
        await message.answer(
            text=Messages.WRITE_YOUR_NAME_WITH_TEXT
        )
        await state.set_state(Reg.name)
        logging.info(f"Пользователь {message.from_user.id} отправил пустое сообщение")
        return

    if message.text == Commands.EXIT_COMMAND:
        await remove_player_by(message=message)
        logging.info(f"Пользователь {message.from_user.id} покинул игру командой выхода")
        return

    if message.text.startswith('/'):
        await message.answer(
            text=Messages.CANT_REGISTER_COMMAND_AS_NAME
        )
        logging.warning(f"Пользователь {message.from_user.id} попытался использовать команду вместо имени: {message.text}")
        return

    player.name = message.text
    logging.info(f"Имя игрока {player_id} установлено: {player.name}")

    if player.is_gamemaster:
        await message.answer(
            text=Messages.ENTER_NUMBER_OF_CHARACTERS,
        )
        await state.set_state(Reg.number_of_characters)
        logging.info(f"Игрок {player_id} — ведущий. Перевод в состояние ввода количества персонажей.")
        return

    await message.answer(
        text=Messages.ENTER_ROOM_ID,
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(Reg.room_id)
    logging.info(f"Игрок {player_id} переведён в состояние ввода ID комнаты")


@router.message(Reg.room_id)
async def add_room_id(message: Message, state: FSMContext):
    """
    Обработчик ввода ID комнаты игроком.

    Проверяет корректность введённого ID, статус комнаты и добавляет игрока,
    если всё в порядке. При необходимости возвращает игрока на повторный ввод.
    """

    logging.info(f"Пользователь {message.from_user.id} вводит ID комнаты")

    await state.clear()
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    result = player.check_room_id(message) if player else None

    if message.text == Commands.EXIT_COMMAND:
        await remove_player_by(message=message)
        logging.info(f"Пользователь {message.from_user.id} покинул игру командой выхода")
        return

    if result == Flags.OK:
        room_id = int(message.text)
        room: Room = get_room_by(room_id)

        if not room.open:
            await message.answer(
                text=Messages.ROOM_IS_CLOSED
            )
            await state.set_state(Reg.room_id)
            logging.info(f"Комната {room_id} закрыта. Игрок {player_id} не был допущен.")
            return

        if player in room.players:
            await message.answer(
                text=Messages.ROOM_ENTERED
            )
            logging.info(f"Игрок {player_id} уже находится в комнате {room_id}")
            return

        room.players.append(player)
        player.room_id = room_id

        await message.answer(
            text=Messages.ROOM_ENTERED
        )
        await send_message(
            chat_id=room.gamemaster,
            text=f'Игрок {player.name} вошёл в комнату'
        )
        logging.info(f"Игрок {player.name} добавлен в комнату {room_id}")
        return

    await message.answer(
        text=result
    )
    logging.warning(f"Игрок {player_id} ввёл некорректный ID комнаты: {message.text} — {result}")

    if result != Flags.PLAYER_IS_IMPOSTOR:
        await state.set_state(Reg.room_id)


@router.message(Reg.number_of_characters)
async def add_number_of_charaters(message: Message, state: FSMContext):
    """
    Обработчик ввода количества персонажей ведущим.

    Проверяет корректность числа. Если всё корректно — сохраняет его в комнате
    и отправляет ведущему номер комнаты и кнопку для закрытия.
    В противном случае — запрашивает повторный ввод.
    """

    logging.info(f"Ведущий {message.from_user.id} вводит количество персонажей")

    await state.clear()
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None
    result = player.check_number_of_characters(message)

    if message.text == Commands.EXIT_COMMAND:
        await remove_player_by(message=message)
        logging.info(f"Ведущий {message.from_user.id} вышел из игры")
        return

    if result == Flags.OK:
        room.number_of_characters = int(message.text)
        await message.answer(
            text=Messages.CLOSE_ROOM
        )
        await message.answer(
            reply_markup=kb.close_room_keyboard,
            text=f'{Messages.YOUR_ROOM_NUMBER_IS}{room.id_number}. '
        )
        logging.info(f"Комната {room.id_number}: установлено количество персонажей — {room.number_of_characters}")
        return

    await message.answer(
        text=result
    )
    logging.warning(f"Некорректный ввод количества персонажей от {message.from_user.id}: {message.text}")

    if result != Flags.PLAYER_IS_IMPOSTOR:
        await state.set_state(Reg.number_of_characters)


@router.message(F.text == Commands.CLOSE_ROOM_COMMAND)
async def close_room(message: Message, state: FSMContext):
    """
    Обработчик команды закрытия комнаты ведущим.

    Проверяет: зарегистрирован ли игрок, вошёл ли он в комнату, является ли ведущим,
    открыта ли ещё комната. При выполнении условий закрывает комнату и уведомляет игроков.
    """

    logging.info('Вызвана функция закрытия комнаты')

    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not player:
        await message.answer(
            text=Messages.PLAYER_NOT_REGISTERED,
            reply_markup=kb.start_keyboard
        )
        logging.warning(f"Незарегистрированный пользователь {message.from_user.id} попытался закрыть комнату")
        return

    if not room:
        await message.answer(text=Messages.ROOM_NOT_ENTERED)
        await state.set_state(Reg.room_id)
        logging.warning(f"Игрок {player_id} не состоит ни в одной комнате")
        return

    if not player.is_gamemaster:
        await message.answer(
            text=Flags.PLAYER_IS_IMPOSTOR,
            reply_markup=ReplyKeyboardRemove()
        )
        logging.warning(f"Игрок {player_id} не является ведущим и попытался закрыть комнату")
        return

    if not room.open:
        await message.answer(
            text=Messages.ROOM_IS_CLOSED,
            reply_markup=kb.add_characters_keyboard
        )
        logging.info(f"Комната {room.id_number} уже была закрыта")
        return

    room.close()
    for player in room.players:
        if not player.is_gamemaster:
            await send_message(
                player.id_number,
                text=(
                    f'{Messages.NUMBER_OF_CHARACTERS_FOR_THIS_GAME_IS}'
                    f'{room.number_of_characters}.'
                )
            )
        await send_message(
            chat_id=player.id_number,
            text=Messages.ADD_CHARACTERS,
            reply_markup=kb.add_characters_keyboard
        )
    logging.info(f"Все игроки в комнате {room.id_number} оповещены о начале этапа выбора персонажей")


@router.message(F.text == Commands.ADD_CHARACTERS_COMMAND)
async def start_adding_characters(message: Message, state: FSMContext):
    """
    Обработчик команды добавления персонажей игроком.

    Проверяет регистрацию, наличие комнаты, состояние комнаты и переход игрока
    к вводу персонажей, если это возможно.
    """
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not player:
        await message.answer(
            text=Messages.PLAYER_NOT_REGISTERED,
            reply_markup=kb.start_keyboard
        )
        return

    if not room:
        await message.answer(
            text=Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return

    if room.characters_united:
        await message.answer(
            text=Messages.WAIT_FOR_OTHER_PLAYERS
        )
        logging.info('Игрок пытается добавить новых персонажей к уже перемешанным')
        return

    if room.open:
        await message.answer(
            text=Messages.CANT_ADD_CHARACTERS_IN_OPEN_ROOM
        )
        logging.info(f"Игрок {player_id} пытается добавить персонажей в открытую комнату")
        return

    if not player.characters:
        await message.answer(
            reply_markup=ReplyKeyboardRemove(),
            text=Messages.ENTER_FIRST_CHARACTER
        )
        await state.set_state(Reg.character)
        logging.info(f"Игрок {player_id} начинает ввод персонажей")
        return


@router.message(Reg.character)
async def add_character(message: Message, state: FSMContext):
    """
    Функция добавления персонажей игрока
    """
    await state.clear()
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not message.text:
        logging.info('Игрок записал персонажа не текстом')
        await message.answer(
            text=Messages.WRITE_CHARACTER_WITH_TEXT
        )
        await state.set_state(Reg.character)
        return

    if message.text == Commands.EXIT_COMMAND:
        logging.info('Игрок вышел во время ввода персонажей')
        await remove_player_by(message=message)
        return

    if message.text.startswith('/'):
        logging.info('Игрок пытается зарегистрировать кмманду для бота в качестве персонажа')
        await message.answer(
            text=Messages.CANT_REGISTER_COMMAND_AS_CHARACTER
        )
        return

    if message.text == Commands.JOIN_CHARACTERS_COMMAND:
        await message.answer(
            text=Messages.ENTER_ALL_CHARACTERS
        )
        await state.set_state(Reg.character)
        return

    character = message.text
    async with room.ROOM_LOCKS[room.id_number]:
        if not player.can_add_more_characters(room):
            player.characters.append(character)
            logging.info(f'Игрок {player.name} добавил последнего персонажа {character}')
            room.unready_players.remove(player)
            await message.answer(
                reply_markup=ReplyKeyboardRemove(),
                text=(
                    Messages.ALL_CHARACTERS_ADDED +
                    (
                        "\n".join(
                            f"🔹 {i+1}. {name}" for i, name in enumerate(player.characters)
                        )
                    )
                )
            )
            logging.info('Игрок получил список своих персонажей')

            if not player.is_gamemaster:
                await message.answer(
                    text=Messages.WAIT_FOR_CHARACTER_JOIN
                )
            else:
                await message.answer(
                    text=Messages.JOIN_CHARACTERS
                )
            if room.player_is_last():
                await send_message(
                    room.gamemaster,
                    text=Messages.ALL_PLAYERS_ENTERD_CHARACTERS,
                    reply_markup=kb.join_characters_keyboard,
                )
            return

    player.characters.append(character)
    logging.info(f'Игрок {player.name} добавил персонажа {character}')
    await message.answer(
        reply_markup=ReplyKeyboardRemove(),
        text=(
            f'{Messages.ENTER_CHARACTER_NUMBER}'
            f' {player.next_character_number()}'
        )
    )
    await state.set_state(Reg.character)


@router.message(F.text == Commands.JOIN_CHARACTERS_COMMAND)
async def join_characters(message: Message, state: FSMContext):
    """
    Функция для объединения всех персонажей в один список
    """
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not player:
        await message.answer(
            text=Messages.PLAYER_NOT_REGISTERED,
            reply_markup=kb.start_keyboard
        )
        return

    if not room:
        await message.answer(
            text=Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return

    if not player.is_gamemaster:
        await message.answer(
            text=Flags.PLAYER_IS_IMPOSTOR,
            reply_markup=ReplyKeyboardRemove()
        )
        return

    if room.characters_united:
        await message.answer(
            text=Messages.WAIT_FOR_OTHER_PLAYERS
        )
        return

    if room.unready_players:
        await message.answer(
            text=Messages.NOT_ALL_PLAYERS_ENTERED_CHARACTERS,
            reply_markup=kb.join_characters_keyboard
        )
        return

    room.characters_united = True

    room.set_availible_positions()

    for new_player in room.players:
        new_player: Player
        room.characters.extend(new_player.characters)
        new_player.characters.clear()
        await send_message(
            new_player.id_number,
            text=(
                f"{Messages.CHARACTERS_JOINED}"
            ),
            reply_markup=await kb.positions_inline(room.availible_positions)
        )

    await message.answer(
        text=Messages.WHEN_ALL_POSITIONS_ARE_CHOSEN,
        reply_markup=kb.play_keyboard
    )


@router.message(F.text == Commands.PLAYERS_ARE_READY_COMMAND)
async def play(message: Message, state: FSMContext):
    """
    Функция для создания окончательно списка игроков

    Закрепляет игроков за позициями, которые они выбрали, или
    новыми позициями, которые были им присвоенны после исключения игроков
    не выбравших себе позицию. Новые позиция соответствуют порядку возрастания старых
    """
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not player:
        await message.answer(
            text=Messages.PLAYER_NOT_REGISTERED,
            reply_markup=kb.start_keyboard
        )
        return

    if not room:
        await message.answer(
            text=Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return

    if not player.is_gamemaster:
        await message.answer(
            text=Flags.PLAYER_IS_IMPOSTOR,
            reply_markup=ReplyKeyboardRemove()
        )
        return

    extra_players = False
    if room.availible_positions:
        extra_players = True
        logging.info('Некоторые номера не были выбраны')
        if len(room.players) == len(room.availible_positions):
            logging.warning('Ни одна позиция не была выбрана')
            await message.answer(
                text=Messages.CANT_START_GAME_WITHOUT_POSITIONED_PLAYERS
            )
            return

        players_to_delete = []
        for player in room.players:
            if not player.has_order:
                players_to_delete.append(player)

        logging.info(f'Игроки, которые будут удалены из комнаты {players_to_delete}')

        for player in players_to_delete:
            if player in room.players:
                room.players.remove(player)
                player.PLAYERS.pop(player.id_number, None)
                await send_message(
                    player.id_number,
                    text=Messages.YOU_DONT_HAVE_POSITION_GAME_OVER
                )
                if player.is_gamemaster:
                    new_gamemaster: Player = room.players[0]
                    room.gamemaster = new_gamemaster.id_number
                    new_gamemaster.is_gamemaster = True

        room.availible_positions.clear()
        room.refresh_players_positions()

    logging.info('Все позиции распределены')
    room.players_ready = True

    for player in room.players:
        if extra_players:
            await send_message(
                player.id_number,
                reply_markup=ReplyKeyboardRemove(),
                text=(
                    f'{Messages.YOUR_NEW_POSITION}'
                    f'{player.position+1}'
                )
            )
        await send_message(
            player.id_number,
            text=(
                f'{Messages.YOUR_GUESSER}'
                f'{room.get_next_player(player).name}\n'
                f'{Messages.YOUR_RIDDLER}'
                f'{room.get_previous_player(player).name}'
            ),
            reply_markup=ReplyKeyboardRemove()
        )
        if room.check_players_order(player):
            await send_message(
                player.id_number,
                reply_markup=kb.start_round_keyboard,
                text=Messages.FIRST_PLAYER_MOVE
            )


@router.message(F.text == Commands.MAKE_THE_MOVE_COMMAND)
async def start_round(message: Message, state: FSMContext):
    """
    Обработка начала хода игрока:
    - Проверяет регистрацию игрока и принадлежность к комнате.
    - Проверяет, готова ли комната и является ли сейчас ход игрока.
    - Запускает раунд и выдаёт персонажа для объяснения.
    - По окончанию времени или при отсутствии персонажей завершает раунд.
    """
    player_id = get_player_id_by(message=message)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not player:
        logging.warning("Игрок не зарегистрирован")
        await message.answer(
            text=Messages.PLAYER_NOT_REGISTERED,
            reply_markup=kb.start_keyboard
        )
        return

    if not room:
        logging.warning(f"Игрок {player.name} не вошёл в комнату")
        await message.answer(
            text=Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return

    if not room.players_ready:
        logging.info(f"Игрок {player.name} начал ход до подтверждения готовности комнаты")
        await message.answer(
            text=Messages.HOST_HASNT_CLAIMED_PLAYERS_READY
        )
        return

    if not room.check_players_order(player):
        logging.info(f"Игрок {player.name} попытался начать не в свою очередь")
        await message.answer(
            text=Messages.WAIT_FOR_YOUR_TURN
        )
        return

    logging.info(f"Игрок {player.name} начал раунд")

    await message.answer(
        text=Messages.YOUR_MOVE_HAS_BEGUN,
        reply_markup=ReplyKeyboardRemove()
    )
    room.start_round()
    last_message = None

    while True:

        if not get_player_by_id(get_player_id_by(message=message)):
            logging.warning(f"Игрок {player_id} вышел во время раунда")
            await message.answer(
                text='Вы принудительно завершили игру'
            )
            break

        if room.times_up() or not room.characters:
            if not room.characters:
                logging.info(f"В комнате {room.id_number} закончились персонажи. Рестарт.")
                room.reset_characters()
                last_message = None
            await end_round(
                player=player, room=room,
                times_up=room.times_up(),
                last_message=last_message
            )
            break

        if not player.current_character:
            character = room.get_character()
            player.current_character = character
            last_message = await message.answer(
                reply_markup=kb.character_inline,
                text=f'{Messages.EXPLAIN_CHARACTER}{character}'
            )
            logging.info(f"Игроку {player.name} выдан персонаж: {character}")

        await asyncio.sleep(0.1)


@router.callback_query(F.data == CallbackData.NEXT_CHARACTER_DATA)
async def next_character(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает кнопку перехода к следующему персонажу:
    - Проверяет игрока, комнату, порядок хода.
    - Переключает персонажа в комнате, если все условия выполнены.
    - Обрабатывает ошибку двойного нажатия.
    """
    try:
        await callback.answer('')
        player_id = get_player_id_by(callback=callback)
        player: Player = get_player_by_id(player_id) if player_id else None
        room: Room = get_room_by(player.room_id) if player else None

        if not player:
            await callback.message.answer(
                text=Messages.PLAYER_NOT_REGISTERED,
                reply_markup=kb.start_keyboard
            )
            return

        if not room:
            await callback.message.answer(
                text=Messages.ROOM_NOT_ENTERED
            )
            await state.set_state(Reg.room_id)
            return

        if not room.check_players_order(player):
            logging.info(f"Игрок {player.name} попытался действовать вне своей очереди")
            await callback.message.answer(
                text=Messages.WAIT_FOR_YOUR_TURN
            )
            return

        if not player.is_playing:
            logging.info(f"Игрок {player.name} не в активной фазе хода")
            await callback.message.answer(
                text=Messages.START_ROUND,
                reply_markup=kb.start_round_keyboard
            )
            return

        await callback.message.edit_text(
            text=Messages.GUESSED_CHARACTER,
            reply_markup=None
        )

        room.next_character()
        logging.info(f"Игрок {player.name} завершил отгадку и запрошен следующий персонаж")

    except TelegramBadRequest:
        logging.error("Обнаружено двойное нажатие на кнопку")


@router.message(Command(Commands.EXIT_COMMAND))
async def exit(message: Message):
    """
    Обрабатывает команду /exit:
    - Удаляет игрока из текущей сессии (если он зарегистрирован).
    - Логгирует выход игрока.
    """
    logging.info(f"Игрок с ID {message.from_user.id} вышел из игры по команде /exit")

    await remove_player_by(message=message)


@router.callback_query(F.data.startswith('position_'))
async def choose_guesser(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает выбор позиции игроком:
    - Проверяет, что игрок и комната существуют.
    - Проверяет, не занята ли выбранная позиция.
    - Назначает игроку позицию и обновляет интерфейс.
    """
    position = int(callback.data.split('_')[-1])
    player_id = get_player_id_by(callback=callback)
    player: Player = get_player_by_id(player_id) if player_id else None
    room: Room = get_room_by(player.room_id) if player else None

    if not player:
        await callback.message.answer(
            text=Messages.PLAYER_NOT_REGISTERED,
            reply_markup=kb.start_keyboard
        )
        return

    if not room:
        await callback.message.answer(
            text=Messages.ROOM_NOT_ENTERED
        )
        await state.set_state(Reg.room_id)
        return

    if player.has_order:
        await callback.answer(
            Messages.YOU_ALREADY_HAVE_POSITION,
            show_alert=True
        )
        logging.info(f"Игрок {player.name} уже имеет позицию")
        return

    async with room.ROOM_LOCKS[room.id_number]:
        if position not in room.availible_positions:
            logging.warning(f"Позиция {position} недоступна для игрока {player.name}")
            await callback.answer(
                Messages.POSITION_ALREADY_CHOSEN,
                show_alert=True
            )
            await callback.message.edit_reply_markup(
                reply_markup=await kb.positions_inline(room.availible_positions)
            )
            return

        player.set_position(position)
        room.availible_positions.remove(position)
        room.set_players_position(player)
        message = f'\n{player.name} на позиции {position}'
        logging.info(f"Игрок {player.name} выбрал позицию {position}")

    await callback.message.answer(
        text=f'Ваш номер в очереди {position}'
    )
    await callback.message.delete()

    await send_message(
        room.gamemaster,
        text=message,
    )
    logging.info(f"Гейммастеру отправлено сообщение о позиции игрока {player.name}")


@router.message(Command(Commands.SHOW_STATS_COMMAND))
async def show_stats(message: Message):

    if not is_admin(message):
        return

    await message.answer(
        text=(
            f'Игроки:\n{[player.name for id_nuber, player in Player.PLAYERS.items()]}'
            f'\nКомнаты:\n{[room.id_number for id_number, room in Room.ROOMS.items()]}'
            f'\nЗанятые номера:\n{[number for number in Room.TAKEN_ROOM_NUMBERS]}'
            f'\nLocks:\n{[lock for lock in Room.ROOM_LOCKS ]}'
        )
    )


@router.message(Command(Commands.INFO_COMMAND))
async def info(message: Message):
    """
    Обработчик запроса правил

    Отправляет правила игры любому желающему с ними ознакомиться
    """

    await message.answer(
        text=Messages.RULES
    )


@router.message(Command(Commands.SHUTDOWN_COMMAND))
async def shutdown_handler(message: Message):
    """Выключает бота по команде /shutdown"""

    if not is_admin(message):
        return

    await message.answer("🛑 Выключаюсь...")

    await on_shutdown(bot)

    loop = asyncio.get_event_loop()
    loop.stop()
