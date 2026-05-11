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
from sqlalchemy import select
from bot_database.db import init_db, AsyncSessionLocal
from bot_database.models import BotSettings, Base
from dotenv import load_dotenv

# Loglarni sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
from migrate_db import migrate

async def main():
    logger.info("⏳ Render konflikti oldini olish uchun 60 soniya kutilmoqda...")
    await asyncio.sleep(60)
    
    # Ma'lumotlar bazasini ishga tushirish va Migratsiya
    await init_db()
    await migrate()
    async with AsyncSessionLocal() as session:
        settings_check = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        if not settings_check.scalar_one_or_none():
            new_settings = BotSettings(id=1)
            session.add(new_settings)
            await session.commit()
            logger.info("✅ Boshlang'ich bot sozlamalari yaratildi.")
    
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
    
    rapid_key = os.getenv("RAPIDAPI_KEY")
    if rapid_key:
        logger.info(f"RapidAPI Key found: {rapid_key[:4]}***")
    else:
        logger.error("CRITICAL: RAPIDAPI_KEY NOT FOUND IN ENVIRONMENT!")

    tw_monitor = TwitterMonitor(
        api_key=rapid_key,
        api_host=os.getenv("RAPIDAPI_HOST", "twitter-api45.p.rapidapi.com"),
        bot_token=os.getenv("BOT_TOKEN"),
        translator=translator,
        aiogram_bot=bot
    )
    dp["tw_monitor"] = tw_monitor
    
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
