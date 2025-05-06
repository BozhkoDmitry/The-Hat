import asyncio

from aio_handlers import router
from aiogram import Dispatcher
from bot import bot, set_bot_commands

dp = Dispatcher()


async def main():
    dp.include_router(router)
    await set_bot_commands(bot)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
