import logging
from aiogram import Router, types
from sqlalchemy import select, func
from bot_database.db import AsyncSessionLocal
from bot_database.models import User, Source, OutputChannel, PendingPost
from bot.utils.texts import get_text
from bot.utils.keyboards import get_main_menu_keyboard

logger = logging.getLogger(__name__)
router = Router()

async def get_user_lang(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.bot_language if user else 'uz'

@router.message(lambda m: m.text in [get_text('btn_stats', 'uz'), get_text('btn_stats', 'ru'), get_text('btn_stats', 'en')])
async def show_stats(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
    
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        
        admin_prefix = ""
        if user.is_admin:
            # Umumiy statistika
            total_users = await session.scalar(select(func.count(User.id)))
            vip_users = await session.scalar(select(func.count(User.id)).where(User.is_vip == True))
            total_posts = await session.scalar(select(func.count(PendingPost.id)).where(PendingPost.status == 'approved'))
            
            admin_prefix = (
                f"🚀 <b>Super Admin Statistikasi:</b>\n\n"
                f"👤 Jami foydalanuvchilar: <b>{total_users}</b>\n"
                f"💎 VIP foydalanuvchilar: <b>{vip_users}</b>\n"
                f"✅ Jami tarjimalar: <b>{total_posts}</b>\n\n"
                f"--------------------------------\n"
                f"<i>Sizning shaxsiy statistikangiz:</i>\n"
            )

        # Manbalar soni
        src_count = await session.scalar(select(func.count(Source.id)).where(Source.user_id == user.id))
        # Kanallar soni
        ch_count = await session.scalar(select(func.count(OutputChannel.id)).where(OutputChannel.user_id == user.id))
        # Approved postlar soni
        post_count = await session.scalar(select(func.count(PendingPost.id)).where(PendingPost.user_id == user.id, PendingPost.status == 'approved'))

    stats_text = {
        'uz': f"{admin_prefix}📊 <b>Sizning statistikangiz:</b>\n\n"
              f"📺 Jami manbalar: <b>{src_count}</b>\n"
              f"📢 Jami kanallar: <b>{ch_count}</b>\n"
              f"✅ Tarjima qilingan postlar: <b>{post_count}</b>",
        'ru': f"{admin_prefix}📊 <b>Ваша статистика:</b>\n\n"
              f"📺 Всего источников: <b>{src_count}</b>\n"
              f"📢 Всего каналов: <b>{ch_count}</b>\n"
              f"✅ Переведенных постов: <b>{post_count}</b>",
        'en': f"{admin_prefix}📊 <b>Your Statistics:</b>\n\n"
              f"📺 Total sources: <b>{src_count}</b>\n"
              f"📢 Total channels: <b>{ch_count}</b>\n"
              f"✅ Translated posts: <b>{post_count}</b>"
    }

    await message.answer(
        stats_text.get(lang, stats_text['uz']),
        reply_markup=get_main_menu_keyboard(lang, is_vip=user.is_vip, is_admin=user.is_admin),
        parse_mode="HTML"
    )
