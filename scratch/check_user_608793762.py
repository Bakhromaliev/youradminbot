import asyncio
from sqlalchemy import select
from bot_database.db import AsyncSessionLocal
from bot_database.models import User, Source, SourceChannelLink, OutputChannel

async def check_user(tg_id):
    async with AsyncSessionLocal() as session:
        # 1. Userni tekshirish
        res = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = res.scalar_one_or_none()
        
        if not user:
            print(f"❌ Foydalanuvchi (ID: {tg_id}) bazada topilmadi.")
            return

        print(f"✅ Foydalanuvchi: {user.username or 'No Username'}")
        print(f"   Tasdiqlangan: {user.is_approved}")
        print(f"   VIP: {user.is_vip}")
        print(f"   Admin Kanal: {user.admin_channel_id or 'Shaxsiy chat'}")

        # 2. Manbalarni tekshirish
        src_res = await session.execute(select(Source).where(Source.user_id == user.id))
        sources = src_res.scalars().all()
        print(f"\n📡 Manbalar ({len(sources)} ta):")
        for s in sources:
            print(f"   - {s.source_id} ({s.source_type})")

        # 3. Kanallarni tekshirish
        ch_res = await session.execute(select(OutputChannel).where(OutputChannel.user_id == user.id))
        channels = ch_res.scalars().all()
        print(f"\n📢 Kanallar ({len(channels)} ta):")
        for c in channels:
            print(f"   - {c.channel_name} ({c.alphabet})")

        # 4. Bog'liqliklarni (Links) tekshirish
        link_res = await session.execute(select(SourceChannelLink).where(SourceChannelLink.user_id == user.id))
        links = link_res.scalars().all()
        print(f"\n🔗 Bog'liqliklar (Links) ({len(links)} ta):")
        for l in links:
            print(f"   - Manba ID: {l.source_id} -> Kanal DB ID: {l.channel_db_id}")

if __name__ == "__main__":
    asyncio.run(check_user(608793762))
