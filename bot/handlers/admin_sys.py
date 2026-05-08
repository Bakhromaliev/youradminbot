import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from sqlalchemy import update, select
from bot_database.db import AsyncSessionLocal
from bot_database.models import User, Source
from datetime import datetime, timedelta
from services.monitor_tg import TelegramMonitor
from services.monitor_tw import TwitterMonitor

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("admin_help"))
async def cmd_admin_help(message: types.Message):
    # Faqat adminlar uchun
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        if not user or not user.is_admin: return

    help_text = (
        "🛠 <b>Bot Admin Buyruqlari:</b>\n\n"
        "1. /sources_status — Barcha Telegram va Twitter manbalarini tekshirish (ishlayaptimi yoki yo'q).\n"
        "2. /stats — Botning umumiy statistikasi (foydalanuvchilar, kanallar, postlar).\n"
        "3. 🛠 <b>Boshqaruv</b> menyusi orqali:\n"
        "   - VIP to'lovlarini tasdiqlash/rad etish.\n"
        "   - Foydalanuvchilarga VIP muddatini berish.\n"
        "   - Bot sozlamalarini (karta raqami, narxlar) o'zgartirish.\n\n"
        "💡 <i>Eslatma: Har qanday yangi post kelsa, u tasdiqlash uchun siz ulagan 'Admin Kanal'ga yoki shaxsiyingizga keladi.</i>"
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("sources_status"))
async def cmd_sources_status(message: types.Message, bot: Bot, tg_monitor: TelegramMonitor, tw_monitor: TwitterMonitor):
    # Faqat adminlar uchun
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        if not user or not user.is_admin: return

    status_msg = "🔍 <b>Manbalar holatini tekshirish...</b>\n\n"
    waiting_msg = await message.answer(status_msg + "⏳ Iltimos kuting, Telegram va Twitter tekshirilmoqda...", parse_mode="HTML")

    async with AsyncSessionLocal() as session:
        tg_sources = (await session.execute(select(Source).where(Source.source_type == "telegram"))).scalars().all()
        tw_sources = (await session.execute(select(Source).where(Source.source_type == "twitter"))).scalars().all()

    full_report = "📊 <b>MANBALAR HOLATI:</b>\n\n"
    
    # Telegram
    full_report += "🔵 <b>Telegram:</b>\n"
    if not tg_sources:
        full_report += "   <i>Manbalar yo'q</i>\n"
    for src in tg_sources:
        check_res = await tg_monitor.check_source_access(src.source_id)
        full_report += f"   🔹 {src.source_id}: {check_res}\n"

    full_report += "\n"

    # Twitter
    full_report += "🐦 <b>Twitter:</b>\n"
    if not tw_sources:
        full_report += "   <i>Manbalar yo'q</i>\n"
    for src in tw_sources:
        check_res = await tw_monitor.check_twitter_access(src.source_id)
        full_report += f"   🔹 {src.source_id}: {check_res}\n"

    await waiting_msg.edit_text(full_report, parse_mode="HTML")

@router.callback_query(F.data.startswith("sys_approve_"))
async def sys_approve_user(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(is_approved=True))
        await session.commit()
    await callback.message.edit_text(f"✅ Foydalanuvchi (ID: {user_id}) tasdiqlandi!")
    try: await bot.send_message(user_id, "🎉 <b>Tabriklaymiz!</b>\n\nAdmin sizga botdan foydalanishga ruxsat berdi.", parse_mode="HTML")
    except: pass
    await callback.answer()

@router.callback_query(F.data.startswith("give_vip_"))
async def give_vip_status(callback: types.CallbackQuery, bot: Bot):
    try:
        parts = callback.data.split("_"); months = int(parts[2]); user_id = int(parts[3])
        until = datetime.utcnow() + timedelta(days=30 * months)
        async with AsyncSessionLocal() as session:
            await session.execute(update(User).where(User.telegram_id == user_id).values(is_approved=True, is_vip=True, vip_until=until))
            await session.commit()
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n✅ <b>{months} oyga VIP berildi!</b>", parse_mode="HTML")
        try: await bot.send_message(user_id, f"💎 <b>Tabriklaymiz!</b>\n\nSizga {months} oyga <b>VIP tarif</b> berildi!", parse_mode="HTML")
        except: pass
    except: await callback.answer("⚠️ Xatolik.", show_alert=True)
    await callback.answer()

@router.callback_query(F.data.startswith("sys_reject_"))
async def sys_reject_user(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[-1])
    try: await callback.message.edit_caption(caption=callback.message.caption + f"\n\n❌ <b>To'lov rad etildi.</b>", parse_mode="HTML")
    except: await callback.message.edit_text(f"❌ Foydalanuvchi (ID: {user_id}) rad etildi.")
    try: await bot.send_message(user_id, "❌ <b>To'lovingiz rad etildi.</b>", parse_mode="HTML")
    except: pass
    await callback.answer()
