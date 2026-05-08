import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from sqlalchemy import update, select
from bot_database.db import AsyncSessionLocal
from bot_database.models import User, Source
from datetime import datetime, timedelta
from services.monitor_tg import TelegramMonitor

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("sources_status"))
async def cmd_sources_status(message: types.Message, bot: Bot, tg_monitor: TelegramMonitor):
    # Faqat adminlar uchun
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        if not user or not user.is_admin:
            return

    status_msg = "🔍 <b>Manbalar holatini tekshirish...</b>\n\n"
    waiting_msg = await message.answer(status_msg + "⏳ Iltimos kuting, bu biroz vaqt olishi mumkin...", parse_mode="HTML")

    async with AsyncSessionLocal() as session:
        # Telegram manbalarini olish
        result = await session.execute(select(Source).where(Source.source_type == "telegram"))
        sources = result.scalars().all()

    if not sources:
        return await waiting_msg.edit_text("📭 Ulangan Telegram manbalari topilmadi.")

    full_report = "📊 <b>Telegram Manbalari Holati:</b>\n\n"
    
    for src in sources:
        check_res = await tg_monitor.check_source_access(src.source_id)
        full_report += f"🔹 <b>ID:</b> <code>{src.source_id}</code>\n"
        full_report += f"   📌 <b>Holat:</b> {check_res}\n"
        full_report += "-------------------\n"

    await waiting_msg.edit_text(full_report, parse_mode="HTML")

@router.callback_query(F.data.startswith("sys_approve_"))
async def sys_approve_user(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(is_approved=True))
        await session.commit()
    await callback.message.edit_text(f"✅ Foydalanuvchi (ID: {user_id}) muvaffaqiyatli tasdiqlandi!")
    try:
        await bot.send_message(user_id, "🎉 <b>Tabriklaymiz!</b>\n\nAdmin sizga botdan foydalanishga ruxsat berdi. Endi barcha imkoniyatlardan foydalanishingiz mumkin!", parse_mode="HTML")
    except: pass
    await callback.answer()

@router.callback_query(F.data.startswith("give_vip_"))
async def give_vip_status(callback: types.CallbackQuery, bot: Bot):
    try:
        parts = callback.data.split("_")
        months = int(parts[2])
        user_id = int(parts[3])
        
        logger.info(f"Admin granting {months} months VIP to {user_id}")
        
        until = datetime.utcnow() + timedelta(days=30 * months)
        
        async with AsyncSessionLocal() as session:
            await session.execute(update(User).where(User.telegram_id == user_id).values(
                is_approved=True, 
                is_vip=True, 
                vip_until=until
            ))
            await session.commit()
        
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n✅ <b>{months} oyga VIP berildi!</b>", parse_mode="HTML")
        try:
            await bot.send_message(user_id, f"💎 <b>Tabriklaymiz!</b>\n\nSizga {months} oy muddatga <b>VIP tarif</b> berildi. Endi sizda kunlik limitlar yo'q!", parse_mode="HTML")
        except Exception as e:
            logger.error(f"Could not notify user {user_id}: {e}")
            
    except Exception as e:
        logger.error(f"Error in give_vip_status: {e}")
        await callback.answer("⚠️ Xatolik yuz berdi.", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data.startswith("sys_reject_"))
async def sys_reject_user(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[-1])
    try:
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n❌ <b>To'lov rad etildi.</b>", parse_mode="HTML")
    except:
        await callback.message.edit_text(f"❌ Foydalanuvchi (ID: {user_id}) rad etildi.")
    
    try:
        await bot.send_message(user_id, "❌ <b>To'lovingiz rad etildi.</b>\n\nIltimos, skrinshot to'g'ri ekanligini va to'lov o'tganligini tekshiring yoki Adminga murojaat qiling.", parse_mode="HTML")
    except: pass
    
    await callback.answer()
