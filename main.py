import asyncio
import sys

# Python 3.14 va Pyrogram uchun loopni eng tepada yaratamiz
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from database.db import init_db
from bot.handlers import start, settings, sources, approval, channels, stats, admin_sys, vip, admin_settings
from bot.middlewares.auth import AuthMiddleware
from services.monitor_tg import TelegramMonitor
from services.monitor_tw import TwitterMonitor
from services.translator import TranslatorService

# Logging sozalamalari
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def start_bot():
    # Ma'lumotlar bazasini ishga tushirish
    await init_db()
    
    # Bot va Dispatcher
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher(storage=MemoryStorage())
    
    # Middleware-ni ro'yxatdan o'tkazish (Xavfsizlik tizimi)
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Tarjimon servisi
    translator = TranslatorService()
    
    # Monitorlarni ishga tushirish
    tg_monitor = TelegramMonitor(
        api_id=os.getenv("API_ID"),
        api_hash=os.getenv("API_HASH"),
        bot_token=os.getenv("BOT_TOKEN"),
        translator=translator,
        aiogram_bot=bot
    )
    
    # Monitor-ni handler-larga uzatish (MUHIM!)
    dp["tg_monitor"] = tg_monitor
    
    # Handlerlarni ro'yxatdan o'tkazish
    dp.include_router(admin_sys.router)
    dp.include_router(admin_settings.router)
    dp.include_router(vip.router)
    dp.include_router(start.router)
    dp.include_router(settings.router)
    dp.include_router(sources.router)
    dp.include_router(approval.router)
    dp.include_router(channels.router)
    dp.include_router(stats.router)
    
    tw_monitor = TwitterMonitor(translator=translator, bot=bot, interval=180)
    
    logger.info("Bot starting...")
    
    # Gathering tasks
    await asyncio.gather(
        dp.start_polling(bot),
        tg_monitor.start(),
        tw_monitor.start()
    )

if __name__ == "__main__":
    try:
        loop.run_until_complete(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
