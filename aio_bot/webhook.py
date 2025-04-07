import asyncio

from bot import bot, on_shutdown, on_startup
from aio_handlers import router
from aiogram import Dispatcher
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler, setup_application
)
from functools import partial
from aiohttp import web
import logging

# Webserver settings
# bind localhost only to prevent any external access
WEB_SERVER_HOST = "::"
# Port for incoming request from reverse proxy. Should be any available port
WEB_SERVER_PORT = 8350

# Path to webhook route, on which Telegram will send requests
WEBHOOK_PATH = "/aio_bot/"

# Base URL for webhook will be used to generate webhook URL for Telegram,
# in this example it is used public DNS with HTTPS support
BASE_WEBHOOK_URL = "https://thehat.alwaysdata.net/"


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)

    dp.startup.register(partial(on_startup, base_url=BASE_WEBHOOK_URL, path=WEBHOOK_PATH))
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
    await site.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logging.info('Бот остановлен')

if __name__ == "__main__":
    asyncio.run(main())
