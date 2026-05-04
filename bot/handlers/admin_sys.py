import logging
from aiogram import Router, types, F, Bot
from sqlalchemy import update, select
from database.db import AsyncSessionLocal
from database.models import User
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
router = Router()

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
async def sys_reject_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    await callback.message.edit_text(f"❌ Foydalanuvchi (ID: {user_id}) rad etildi.")
    await callback.answer()
