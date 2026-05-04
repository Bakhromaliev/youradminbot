import logging
from aiogram import Router, types, F, Bot
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from database.db import AsyncSessionLocal
from database.models import User
from bot.utils.texts import get_text, LANG_LABELS
from bot.utils.keyboards import get_main_menu_keyboard, get_settings_keyboard

logger = logging.getLogger(__name__)
router = Router()

async def get_user_lang(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.bot_language if user else 'uz'

@router.message(lambda m: m.text in [get_text('btn_settings', 'uz'), get_text('btn_settings', 'ru'), get_text('btn_settings', 'en')])
async def show_settings(message: types.Message, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(message.from_user.id)
    await message.answer(
        get_text('settings_title', lang), 
        reply_markup=get_settings_keyboard(lang), 
        parse_mode="HTML"
    )

# YANGI: Asosiy menyu tugmasini tutib qolish
@router.message(lambda m: m.text in [get_text('btn_main_menu', 'uz'), get_text('btn_main_menu', 'ru'), get_text('btn_main_menu', 'en')])
async def go_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(message.from_user.id)
    await message.answer(
        get_text('welcome_msg', lang),
        reply_markup=get_main_menu_keyboard(lang, user_id=message.from_user.id),
        parse_mode="HTML"
    )

@router.message(lambda m: m.text in [get_text('btn_change_lang', 'uz'), get_text('btn_change_lang', 'ru'), get_text('btn_change_lang', 'en')])
async def change_lang_start(message: types.Message):
    lang = await get_user_lang(message.from_user.id)
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
