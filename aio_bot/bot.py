import os
from aiogram import Bot
from dotenv import load_dotenv


load_dotenv()

TOKEN = os.getenv('TOKEN')

bot = Bot(token=TOKEN)


async def send_message(chat_id, text, reply_markup=None):
    await bot.send_message(
        chat_id=chat_id, text=text, reply_markup=reply_markup
    )


async def on_shutdown(bot: Bot) -> None:
    """Вызывается при выключении бота"""
    print("🛑 Бот завершает работу...")

    # Удаляем вебхук
    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Вебхук удален!")

    # Закрываем сессию
    await bot.session.close()
    print("✅ Сессия закрыта!")
