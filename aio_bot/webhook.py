import asyncio

from bot import bot, on_shutdown
from aio_handlers import router
from aiogram import Dispatcher, Bot
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler, setup_application
)
from aiohttp import web

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


async def set_bot_commands(bot: Bot):
    """Устанавливаем команды бота при запуске"""
    commands = [
        BotCommand(command="start", description="Начать новую игру"),
        BotCommand(command="exit", description="Покинуть игру"),
        BotCommand(command="info", description="Посмотреть правила"),
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot: Bot) -> None:

    await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}")
    await set_bot_commands(bot)


async def main() -> None:
    dp = Dispatcher()
    dp.include_router(router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
    await site.start()

    print(f"Webhook сервер запущен: {BASE_WEBHOOK_URL}{WEBHOOK_PATH}")

    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("Бот выключается...")

if __name__ == "__main__":
    asyncio.run(main())
