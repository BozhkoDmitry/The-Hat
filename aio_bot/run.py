import asyncio

from aio_handlers import router
from aiogram import Dispatcher
from aio_handlers import bot

dp = Dispatcher()


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
