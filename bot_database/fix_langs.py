import asyncio
from sqlalchemy import select, update
from database.db import AsyncSessionLocal
from database.models import OutputChannel

async def fix_channels():
    async with AsyncSessionLocal() as session:
        # Tili NULL bo'lgan kanallarni 'uz' ga o'zgartiramiz
        await session.execute(
            update(OutputChannel)
            .where(OutputChannel.target_lang == None)
            .values(target_lang='uz')
        )
        await session.commit()
        print("✅ Barcha kanallar tili 'uz' ga sozlandi.")

if __name__ == "__main__":
    asyncio.run(fix_channels())
