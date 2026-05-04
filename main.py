import os
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import start, sources, channels, approval, settings, vip, admin_sys, admin_settings, stats
from bot.middlewares.auth import AuthMiddleware
from services.monitor_tg import TelegramMonitor
from services.monitor_tw import TwitterMonitor
from services.translator import TranslatorService
from database.db import init_db
from dotenv import load_dotenv

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

async def main():
    # Ma'lumotlar bazasini ishga tushirish
    await init_db()
    
    # Bot va Dispatcher
    bot = Bot(token=os.getenv("BOT_TOKEN"))
    dp = Dispatcher(storage=MemoryStorage())
    
    # Middleware-ni ro'yxatdan o'tkazish
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Tarjimon servisi
    translator = TranslatorService()
    
    # Monitorlarni ishga tushirish
    tg_monitor = TelegramMonitor(
        api_id=int(os.getenv("API_ID")),
        api_hash=os.getenv("API_HASH"),
        bot_token=os.getenv("BOT_TOKEN"),
        translator=translator,
        aiogram_bot=bot,
        session_string=os.getenv("TELEGRAM_SESSION")
    )
    
    # Monitor-ni handler-larga uzatish
    dp["tg_monitor"] = tg_monitor
    
    # Handlerlarni ro'yxatdan o'tkazish
    dp.include_router(vip.router) # VIP birinchi
    dp.include_router(admin_sys.router)
    dp.include_router(admin_settings.router)
    dp.include_router(start.router)
    dp.include_router(sources.router)
    dp.include_router(approval.router)
    dp.include_router(settings.router)
    dp.include_router(channels.router)
    dp.include_router(stats.router)
    
    tw_monitor = TwitterMonitor(translator=translator, bot=bot, interval=180)
    
    logger.info("Bot starting with Telethon support...")
    logger.info(">>> BOT STARTING - VERSION 2.5 FINAL - ALL FIXES APPLIED <<<")
    logger.info(">>> BOT STARTING - VERSION 2.5 FINAL - ALL FIXES APPLIED <<<")
    logger.info(">>> BOT STARTING - VERSION 2.5 FINAL - ALL FIXES APPLIED <<<")
    
    # Monitorlarni fonda ishga tushirish
    asyncio.create_task(tg_monitor.start())
    asyncio.create_task(tw_monitor.start())
    
    # Botni polling rejimida boshlash
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"FATAL STARTUP ERROR: {e}", exc_info=True)
