import asyncio

from aio_handlers import bot, router
from aiogram import Dispatcher

dp = Dispatcher()


async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
