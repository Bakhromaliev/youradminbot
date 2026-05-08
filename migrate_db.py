import asyncio
import os
from sqlalchemy import text
from bot_database.db import AsyncSessionLocal
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    print("🚀 Baza migratsiyasi boshlandi...")
    async with AsyncSessionLocal() as session:
        try:
            # 1. bot_users jadvaliga admin_channel ustunlarini qo'shish
            print("Checking bot_users columns...")
            await session.execute(text("ALTER TABLE bot_users ADD COLUMN IF NOT EXISTS admin_channel_id VARCHAR;"))
            await session.execute(text("ALTER TABLE bot_users ADD COLUMN IF NOT EXISTS admin_channel_name VARCHAR;"))
            
            # 2. bot_pending_posts jadvaliga source_id ustunini qo'shish
            print("Checking bot_pending_posts columns...")
            await session.execute(text("ALTER TABLE bot_pending_posts ADD COLUMN IF NOT EXISTS source_id INTEGER REFERENCES bot_sources(id);"))
            await session.execute(text("ALTER TABLE bot_pending_posts ALTER COLUMN link_id DROP NOT NULL;"))
            
            await session.commit()
            print("✅ Baza muvaffaqiyatli yangilandi!")
        except Exception as e:
            print(f"❌ Xatolik yuz berdi: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate())
