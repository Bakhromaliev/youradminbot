from aiogram import Router, types, F
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import User
from bot.utils.texts import get_text, LANG_LABELS
from bot.utils.keyboards import get_main_menu_keyboard # YANGI

router = Router()

class RegistrationStates(StatesGroup):
    waiting_for_lang = State()

@router.message(F.text == "/start")
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if user:
            await message.answer(
                get_text('welcome_msg', user.bot_language),
                reply_markup=get_main_menu_keyboard(user.bot_language, is_vip=user.is_vip, is_admin=user.is_admin), 
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
