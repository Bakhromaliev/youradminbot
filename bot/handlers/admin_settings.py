import logging
import asyncio
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from bot_database.db import AsyncSessionLocal
from bot_database.models import BotSettings, User
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)
router = Router()

class AdminSettingsStates(StatesGroup):
    waiting_for_card = State()
    waiting_for_owner = State()
    waiting_for_price_month = State()
    waiting_for_price_6_months = State()
    waiting_for_price_year = State()
    waiting_for_broadcast_msg = State()

@router.message(F.text == "🛠 Boshqaruv")
async def show_admin_panel(message: types.Message):
    async with AsyncSessionLocal() as session:
        # Faqat adminligini yana bir bor tekshiramiz
        res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = res.scalar_one()
        if not user.is_admin: return

        settings_res = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        settings = settings_res.scalar_one_or_none()
        
        if not settings:
            settings = BotSettings(id=1, card_number="Kiritilmagan", card_owner="Kiritilmagan")
            session.add(settings)
            await session.commit()

        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="💳 Kartani o'zgartirish", callback_data="set_card"))
        builder.row(types.InlineKeyboardButton(text="👤 Egasi ismini o'zgartirish", callback_data="set_owner"))
        builder.row(types.InlineKeyboardButton(text="💰 Oylik narxni o'zgartirish", callback_data="set_price_m"))
        builder.row(types.InlineKeyboardButton(text="💰 6 oylik narxni o'zgartirish", callback_data="set_price_6m"))
        builder.row(types.InlineKeyboardButton(text="💰 Yillik narxni o'zgartirish", callback_data="set_price_y"))
        builder.row(types.InlineKeyboardButton(text="📢 Xabar yuborish (Foydalanuvchilarga)", callback_data="start_broadcast"))
        
        text = (
            "🛠 <b>Bot Boshqaruv Paneli</b>\n\n"
            f"💳 Karta: <code>{settings.card_number}</code>\n"
            f"👤 Ega: {settings.card_owner}\n"
            f"💵 Oylik VIP: {settings.vip_price_monthly:,} so'm\n"
            f"💵 6 oylik VIP: {settings.vip_price_6_months:,} so'm\n"
            f"💵 Yillik VIP: {settings.vip_price_yearly:,} so'm"
        )
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "start_broadcast")
async def start_broadcast_prompt(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📢 <b>Foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.</b>\n\nBu matn, rasm, video yoki har qanday formatda bo'lishi mumkin. Bekor qilish uchun 'bekor' deb yozing.", parse_mode="HTML")
    await state.set_state(AdminSettingsStates.waiting_for_broadcast_msg)
    await callback.answer()

@router.message(AdminSettingsStates.waiting_for_broadcast_msg)
async def process_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    if message.text and message.text.lower() == "bekor":
        await state.clear()
        return await message.answer("❌ Xabar yuborish bekor qilindi.")

    await message.answer("⏳ <b>Xabar yuborish boshlandi...</b>\nBu biroz vaqt olishi mumkin.", parse_mode="HTML")
    await state.clear()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.telegram_id))
        users = result.scalars().all()

    success = 0
    fail = 0
    
    for uid in users:
        try:
            # Xabarni har bir foydalanuvchiga nusxasini yuboramiz (Copy message)
            await message.copy_to(chat_id=uid)
            success += 1
            # Telegram limitlariga amal qilish uchun kichik to'xtalish
            if success % 20 == 0:
                await asyncio.sleep(0.5)
        except Exception as e:
            fail += 1
            logger.debug(f"Failed to send message to {uid}: {e}")

    await message.answer(
        f"✅ <b>Xabar yuborish yakunlandi!</b>\n\n"
        f"🟢 Muvaffaqiyatli: {success}\n"
        f"🔴 Muvaffaqiyatsiz: {fail}",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "set_card")
async def start_set_card(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💳 Yangi karta raqamini yuboring:")
    await state.set_state(AdminSettingsStates.waiting_for_card)
    await callback.answer()

@router.message(AdminSettingsStates.waiting_for_card)
async def process_set_card(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        await session.execute(update(BotSettings).where(BotSettings.id == 1).values(card_number=message.text))
        await session.commit()
    await message.answer(f"✅ Karta raqami yangilandi: {message.text}")
    await state.clear()

@router.callback_query(F.data == "set_owner")
async def start_set_owner(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("👤 Karta egasining ismini yuboring:")
    await state.set_state(AdminSettingsStates.waiting_for_owner)
    await callback.answer()

@router.message(AdminSettingsStates.waiting_for_owner)
async def process_set_owner(message: types.Message, state: FSMContext):
    async with AsyncSessionLocal() as session:
        await session.execute(update(BotSettings).where(BotSettings.id == 1).values(card_owner=message.text))
        await session.commit()
    await message.answer(f"✅ Karta egasi yangilandi: {message.text}")
    await state.clear()

@router.callback_query(F.data == "set_price_m")
async def start_set_price_m(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Oylik VIP narxini yuboring (faqat raqam):")
    await state.set_state(AdminSettingsStates.waiting_for_price_month)
    await callback.answer()

@router.message(AdminSettingsStates.waiting_for_price_month)
async def process_set_price_m(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("⚠️ Iltimos, faqat raqam yuboring.")
    async with AsyncSessionLocal() as session:
        await session.execute(update(BotSettings).where(BotSettings.id == 1).values(vip_price_monthly=int(message.text)))
        await session.commit()
    await message.answer(f"✅ Oylik VIP narxi yangilandi: {int(message.text):,} so'm")
    await state.clear()

@router.callback_query(F.data == "set_price_6m")
async def start_set_price_6m(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 6 oylik VIP narxini yuboring (faqat raqam):")
    await state.set_state(AdminSettingsStates.waiting_for_price_6_months)
    await callback.answer()

@router.message(AdminSettingsStates.waiting_for_price_6_months)
async def process_set_price_6m(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("⚠️ Iltimos, faqat raqam yuboring.")
    async with AsyncSessionLocal() as session:
        await session.execute(update(BotSettings).where(BotSettings.id == 1).values(vip_price_6_months=int(message.text)))
        await session.commit()
    await message.answer(f"✅ 6 oylik VIP narxi yangilandi: {int(message.text):,} so'm")
    await state.clear()

@router.callback_query(F.data == "set_price_y")
async def start_set_price_y(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Yillik VIP narxini yuboring (faqat raqam):")
    await state.set_state(AdminSettingsStates.waiting_for_price_year)
    await callback.answer()

@router.message(AdminSettingsStates.waiting_for_price_year)
async def process_set_price_y(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("⚠️ Iltimos, faqat raqam yuboring.")
    async with AsyncSessionLocal() as session:
        await session.execute(update(BotSettings).where(BotSettings.id == 1).values(vip_price_yearly=int(message.text)))
        await session.commit()
    await message.answer(f"✅ Yillik VIP narxi yangilandi: {int(message.text):,} so'm")
    await state.clear()
