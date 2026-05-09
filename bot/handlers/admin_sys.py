import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from sqlalchemy import update, select
from bot_database.db import AsyncSessionLocal
from bot_database.models import User, Source
from datetime import datetime, timedelta
from services.monitor_tg import TelegramMonitor
from services.monitor_tw import TwitterMonitor
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("admin_help"))
async def cmd_admin_help(message: types.Message):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        if not user or not user.is_admin: return

    help_text = (
        "🛠 <b>Bot Admin Buyruqlari:</b>\n\n"
        "1. /sources_status — Barcha manbalarni tekshirish.\n"
        "2. /user_info <ID> — Foydalanuvchi holatini tekshirish.\n"
        "3. /approve_user <ID> — Foydalanuvchini qo'lda tasdiqlash.\n"
        "4. /stats — Bot statistikasi.\n"
    )
    await message.answer(help_text, parse_mode="HTML")

@router.message(Command("sources_status"))
async def cmd_sources_status(message: types.Message, bot: Bot, tg_monitor: TelegramMonitor, tw_monitor: TwitterMonitor):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        if not user or not user.is_admin: return

    status_msg = "🔍 <b>Manbalar holatini tekshirish...</b>\n\n"
    waiting_msg = await message.answer(status_msg + "⏳ Iltimos kuting...", parse_mode="HTML")

    async with AsyncSessionLocal() as session:
        tg_sources = (await session.execute(select(Source).where(Source.source_type == "telegram"))).scalars().all()
        tw_sources = (await session.execute(select(Source).where(Source.source_type == "twitter"))).scalars().all()

    full_report = "📊 <b>MANBALAR HOLATI:</b>\n\n"
    full_report += "🔵 <b>Telegram:</b>\n"
    for src in tg_sources:
        check_res = await tg_monitor.check_source_access(src.source_id)
        full_report += f"   🔹 {src.source_id}: {check_res}\n"
    
    full_report += "\n🐦 <b>Twitter:</b>\n"
    for src in tw_sources:
        check_res = await tw_monitor.check_twitter_access(src.source_id)
        full_report += f"   🔹 {src.source_id}: {check_res}\n"

    await waiting_msg.edit_text(full_report, parse_mode="HTML")

@router.message(Command("user_info"))
async def cmd_user_info(message: types.Message):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        me = user_res.scalar_one_or_none()
        if not me or not me.is_admin: return

    parts = message.text.split()
    if len(parts) < 2: return await message.answer("ℹ️ /user_info <ID>")
    
    target_id = int(parts[1])
    async with AsyncSessionLocal() as session:
        from bot_database.models import OutputChannel
        res = await session.execute(select(User).where(User.telegram_id == target_id))
        user = res.scalar_one_or_none()
        if not user: return await message.answer("❌ Topilmadi.")

        src_res = await session.execute(select(Source).where(Source.user_id == user.id))
        sources = src_res.scalars().all()
        ch_res = await session.execute(select(OutputChannel).where(OutputChannel.user_id == user.id))
        channels = ch_res.scalars().all()

        text = (
            f"👤 <b>Foydalanuvchi:</b>\n"
            f"🆔 ID: <code>{user.telegram_id}</code>\n"
            f"✅ Tasdiqlangan: {'HA' if user.is_approved else 'YOQ'}\n"
            f"💎 VIP: {'HA' if user.is_vip else 'YOQ'}\n"
            f"📊 Manbalar: {len(sources)} ta\n"
            f"📢 Kanallar: {len(channels)} ta\n"
        )
        builder = InlineKeyboardBuilder()
        if not user.is_approved:
            builder.row(types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"sys_approve_{user.telegram_id}"))
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.message(Command("approve_user"))
async def cmd_approve_user_manual(message: types.Message, bot: Bot):
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        me = user_res.scalar_one_or_none()
        if not me or not me.is_admin: return

    parts = message.text.split()
    if len(parts) < 2: return await message.answer("ℹ️ /approve_user <ID>")
    target_id = int(parts[1])
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.telegram_id == target_id).values(is_approved=True))
        await session.commit()
    await message.answer(f"✅ {target_id} tasdiqlandi!")
    try: await bot.send_message(target_id, "✅ Admin sizga ruxsat berdi.")
    except: pass

@router.callback_query(F.data.startswith("sys_approve_"))
async def sys_approve_user(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.telegram_id == user_id).values(is_approved=True))
        await session.commit()
    await callback.message.edit_text(f"✅ Foydalanuvchi (ID: {user_id}) tasdiqlandi!")
    try: await bot.send_message(user_id, "🎉 Admin sizga botdan foydalanishga ruxsat berdi.")
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
        try: await bot.send_message(user_id, f"💎 Sizga {months} oyga VIP berildi!")
        except: pass
    except: await callback.answer("⚠️ Xatolik.", show_alert=True)
    await callback.answer()

@router.callback_query(F.data.startswith("sys_reject_"))
async def sys_reject_user(callback: types.CallbackQuery, bot: Bot):
    user_id = int(callback.data.split("_")[-1])
    try: await callback.message.edit_caption(caption=callback.message.caption + f"\n\n❌ <b>To'lov rad etildi.</b>")
    except: await callback.message.edit_text(f"❌ Foydalanuvchi (ID: {user_id}) rad etildi.")
    await callback.answer()
