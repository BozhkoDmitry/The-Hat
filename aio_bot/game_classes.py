import os
from random import choice, randint
from time import time

from aiogram.types import Message
from dotenv import load_dotenv

load_dotenv()


class Player:
    PLAYERS = {}

    class Messages:
        CREATE_OR_ENTER_ROOM = os.getenv('CREATE_OR_ENTER_ROOM')
        EXIT_PREVIOUS_GAME = os.getenv('EXIT_PREVIOUS_GAME')
        ENTER_YOUR_NAME = os.getenv('ENTER_YOUR_NAME')
        ENTER_NUMBER_OF_CHARACTERS = os.getenv('ENTER_NUMBER_OF_CHARACTERS')
        ENTER_FIRST_CHARACTER = os.getenv('ENTER_FIRST_CHARACTER')
        ENTER_ROOM_ID = os.getenv('ENTER_ROOM_ID')
        ENTER_POSITION = os.getenv('ENTER_POSITION')
        OK = os.getenv('OK')
        ROOM_ENTERED = os.getenv('ROOM_ENTERED')
        ROOM_IS_CLOSED = os.getenv('ROOM_IS_CLOSED')
        PLAYER_NOT_REGISTERED = os.getenv('PLAYER_NOT_REGISTERED')
        CLOSE_ROOM = os.getenv('CLOSE_ROOM')
        PLAYER_IS_IMPOSTOR = os.getenv('PLAYER_IS_IMPOSTOR')
        ROOM_NOT_ENTERED = os.getenv('ROOM_NOT_ENTERED')
        WAIT_FOR_OTHER_PLAYERS = os.getenv('WAIT_FOR_OTHER_PLAYERS')
        WAIT_FOR_YOUR_TURN = os.getenv('WAIT_FOR_YOUR_TURN')
        FIRST_PLAYER_MOVE = os.getenv('FIRST_PLAYER_MOVE')
        YOUR_MOVE = os.getenv('YOUR_MOVE')
        ALL_CHARACTERS_GUESSED = os.getenv('ALL_CHARACTERS_GUESSED')
        START_ROUND = os.getenv('START_ROUND')
        FINISH_ROUND = os.getenv('FINISH_ROUND')
        GAME_EXITED = os.getenv('GAME_EXITED')
        GAME_OVER = os.getenv('GAME_OVER')
        PLAYER_NOT_ORDERED = os.getenv('PLAYER_NOT_ORDERED')
        READY_TO_PLAY = os.getenv('READY_TO_PLAY')
        JOIN_CHARACTERS = os.getenv('JOIN_CHARACTERS')
        ENTER_ORDER = os.getenv('ENTER_ORDER')
        CHARACTERS_JOINED = os.getenv('CHARACTERS_JOINED')
        ADD_CHARACTERS = os.getenv('ADD_CHARACTERS')
        NOT_ENOUGH_CHARACTERS = os.getenv('NOT_ENOUGH_CHARACTERS')
        MESSAGE_NOT_INTEGER = os.getenv('MESSAGE_NOT_INTEGER')
        POSITION_UNAVAILIBLE = os.getenv('POSITION_UNAVAILIBLE')
        ROOM_NUMBER_OUT_OF_RANGE = os.getenv('ROOM_NUMBER_OUT_OF_RANGE')
        ROOM_DOESNT_EXIST = os.getenv('ROOM_DOESNT_EXIST')

    def __init__(self, id_number):
        self.id_number = id_number
        self.room_id = None
        self.name = None
        self.position = None
        self.score = 0
        self.round_score = 0
        self.characters = []
        self.current_character = None
        self.is_gamemaster = False
        self.is_playing = False
        self.has_order = False
        self.guesser = None
        self.riddler = None
        self.is_chosen = False

    def can_add_more_characters(self, room):
        return self.next_character_number() < room.number_of_characters

    def next_character_number(self):
        return len(self.characters)+1

    def check_room_id(self, message: Message):
        try:
            value = int(message.text)
            if value < Room.MIN_ROOM_NUMBER or value > Room.MAX_ROOM_NUMBER:
                return self.Messages.ROOM_NUMBER_OUT_OF_RANGE
            elif value not in Room.TAKEN_ROOM_NUMBERS:
                return self.Messages.ROOM_DOESNT_EXIST
            else:
                return self.Messages.OK
        except ValueError:
            return self.Messages.MESSAGE_NOT_INTEGER

    def check_number_of_characters(self, message: Message):
        try:
            value = int(message.text)
            if value < Room.MIN_NUMBER_OF_CHARACTERS:
                return self.Messages.NOT_ENOUGH_CHARACTERS
            elif not self.is_gamemaster:
                return self.Messages.PLAYER_IS_IMPOSTOR
            else:
                return self.Messages.OK
        except ValueError:
            return self.Messages.MESSAGE_NOT_INTEGER

    def set_position(self, position):
        self.position = position-1
        self.has_order = True

    def get_point(self):
        self.score += 1
        self.round_score += 1


class Room:
    MIN_NUMBER_OF_CHARACTERS = 1
    MIN_ROOM_NUMBER = 1000
    MAX_ROOM_NUMBER = 9999
    TAKEN_ROOM_NUMBERS = []
    ROOMS = {}

    def __init__(self, gamemaster_id):
        self.players = []
        self.unready_players = []
        self.__id_number = self.set_room_id()
        self.characters = []
        self.guessed_characters = []
        self.availible_positions = []
        self.gamemaster = gamemaster_id
        self.open = True
        self.number_of_characters = 0
        self.__round_finishes = None
        self.current_player_position = 0
        self.round_duration = 60
        self.round = 1
        self.guesser = None
        self.characters_united = False
        self.order_set = False
        self.players_ready = False

    @property
    def id_number(self):
        return self.__id_number

    @classmethod
    def set_room_id(cls):
        while True:
            room_id = randint(cls.MIN_ROOM_NUMBER, cls.MAX_ROOM_NUMBER)
            if room_id not in cls.TAKEN_ROOM_NUMBERS:
                cls.TAKEN_ROOM_NUMBERS.append(room_id)
                break
        return room_id

    def check_position(self, message: Message):
        try:
            position = int(message.text)
            if position not in self.availible_positions:
                return Player.Messages.POSITION_UNAVAILIBLE
            else:
                return Player.Messages.OK
        except ValueError:
            return Player.Messages.MESSAGE_NOT_INTEGER

    def add_player(self, player: Player):
        if player not in self.players:
            self.players.append(player)

    def get_character(self):
        while True:
            if self.characters:
                character = choice(self.characters)
                if character not in self.guessed_characters:
                    break
            else:
                return Player.Messages.ALL_CHARACTERS_GUESSED
        return character

    def get_next_player(self, player: Player):
        position = player.position+1
        return self.players[position % len(self.players)]

    def get_previous_player(self, player: Player):
        position = player.position-1
        return self.players[position]

    def set_timer(self):
        self.__round_finishes = float(time())+self.round_duration

    def times_up(self):
        return int(time()) > self.__round_finishes

    def reset_characters(self):
        for character in self.guessed_characters:
            self.characters.append(character)
        self.guessed_characters.clear()

    def refresh_availible_positions(self, player: Player):
        position = player.position + 1
        self.availible_positions.remove(position)

    def refresh_players_positions(self):
        for i in range(len(self.players)):
            player: Player = self.players[i]
            player.position = i

    def refresh_characters(self, player: Player):
        if player.current_character:
            self.characters.remove(player.current_character)
            self.guessed_characters.append(player.current_character)
            player.current_character = None

    def last_round(self):
        return self.round > 3

    def check_players_order(self, player: Player):
        return player.position == self.current_player_position

    def next_round(self):
        self.round += 1

    def start_round(self):
        riddler: Player = self.players[self.current_player_position]
        guesser: Player = self.get_next_player(riddler)
        riddler.is_playing = True
        guesser.is_playing = True
        self.set_timer()

    def end_round(self):
        riddler: Player = self.players[self.current_player_position]
        guesser: Player = self.get_next_player(riddler)
        self.current_player_position = guesser.position
        riddler.current_character = None
        riddler.round_score = 0
        guesser.round_score = 0
        guesser.is_playing = False
        riddler.is_playing = False

    def new_stage(self):
        for player in self.players:
            self.unready_players.append(player)

    def close(self):
        self.open = False
        self.new_stage()

    def set_players_position(self, player: Player):
        self.players[player.position] = player

    def set_availible_positions(self):
        for i in range(1, len(self.players)+1):
            self.availible_positions.append(i)

    def players_have_order(self):
        for player in self.players:
            player: Player
            if not player.has_order:
                return False
        return True

    def player_is_last(self):
        return not self.unready_players

    def next_character(self):
        riddler: Player = self.players[self.current_player_position]
        guesser: Player = self.get_next_player(riddler)
        self.refresh_characters(riddler)
        riddler.get_point()
        if riddler != guesser:
            guesser.get_point()
