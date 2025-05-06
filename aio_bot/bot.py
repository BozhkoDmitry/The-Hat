import os

from aiogram import Bot
from aiogram.types import BotCommand
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')

bot = Bot(token=TOKEN, parse_mode="HTML")


async def send_message(chat_id, text, reply_markup=None):
    await bot.send_message(
        chat_id=chat_id, text=text, reply_markup=reply_markup
    )


async def set_bot_commands(bot: Bot):
    """Устанавливаем команды бота при запуске"""
    commands = [
        BotCommand(command="start", description="Начать новую игру"),
        BotCommand(command="exit", description="Покинуть игру"),
        BotCommand(command="info", description="Посмотреть правила"),
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot: Bot, base_url, path):
    """Вызывается при включении бота"""

    await bot.set_webhook(f"{base_url}{path}")
    await set_bot_commands(bot)


async def on_shutdown(bot: Bot):
    """Вызывается при выключении бота"""

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
