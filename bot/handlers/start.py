from aiogram import Router, types, F
import os
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from bot_database.db import AsyncSessionLocal
from bot_database.models import User
from bot.utils.texts import get_text, LANG_LABELS
from bot.utils.keyboards import get_main_menu_keyboard # YANGI

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_lang = State()

@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "1400240097"))
    user_id = message.from_user.id
    
    # Super Admin uchun bazaga kirmasdan javob berish (Tezkorlik)
    if user_id == SUPER_ADMIN_ID:
        welcome_text = get_text('welcome_msg', 'uz') + f"\n\n🆔 Sizning ID: <code>{user_id}</code>"
        return await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard('uz', is_vip=True, is_admin=True), 
            parse_mode="HTML"
        )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        
        is_admin = user and user.is_admin
        is_vip = user and user.is_vip

        welcome_text = get_text('welcome_msg', user.bot_language if user else 'uz')
        welcome_text += f"\n\n🆔 Sizning ID: <code>{user_id}</code>" # ID'ni ko'rsatamiz

        if user:
            # Agar super admin bo'lsa, bazada ham admin qilib qo'yamiz
            if user_id == SUPER_ADMIN_ID and not user.is_admin:
                user.is_admin = True
                await session.commit()

            await message.answer(
                welcome_text,
                reply_markup=get_main_menu_keyboard(user.bot_language, is_vip=is_vip, is_admin=is_admin), 
                parse_mode="HTML"
            )
        else:
            await state.set_state(RegistrationStates.waiting_for_lang)
            builder = ReplyKeyboardBuilder()
            for code, label in LANG_LABELS.items():
                builder.row(types.KeyboardButton(text=label))
            
            await message.answer(get_text('start_msg', 'uz'), reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

@router.message(RegistrationStates.waiting_for_lang)
async def process_language(message: types.Message, state: FSMContext):
    selected_lang = None
    for code, label in LANG_LABELS.items():
        if message.text == label:
            selected_lang = code
            break
    
    if selected_lang:
        async with AsyncSessionLocal() as session:
            new_user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                bot_language=selected_lang
            )
            session.add(new_user)
            await session.commit()
        
        await state.clear()
        await message.answer(
            get_text('welcome_msg', selected_lang),
            reply_markup=get_main_menu_keyboard(selected_lang, is_vip=False, is_admin=False), 
            parse_mode="HTML"
        )
    else:
        await message.answer("Iltimos, tugmalardan birini tanlang.")

# --- DEBUG BUYRUG'I (Faqat Admin uchun) ---
@router.message(F.text == "/debug_sources")
async def debug_sources(message: types.Message):
    SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "1400240097"))
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    
    from bot_database.models import SourceChannelLink, Source
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(SourceChannelLink))
        links = result.scalars().all()
        
        if not links:
            return await message.answer("❌ Bazada hech qanday SourceChannelLink yo'q.")
        
        text = "🔍 <b>Bazadagi SourceChannelLink yozuvlari:</b>\n\n"
        for lnk in links:
            text += f"• ID: <code>{lnk.id}</code>\n"
            text += f"  source_channel_id: <code>{lnk.source_channel_id}</code>\n"
            text += f"  channel_db_id: <code>{lnk.channel_db_id}</code>\n\n"
        
        await message.answer(text, parse_mode="HTML")

@router.message(F.text == "/tg_info")
async def tg_info(message: types.Message, tg_monitor: 'TelegramMonitor' = None):
    SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "1400240097"))
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    
    if not tg_monitor:
        return await message.answer("❌ Monitor topilmadi.")
        
    status_text = await tg_monitor.get_status()
    await message.answer(f"📊 <b>Telegram Monitor Holati:</b>\n\n{status_text}", parse_mode="HTML")
