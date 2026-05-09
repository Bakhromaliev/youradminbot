import logging
from aiogram import Router, types, F, Bot
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from bot_database.db import AsyncSessionLocal
from bot_database.models import User
from bot.utils.texts import get_text, LANG_LABELS
from bot.utils.keyboards import get_main_menu_keyboard, get_settings_keyboard, get_cancel_keyboard

logger = logging.getLogger(__name__)
router = Router()

class AdminChannelState(StatesGroup):
    waiting_for_channel = State()

async def get_user_lang(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.bot_language if user else 'uz', user

@router.message(lambda m: m.text in [get_text('btn_settings', 'uz'), get_text('btn_settings', 'ru'), get_text('btn_settings', 'en')])
async def show_settings(message: types.Message, state: FSMContext):
    await state.clear()
    lang, _ = await get_user_lang(message.from_user.id)
    await message.answer(
        get_text('settings_title', lang), 
        reply_markup=get_settings_keyboard(lang), 
        parse_mode="HTML"
    )

@router.message(lambda m: m.text in [get_text('btn_admin_channel', 'uz'), get_text('btn_admin_channel', 'ru'), get_text('btn_admin_channel', 'en')])
async def admin_channel_settings(message: types.Message, state: FSMContext):
    lang, user = await get_user_lang(message.from_user.id)
    
    if user.admin_channel_id:
        # Agar kanal ulangan bo'lsa
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text=get_text('btn_remove_admin_channel', lang), callback_data="remove_admin_channel"))
        
        status_text = f"🛡 <b>Admin Kanal holati:</b>\n\n✅ Ulangan: <b>{user.admin_channel_name}</b> (ID: <code>{user.admin_channel_id}</code>)\n\n<i>Yangi xabarlar tasdiqlash uchun shu kanalga yuboriladi.</i>"
        await message.answer(status_text, reply_markup=builder.as_markup(), parse_mode="HTML")
    else:
        # Agar kanal ulanmagan bo'lsa
        await state.set_state(AdminChannelState.waiting_for_channel)
        await message.answer(get_text('admin_channel_prompt', lang), reply_markup=get_cancel_keyboard(lang), parse_mode="HTML")

@router.message(AdminChannelState.waiting_for_channel)
async def process_admin_channel(message: types.Message, state: FSMContext, bot: Bot):
    lang, _ = await get_user_lang(message.from_user.id)
    
    if message.text in [get_text('btn_cancel', 'uz'), get_text('btn_cancel', 'ru'), get_text('btn_cancel', 'en')]:
        await state.clear()
        return await show_settings(message, state)

    channel_input = message.text.strip()
    
    # Agar raqam bo'lmasa va @ bilan boshlanmasa, @ qo'shib qo'yamiz
    if not channel_input.startswith('@') and not (channel_input.startswith('-') or channel_input.isdigit()):
        channel_input = f"@{channel_input}"

    try:
        # Bot u yerda adminmi?
        chat = await bot.get_chat(channel_input)
        if chat.type not in ['channel', 'group', 'supergroup']:
            return await message.answer("❌ Bu yaroqli kanal yoki guruh emas.")
        
        member = await bot.get_chat_member(chat.id, bot.id)
        if member.status not in ['administrator', 'creator']:
            return await message.answer("❌ Bot ushbu kanalda <b>ADMIN</b> emas. Iltimos, avval admin qilib, keyin qayta urinib ko'ring.", parse_mode="HTML")
        
        async with AsyncSessionLocal() as session:
            # Biz har doim RAQAMLI ID ni saqlaymiz, bu eng ishonchli yo'l
            await session.execute(update(User).where(User.telegram_id == message.from_user.id).values(
                admin_channel_id=str(chat.id),
                admin_channel_name=chat.title
            ))
            await session.commit()
        
        await state.clear()
        await message.answer(get_text('admin_channel_success', lang, name=chat.title), reply_markup=get_settings_keyboard(lang), parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Error connecting admin channel: {e}")
        await message.answer("❌ Kanal topilmadi. Iltimos, ID yoki @username to'g'riligini (masalan: <code>@kanalingiz</code> yoki raqamli ID) va bot u yerda admin ekanligini tekshiring.", parse_mode="HTML")

@router.callback_query(F.data == "remove_admin_channel")
async def remove_admin_channel(callback: types.CallbackQuery):
    lang, _ = await get_user_lang(callback.from_user.id)
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.telegram_id == callback.from_user.id).values(
            admin_channel_id=None,
            admin_channel_name=None
        ))
        await session.commit()
    
    await callback.message.edit_text(get_text('admin_channel_removed', lang), parse_mode="HTML")
    await callback.answer()

@router.message(lambda m: m.text in [get_text('btn_main_menu', 'uz'), get_text('btn_main_menu', 'ru'), get_text('btn_main_menu', 'en')])
async def go_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    lang, _ = await get_user_lang(message.from_user.id)
    await message.answer(
        get_text('welcome_msg', lang),
        reply_markup=get_main_menu_keyboard(lang, user_id=message.from_user.id),
        parse_mode="HTML"
    )

@router.message(lambda m: m.text in [get_text('btn_change_lang', 'uz'), get_text('btn_change_lang', 'ru'), get_text('btn_change_lang', 'en')])
async def change_lang_start(message: types.Message):
    lang, _ = await get_user_lang(message.from_user.id)
    builder = InlineKeyboardBuilder()
    for code, label in LANG_LABELS.items():
        builder.row(types.InlineKeyboardButton(text=label, callback_data=f"set_lang_{code}"))
    
    await message.answer(
        get_text('lang_select_prompt', lang), 
        reply_markup=builder.as_markup(), 
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("set_lang_"))
async def process_lang_callback(callback: types.CallbackQuery, state: FSMContext):
    new_lang = callback.data.split("_")[-1]
    async with AsyncSessionLocal() as session:
        await session.execute(update(User).where(User.telegram_id == callback.from_user.id).values(bot_language=new_lang))
        await session.commit()
    
    await state.clear()
    try: await callback.message.delete()
    except: pass
    
    await callback.message.answer(
        get_text('lang_changed', new_lang, lang=LANG_LABELS[new_lang]),
        reply_markup=get_main_menu_keyboard(new_lang, user_id=callback.from_user.id),
        parse_mode="HTML"
    )
    await callback.answer()
