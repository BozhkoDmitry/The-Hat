import os

from dotenv import load_dotenv
from game_classes import Player, Room
from telebot import TeleBot
from telebot.types import (KeyboardButton, Message, ReplyKeyboardMarkup,
                           ReplyKeyboardRemove)

load_dotenv()

TOKEN = os.getenv('TOKEN')


bot = TeleBot(TOKEN)


def send_message(chat_id, text, markup=None):
    bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)


def next_step(message: Message, func):
    clear_handler(message)
    bot.register_next_step_handler(message, func)


def clear_handler(message: Message):
    bot.clear_step_handler_by_chat_id(get_id(message))


def get_id(message: Message):
    return message.from_user.id


def get_player_by(message: Message = None, player_id=False):
    if player_id:
        return Player.PLAYERS.get(player_id)
    return Player.PLAYERS.get(get_id(message))


def get_room_by(message: Message = None, room_id=False):
    if not room_id:
        player: Player = get_player_by(message)
        return Room.ROOMS.get(player.room_id) if player else None
    return Room.ROOMS.get(room_id)


def create_player(message: Message):
    if not get_player_by(message):
        player = Player(get_id(message))
        player.PLAYERS[player.id_number] = player
        return player
    else:
        return None


def remove_player(message: Message):
    player: Player = get_player_by(message)
    room: Room = get_room_by(message)
    if room and player:
        room.players.remove(player)
        del player.PLAYERS[player.id_number]
        del player
    elif player:
        del player.PLAYERS[player.id_number]
        del player


def create_room(gamemaster: Player):
    room = Room(gamemaster.id_number)
    gamemaster.room_id = room.id_number
    gamemaster.is_gamemaster = True
    room.players.append(gamemaster)
    room.ROOMS[room.id_number] = room
    return room


def add_buttons(commands: list):
    buttons = []
    for command in commands:
        buttons.append(KeyboardButton(command))
    return buttons


def set_markup(commands: list):
    markup = ReplyKeyboardMarkup(
        one_time_keyboard=True, resize_keyboard=True
    )
    buttons = add_buttons(commands)
    for button in buttons:
        markup.add(button)
    return markup


def remove_markup():
    return ReplyKeyboardRemove()


def game_over(message: Message):
    room: Room = get_room_by(message)
    if room:
        for player in room.players:
            player: Player
            del player.PLAYERS[player.id_number]
            del player
        room.TAKEN_ROOM_NUMBERS.remove(room.id_number)
        del room.ROOMS[room.id_number]
        del room


@bot.message_handler(commands=['start'])
def start(message: Message):
    player: Player = get_player_by(message)
    room: Room = get_room_by(message)

    if not (player and room):
        send_message(
            get_id(message),
            markup=set_markup(['/new_room', '/enter_room']),
            text=Player.Messages.CREATE_OR_ENTER_ROOM
        )
        return None

    send_message(
        get_id(message),
        markup=set_markup(['/exit']),
        text=Player.Messages.EXIT_PREVIOUS_GAME
    )


@bot.message_handler(commands=['enter_room'])
def enter_room(message: Message):
    player: Player = create_player(message)

    if player:
        send_message(
            player.id_number,
            markup=remove_markup(),
            text=player.Messages.ENTER_YOUR_NAME
        )
        next_step(message, add_name)
        return None

    send_message(
        get_id(message),
        markup=set_markup(['/start']),
        text=Player.Messages.EXIT_PREVIOUS_GAME
    )


def add_name(message: Message):
    player: Player = get_player_by(message)

    if message.text == '/exit':
        send_message(
            player.id_number,
            markup=set_markup(['/start']),
            text=player.Messages.GAME_EXITED
        )
        remove_player(message)
        clear_handler(message)
        return None

    player.name = message.text

    if player.is_gamemaster:
        send_message(
            player.id_number,
            text=player.Messages.ENTER_NUMBER_OF_CHARACTERS
        )
        next_step(message, set_number_of_characters)
        return None

    send_message(
        player.id_number,
        text=player.Messages.ENTER_ROOM_ID
    )
    next_step(message, add_player)


def add_player(message: Message):
    player: Player = get_player_by(message)
    result = player.check_room_id(message)

    if message.text == '/exit':
        send_message(
            player.id_number,
            markup=set_markup(['/start']),
            text=player.Messages.GAME_EXITED
        )
        remove_player(message)
        clear_handler(message)
        return None

    if result == player.Messages.OK:
        room_id = int(message.text)
        room: Room = get_room_by(room_id=room_id)
        if not room.open:
            send_message(
                player.id_number,
                text=player.Messages.ROOM_IS_CLOSED
            )
            next_step(message, add_player)
            return None
        if player in room.players:
            send_message(
                player.id_number,
                text=player.Messages.ROOM_ENTERED
            )
            clear_handler(message)
            return None
        room.players.append(player)
        player.room_id = room_id
        send_message(
            player.id_number,
            text=player.Messages.ROOM_ENTERED
        )
        send_message(
            room.gamemaster,
            text=f'Игрок {player.name} вошёл в комнату'
        )
        clear_handler(message)
        return None

    send_message(
        player.id_number,
        text=result
    )
    clear_handler(message)
    if result != player.Messages.PLAYER_IS_IMPOSTOR:
        next_step(message, set_number_of_characters)


@bot.message_handler(commands=['new_room'])
def new_room(message: Message):
    gamemaster: Player = create_player(message)
    if gamemaster:
        create_room(gamemaster),
        send_message(
            gamemaster.id_number,
            markup=remove_markup(),
            text=gamemaster.Messages.ENTER_YOUR_NAME
        )
        next_step(message, add_name)
        return None

    send_message(
        get_id(message),
        markup=remove_markup(),
        text=Player.Messages.EXIT_PREVIOUS_GAME
    )


def set_number_of_characters(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)
    result = player.check_number_of_characters(message)

    if message.text == '/exit':
        send_message(
            player.id_number,
            markup=set_markup(['/start']),
            text=player.Messages.GAME_EXITED
        )
        remove_player(message)
        clear_handler(message)
        return None

    if result == player.Messages.OK:
        room.number_of_characters = int(message.text)
        send_message(
            player.id_number,
            text=player.Messages.CLOSE_ROOM
        )
        send_message(
            player.id_number,
            markup=set_markup(['/close_room']),
            text=f'Номер вашей комнаты: {room.id_number}. '
        )
        clear_handler(message)
        return None

    send_message(
        player.id_number,
        text=result
    )
    clear_handler(message)
    if result != player.Messages.PLAYER_IS_IMPOSTOR:
        next_step(message, set_number_of_characters)


@bot.message_handler(commands=['close_room'])
def close_room(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)

    if not (room and player):
        if not room:
            if not player:
                send_message(
                    get_id(message),
                    markup=set_markup(['/start']),
                    text=Player.Messages.PLAYER_NOT_REGISTERED
                )
                return None
            send_message(
                player.id_number,
                text=player.Messages.ROOM_NOT_ENTERED
            )
            next_step(message, add_player)
            return None

    if player.is_gamemaster:
        if room.open and player.is_ignored:
            room.close()
            for player in room.players:
                player.is_ignored = False
                send_message(
                    player.id_number,
                    markup=set_markup(['/add_characters']),
                    text=player.Messages.ADD_CHARACTERS
                )
                if not player.is_gamemaster:
                    send_message(
                        player.id_number,
                        text=(
                            'Количесво персонажей на эту игру - '
                            f'{room.number_of_characters}.'
                        )
                    )
            clear_handler(message)
        else:
            send_message(
                player.id_number,
                markup=remove_markup(),
                text=player.Messages.ROOM_IS_CLOSED
            )
            clear_handler(message)
    else:
        send_message(
            player.id_number,
            markup=remove_markup(),
            text=player.Messages.PLAYER_IS_IMPOSTOR
        )
        clear_handler(message)


@bot.message_handler(commands=['add_characters'], content_types=['text'])
def add_character(message: Message):
    player: Player = get_player_by(message)
    room: Room = get_room_by(message)

    if not message.text:
        send_message(
            get_id(message),
            text='Персонажа можно записать только текстом'
        )
        next_step(message, add_character)
        return None

    if not (room and player):
        if not room:
            if not player:
                send_message(
                    get_id(message),
                    markup=set_markup(['/start']),
                    text=Player.Messages.PLAYER_NOT_REGISTERED
                )
                return None
            send_message(
                player.id_number,
                text=player.Messages.ROOM_NOT_ENTERED
            )
            next_step(message, add_player)
            return None

    if message.text == '/exit':
        send_message(
            player.id_number,
            markup=set_markup(['/start']),
            text=player.Messages.GAME_EXITED
        )
        remove_player(message)
        clear_handler(message)
        return None

    if room.characters_united:
        send_message(
            player.id_number,
            text=player.Messages.WAIT_FOR_OTHER_PLAYERS
        )
        clear_handler(message)
        return None

    if message.text == '/add_characters':
        send_message(
            player.id_number,
            markup=remove_markup(),
            text=player.Messages.ENTER_FIRST_CHARACTER
        )
        next_step(message, add_character)
        return None

    character = message.text

    if not player.can_add_more_characters(room):
        player.characters.append(character)
        send_message(
            player.id_number,
            markup=remove_markup(),
            text=(
                'Вы добавили всех персонажей: '
                f"{', '.join(player.characters)}"
            )
        )
        if player.is_gamemaster:
            send_message(
                player.id_number,
                markup=set_markup(['/join']),
                text=player.Messages.JOIN_CHARACTERS
            )
        player.is_ignored = True
        clear_handler(message)
        return None

    player.characters.append(character)
    send_message(
        player.id_number,
        markup=remove_markup(),
        text=(
            'Ведите персонажа № '
            f' {player.next_character_number()}'
        )
    )
    next_step(message, add_character)


@bot.message_handler(commands=['join'])
def unite_characters(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)

    if not (room and player):
        if not room:
            if not player:
                send_message(
                    get_id(message),
                    markup=set_markup(['/start']),
                    text=Player.Messages.PLAYER_NOT_REGISTERED
                )
                return None
            send_message(
                player.id_number,
                text=player.Messages.ROOM_NOT_ENTERED
            )
            next_step(message, add_player)
            return None

    if not player.is_gamemaster:
        send_message(
            player.id_number,
            markup=remove_markup(),
            text=player.Messages.PLAYER_IS_IMPOSTOR
        )
        return None

    if room.characters_united:
        send_message(
            player.id_number,
            markup=set_markup(['/enter_order']),
            text=player.Messages.CHARACTERS_JOINED
        )
        return None

    room.characters_united = True
    position = 1
    for player in room.players:
        room.characters.extend(player.characters)
        send_message(
            player.id_number,
            text=player.Messages.CHARACTERS_JOINED
        )
        send_message(
            player.id_number,
            markup=set_markup(['/enter_order']),
            text=player.Messages.ENTER_ORDER
        )
        room.availible_positions.append(position)
        position += 1


@bot.message_handler(commands=['enter_order'])
def enter_order(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)

    if not (room and player):
        if not room:
            if not player:
                send_message(
                    get_id(message),
                    markup=set_markup(['/start']),
                    text=Player.Messages.PLAYER_NOT_REGISTERED
                )
                return None
            send_message(
                player.id_number,
                text=player.Messages.ROOM_NOT_ENTERED
            )
            next_step(message, add_player)
            return None

    if not room.characters_united:
        send_message(
            player.id_number,
            text=player.Messages.WAIT_FOR_OTHER_PLAYERS
        )
        return None

    send_message(
        player.id_number,
        markup=remove_markup(),
        text=player.Messages.ENTER_POSITION
    )
    next_step(message, set_order)


def set_order(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)
    result = room.check_position(message)

    if message.text == '/exit':
        send_message(
            player.id_number,
            markup=set_markup(['/start']),
            text=player.Messages.GAME_EXITED
        )
        remove_player(message)
        clear_handler(message)
        return None

    if result == player.Messages.OK:
        player.set_position(message)
        room.set_players_position(player)
        send_message(
            player.id_number,
            markup=set_markup(['/play']),
            text=player.Messages.READY_TO_PLAY
        )
        clear_handler(message)
        return None

    send_message(
        player.id_number,
        markup=remove_markup(),
        text=result
    )
    next_step(message, set_order)


@bot.message_handler(commands=['play'])
def play(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)

    if not (room and player):
        if not room:
            if not player:
                send_message(
                    get_id(message),
                    markup=set_markup(['/start']),
                    text=Player.Messages.PLAYER_NOT_REGISTERED
                )
                return None
            send_message(
                player.id_number,
                text=player.Messages.ROOM_NOT_ENTERED
            )
            next_step(message, add_player)
            return None

    if not player.has_order:
        send_message(
            player.id_number,
            markup=set_markup(['/enter_order']),
            text=player.Messages.PLAYER_NOT_ORDERED
        )
        return None

    player.is_ignored = True
    player.is_ready = True

    if not room.player_is_last(player):
        send_message(
            player.id_number,
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
        send_message(
            player.id_number,
            text=(
                f'Вы загадываете слова игроку {next_player.name} '
                f'и отгадывате слова игрока {previous_player.name}'
            )
        )
        if room.check_players_order(player):
            send_message(
                player.id_number,
                markup=set_markup(['/start_round']),
                text=player.Messages.FIRST_PLAYER_MOVE
            )


@bot.message_handler(commands=['start_round'])
def start_round(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)

    if not (room and player):
        if not room:
            if not player:
                send_message(
                    get_id(message),
                    markup=set_markup(['/start']),
                    text=Player.Messages.PLAYER_NOT_REGISTERED
                )
                return None
            send_message(
                player.id_number,
                text=player.Messages.ROOM_NOT_ENTERED
            )
            next_step(message, add_player)
            return None

    if not room.check_players_are_ready():
        send_message(
            player.id_number,
            text=player.Messages.WAIT_FOR_OTHER_PLAYERS
        )
        return None

    if not room.check_players_order(player):
        send_message(
            player.id_number,
            text=player.Messages.WAIT_FOR_YOUR_TURN
        )
        return None

    guesser: Player = room.get_next_player(player)
    player.is_playing = True
    guesser.is_playing = True
    room.set_timer()

    while not room.times_up():

        if not room.characters:
            room.reset_charracters()
            if not room.last_round():
                for player in room.players:
                    send_message(
                        player.id_number,
                        markup=remove_markup(),
                        text=player.Messages.ALL_CHARACTERS_GUESSED
                    )
                send_message(
                    player.id_number,
                    text=(
                        'Количество угаданных персонажей в этом '
                        f'раунде {player.round_score}'
                    )
                )
                send_message(
                    guesser.id_number,
                    text=(
                        'Количество угаданных персонажей в этом '
                        f'раунде {guesser.round_score}'
                    )
                )
                send_message(
                    guesser.id_number,
                    markup=set_markup(['/start_round']),
                    text=guesser.Messages.YOUR_MOVE
                )
                room.end_round(player)
                room.next_round()
                break

            for player in room.players:
                send_message(
                    player.id_number,
                    markup=remove_markup(),
                    text=player.Messages.GAME_OVER
                )
                send_message(
                    player.id_number,
                    text=(
                        'Количество ваших очков: '
                        f'{player.score}'
                    )
                )
                send_message(
                    player.id_number,
                    markup=set_markup(['/start']),
                    text=(
                        'Если хотите сыграть ещё раз введите '
                        'команду "/start"'
                    )
                )
            game_over(message)
            break

        if not player.current_character:
            character = room.get_character()
            player.current_character = character
            send_message(
                player.id_number,
                markup=set_markup(['/next']),
                text=f'Объясните персонажа {character}'
            )

    send_message(
        player.id_number,
        markup=remove_markup(),
        text=(
            'Время вышло. Количество угаданных '
            'персонажей: '
            f'{player.round_score}'
            )
    )
    send_message(
        guesser.id_number,
        markup=remove_markup(),
        text=(
            'Время вышло. Количество угаданных '
            'персонажей: '
            f'{guesser.round_score}'
        )
    )
    send_message(
        guesser.id_number,
        markup=set_markup(['/start_round']),
        text=player.Messages.YOUR_MOVE
    )
    room.end_round(player)


@bot.message_handler(commands=['next'])
def character_guessed(message: Message):
    player: Player = get_player_by(message)
    room: Room = get_room_by(message)

    if not (room and player):
        if not room:
            if not player:
                send_message(
                    get_id(message),
                    markup=set_markup(['/start']),
                    text=Player.Messages.PLAYER_NOT_REGISTERED
                )
                return None
            send_message(
                player.id_number,
                text=player.Messages.ROOM_NOT_ENTERED
            )
            next_step(message, add_player)
            return None

    if not room.check_players_order(player):
        send_message(
            player.id_number,
            text=player.Messages.WAIT_FOR_YOUR_TURN
        )
        clear_handler(message)
        return None

    if not player.is_playing:
        send_message(
            player.id_number,
            markup=set_markup(['/start_round']),
            text=player.Messages.START_ROUND
        )
        return None

    room.refresh_characters(player)
    guesser: Player = room.get_next_player(player)
    player.get_point()
    guesser.get_point()
    clear_handler(message)


@bot.message_handler(commands=['exit'])
def exit(message: Message):
    room: Room = get_room_by(message)
    player: Player = get_player_by(message)
    if room and player:
        if player.is_playing:
            send_message(
                player.id_number,
                text=player.Messages.FINISH_ROUND
            )
            return None
        send_message(
            player.id_number,
            markup=set_markup(['/start']),
            text=player.Messages.GAME_EXITED
        )
        remove_player(message)
    elif player:
        remove_player(message)


@bot.message_handler(commands=['/destroy_room'])
def destroy_room(message: Message):
    room: Room = get_room_by(message)
    if room:
        if get_id(message) == room.gamemaster:
            game_over(message)


if __name__ == '__main__':
    bot.infinity_polling()
