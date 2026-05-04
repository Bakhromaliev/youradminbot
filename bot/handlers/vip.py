import os
import logging
from datetime import datetime
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import User, BotSettings
from bot.utils.texts import get_text
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)
router = Router()

SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "1400240097"))

class VIPStates(StatesGroup):
    waiting_for_screenshot = State()

@router.message(F.text.contains("💎 VIP Tarif"))
async def show_vip_info(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one()
        
        if user.is_admin:
            return await message.answer("👑 Siz Super Adminsiz, sizda cheksiz VIP imkoniyati mavjud.")

        settings_res = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        settings = settings_res.scalar_one()

        vip_status_text = ""
        if user.is_vip and user.vip_until:
            now = datetime.utcnow()
            remaining = user.vip_until - now
            if remaining.days >= 0:
                until_str = user.vip_until.strftime("%d.%m.%Y")
                vip_status_text = (
                    f"🌟 <b>Sizning VIP holatingiz faol!</b>\n"
                    f"📅 Tugash sanasi: <b>{until_str}</b>\n"
                    f"⏳ Qolgan vaqt: <b>{remaining.days} kun</b>\n\n"
                    f"<i>Muddatni uzaytirish uchun quyidagi tariflardan foydalanishingiz mumkin:</i>\n\n"
                )
            else:
                # Muddat tugagan bo'lsa (lekin hali is_vip=True bo'lsa)
                user.is_vip = False
                await session.commit()

        info_text = (
            f"{vip_status_text}"
            "💎 <b>VIP Tarif afzalliklari:</b>\n\n"
            "- Kunlik cheksiz postlar\n"
            "- Tezkor tarjima\n"
            "- Reklamasiz foydalanish\n\n"
            "💰 <b>Narxlar:</b>\n"
            f"- 1 oylik: <b>{settings.vip_price_monthly:,} so'm</b>\n"
            f"- 6 oylik: <b>{settings.vip_price_6_months:,} so'm</b>\n"
            f"- 1 yillik: <b>{settings.vip_price_yearly:,} so'm</b>\n\n"
            "⚠️ <b>Muhim:</b> Siz faqat 1, 6 yoki 12 oylik tariflarni sotib olishingiz mumkin!\n\n"
            "💳 <b>To'lov ma'lumotlari:</b>\n"
            f"Karta: <code>{settings.card_number}</code>\n"
            f"Ega: {settings.card_owner}\n\n"
            "📩 To'lov qilganingizdan so'ng skrinshotni shu yerga yuboring. Admin tasdiqlashi bilan VIP yoqiladi."
        )
        
        await message.answer(info_text, parse_mode="HTML")
        await state.set_state(VIPStates.waiting_for_screenshot)

@router.message(VIPStates.waiting_for_screenshot, F.photo)
async def process_payment_screenshot(message: types.Message, state: FSMContext, bot: Bot):
    photo = message.photo[-1]
    user_id = message.from_user.id
    username = message.from_user.username or "yo'q"
    
    # Super Adminga yuborish
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ 1 oy VIP", callback_data=f"give_vip_1_{user_id}"))
    builder.row(types.InlineKeyboardButton(text="✅ 6 oy VIP", callback_data=f"give_vip_6_{user_id}"))
    builder.row(types.InlineKeyboardButton(text="✅ 1 yil VIP", callback_data=f"give_vip_12_{user_id}"))
    builder.row(types.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"sys_reject_{user_id}"))
    
    await bot.send_photo(
        SUPER_ADMIN_ID,
        photo.file_id,
        caption=f"💰 <b>Yangi to'lov skrinshoti!</b>\n\nFoydalanuvchi: @{username}\nID: <code>{user_id}</code>\nIsm: {message.from_user.full_name}\n\nUshbu foydalanuvchiga VIP bermoqchimisiz?",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )
    
    await message.answer("✅ <b>Skrinshot qabul qilindi!</b>\n\nAdmin to'lovni tekshirib, tez orada VIP tarifingizni yoqadi. Iltimos, kuting.", parse_mode="HTML")
    await state.clear()

def is_menu_button(message: types.Message):
    menu_buttons = [
        get_text('btn_sources', 'uz'), get_text('btn_sources', 'ru'), get_text('btn_sources', 'en'),
        get_text('btn_my_channels', 'uz'), get_text('btn_my_channels', 'ru'), get_text('btn_my_channels', 'en'),
        get_text('btn_settings', 'uz'), get_text('btn_settings', 'ru'), get_text('btn_settings', 'en'),
        get_text('btn_stats', 'uz'), get_text('btn_stats', 'ru'), get_text('btn_stats', 'en'),
        get_text('btn_vip', 'uz'), get_text('btn_vip', 'ru'), get_text('btn_vip', 'en'),
        "🛠 Boshqaruv"
    ]
    return message.text in menu_buttons or (message.text and message.text.startswith('/'))

@router.message(VIPStates.waiting_for_screenshot, lambda m: not is_menu_button(m))
async def invalid_vip_input(message: types.Message):
    await message.answer("⚠️ Iltimos, to'lov skrinshotini (rasm ko'rinishida) yuboring.\n\nBekor qilish uchun boshqa menyu tugmasini bosing.")
