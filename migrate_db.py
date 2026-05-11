import asyncio
import os
from sqlalchemy import text
from bot_database.db import AsyncSessionLocal, DATABASE_URL
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
            if "sqlite" not in DATABASE_URL.lower():
                await session.execute(text("ALTER TABLE bot_pending_posts ALTER COLUMN link_id DROP NOT NULL;"))
            
            # 3. ON DELETE CASCADE bog'liqliklarini to'g'irlash (Faqat PostgreSQL uchun)
            if "postgresql" in DATABASE_URL.lower() or "postgres" in DATABASE_URL.lower():
                print("Updating Foreign Key constraints for CASCADE DELETE (PostgreSQL)...")
                queries = [
                    # bot_source_links -> bot_output_channels
                    "ALTER TABLE bot_source_links DROP CONSTRAINT IF EXISTS bot_source_links_channel_db_id_fkey",
                    "ALTER TABLE bot_source_links ADD CONSTRAINT bot_source_links_channel_db_id_fkey FOREIGN KEY (channel_db_id) REFERENCES bot_output_channels(id) ON DELETE CASCADE",
                    
                    # bot_source_links -> bot_sources
                    "ALTER TABLE bot_source_links DROP CONSTRAINT IF EXISTS bot_source_links_source_id_fkey",
                    "ALTER TABLE bot_source_links ADD CONSTRAINT bot_source_links_source_id_fkey FOREIGN KEY (source_id) REFERENCES bot_sources(id) ON DELETE CASCADE",
                    
                    # bot_pending_posts -> bot_source_links
                    "ALTER TABLE bot_pending_posts DROP CONSTRAINT IF EXISTS bot_pending_posts_link_id_fkey",
                    "ALTER TABLE bot_pending_posts ADD CONSTRAINT bot_pending_posts_link_id_fkey FOREIGN KEY (link_id) REFERENCES bot_source_links(id) ON DELETE CASCADE",

                    # bot_post_media -> bot_pending_posts
                    "ALTER TABLE bot_post_media DROP CONSTRAINT IF EXISTS bot_post_media_post_id_fkey",
                    "ALTER TABLE bot_post_media ADD CONSTRAINT bot_post_media_post_id_fkey FOREIGN KEY (post_id) REFERENCES bot_pending_posts(id) ON DELETE CASCADE"
                ]
                for q in queries:
                    await session.execute(text(q))
            
            await session.commit()
            print("✅ Baza muvaffaqiyatli yangilandi!")
        except Exception as e:
            print(f"❌ Xatolik yuz berdi: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(migrate())
