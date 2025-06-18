import asyncio

from aio_handlers import router, game_over
from aiogram import Dispatcher
from bot import bot, set_bot_commands
from game_classes import Room
from time import time
import logging

dp = Dispatcher()

logging.basicConfig(
    level=logging.INFO,
    format="%(funcName)s- %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)


async def delete_hanging_rooms():
    rooms = Room.ROOMS.values()
    if not rooms:
        logging.info('Нету созданных комнат')
        return
    logging.info('Найдены созданные комнаты, начинаю проверку')
    for room in rooms:
        if (room.created_at - time()) >= 86400:
            await game_over(room)
    await asyncio.sleep(2)


async def main():
    dp.include_router(router)
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
