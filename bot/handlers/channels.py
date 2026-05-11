import logging
import re
from aiogram import Router, types, F, Bot
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update, delete
from bot_database.db import AsyncSessionLocal
from bot_database.models import User, OutputChannel, SourceChannelLink
from bot.utils.texts import get_text, LANG_LABELS
from bot.utils.keyboards import get_main_menu_keyboard, get_cancel_keyboard

logger = logging.getLogger(__name__)
router = Router()

class ChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    viewing_channels = State()
    viewing_single_channel = State()
    editing_target_lang = State()
    editing_alphabet = State()
    editing_signature = State()
    waiting_for_sig_style = State() # NEW
    waiting_for_sig_spacing = State() # NEW

async def get_user_lang(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.bot_language if user else 'uz'

async def show_channel_settings(message: types.Message, state: FSMContext, channel_id: int):
    lang = await get_user_lang(message.from_user.id)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OutputChannel).where(OutputChannel.id == channel_id))
        ch = result.scalar_one_or_none()
    
    if not ch:
        await list_channels(message, state); return

    await state.update_data(current_ch_id=ch.id, current_ch_label=ch.channel_name or ch.channel_id)
    await state.set_state(ChannelStates.viewing_single_channel)
    
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="🌐 Nishon til"), types.KeyboardButton(text="🅰️ Alifbo"))
    builder.row(types.KeyboardButton(text="✍️ Imzo"), types.KeyboardButton(text="🗑 Kanalni o'chirish"))
    builder.row(types.KeyboardButton(text="⬅️ Orqaga"))
    
    style = "Qalin" if ch.is_bold_signature else "Oddiy"
    spacing = f"{ch.signature_spacing} qator"
    
    info = (
        f"📢 <b>Kanal: {ch.channel_name}</b>\n"
        f"🌐 Til: <b>{ch.target_lang}</b>\n"
        f"🅰️ Alifbo: <b>{ch.alphabet}</b>\n"
        f"✍️ Imzo: <code>{ch.signature or 'Yoq'}</code>\n"
        f"🎨 Uslub: <b>{style}</b> | 📏 Oraliq: <b>{spacing}</b>"
    )
    await message.answer(info, reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

# ... (Kanal ro'yxati va boshqa handlerlar o'sha-o'sha)

@router.message(F.text == "✍️ Imzo")
async def edit_ch_sig_start(message: types.Message, state: FSMContext):
    await state.set_state(ChannelStates.editing_signature)
    await message.answer("📝 Yangi imzo matnini yuboring yoki 'O'chirish' deb yozing:", reply_markup=get_cancel_keyboard('uz'))

@router.message(ChannelStates.editing_signature)
async def edit_ch_sig_save(message: types.Message, state: FSMContext):
    if "Bekor qilish" in message.text:
        data = await state.get_data()
        await show_channel_settings(message, state, data['current_ch_id']); return
    
    sig = message.text if message.text.lower() != "o'chirish" else None
    await state.update_data(temp_sig=sig)
    
    if not sig:
        data = await state.get_data()
        async with AsyncSessionLocal() as session:
            await session.execute(update(OutputChannel).where(OutputChannel.id == data['current_ch_id']).values(signature=None))
            await session.commit()
        await show_channel_settings(message, state, data['current_ch_id'])
        return

    # Keyingi qadam: Style
    await state.set_state(ChannelStates.waiting_for_sig_style)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Bold (Qalin)"), types.KeyboardButton(text="Normal (Oddiy)"))
    await message.answer("🎨 Imzo uslubini tanlang:", reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(ChannelStates.waiting_for_sig_style)
async def edit_ch_sig_style(message: types.Message, state: FSMContext):
    is_bold = "Bold" in message.text
    await state.update_data(temp_is_bold=is_bold)
    
    # Keyingi qadam: Spacing
    await state.set_state(ChannelStates.waiting_for_sig_spacing)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="0 qator"), types.KeyboardButton(text="1 qator"))
    builder.row(types.KeyboardButton(text="2 qator"), types.KeyboardButton(text="3 qator"))
    await message.answer("📏 Post va imzo orasida necha qator bo'shliq bo'lsin?", reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(ChannelStates.waiting_for_sig_spacing)
async def edit_ch_sig_spacing_finish(message: types.Message, state: FSMContext):
    try:
        spacing = int(message.text.split(" ")[0])
    except: spacing = 1
    
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        await session.execute(update(OutputChannel).where(OutputChannel.id == data['current_ch_id']).values(
            signature=data['temp_sig'],
            is_bold_signature=data['temp_is_bold'],
            signature_spacing=spacing
        ))
        await session.commit()
    
    await message.answer("✅ Imzo sozlamalari saqlandi!")
    await show_channel_settings(message, state, data['current_ch_id'])

# ... (Qolgan navigatsiya handlerlari)
@router.message(lambda m: m.text in [get_text('btn_my_channels', 'uz'), get_text('btn_my_channels', 'ru'), get_text('btn_my_channels', 'en')])
async def list_channels(message: types.Message, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(message.from_user.id)
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        
        if not user:
            user = User(telegram_id=message.from_user.id, username=message.from_user.username, is_approved=True)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        channels = (await session.execute(select(OutputChannel).where(OutputChannel.user_id == user.id))).scalars().all()
    builder = ReplyKeyboardBuilder()
    for ch in channels: builder.row(types.KeyboardButton(text=f"📢 {ch.channel_name or ch.channel_id}"))
    builder.row(types.KeyboardButton(text=get_text('btn_add_channel', lang)), types.KeyboardButton(text=get_text('btn_main_menu', lang)))
    await state.set_state(ChannelStates.viewing_channels)
    await message.answer("📢 <b>Sizning kanallaringiz</b>", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

@router.message(lambda m: m.text in [get_text('btn_add_channel', 'uz'), get_text('btn_add_channel', 'ru'), get_text('btn_add_channel', 'en')])
async def add_channel_start(message: types.Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    await state.set_state(ChannelStates.waiting_for_channel_id)
    await message.answer(get_text('add_channel_prompt', lang), reply_markup=get_cancel_keyboard(lang), parse_mode="HTML")

@router.message(ChannelStates.waiting_for_channel_id)
async def process_channel_id(message: types.Message, state: FSMContext, bot: Bot):
    lang = await get_user_lang(message.from_user.id)
    raw_input = message.text.strip()
    if any(raw_input == get_text(k, lang) for k in ['btn_cancel', 'btn_back', 'btn_main_menu']): 
        await list_channels(message, state); return
    channel_id = raw_input
    if "t.me/" in raw_input: channel_id = "@" + raw_input.split("t.me/")[-1].split("/")[0]
    try:
        chat = await bot.get_chat(channel_id)
        member = await bot.get_chat_member(chat.id, (await bot.get_me()).id)
        if member.status not in ["administrator", "creator"]:
            await message.answer(get_text('bot_not_admin', lang)); return
        async with AsyncSessionLocal() as session:
            user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
            user = user_res.scalar_one()
            new_channel = OutputChannel(user_id=user.id, channel_id=str(chat.id), channel_name=chat.title or chat.full_name or channel_id)
            session.add(new_channel)
            await session.commit()
            ch_id = new_channel.id
        await message.answer("✅ Kanal qo'shildi!")
        await show_channel_settings(message, state, ch_id)
    except Exception as e: await message.answer("❌ Kanal topilmadi yoki bot admin emas.")

@router.message(F.text == "🌐 Nishon til")
async def edit_ch_lang_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'current_ch_id' not in data: return
    await state.set_state(ChannelStates.editing_target_lang)
    builder = ReplyKeyboardBuilder()
    for code, label in LANG_LABELS.items(): builder.row(types.KeyboardButton(text=f"Lang:{code}:{label}"))
    builder.row(types.KeyboardButton(text="⬅️ Bekor qilish"))
    await message.answer("Yangi tilni tanlang:", reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text.startswith("Lang:"))
async def edit_ch_lang_finish(message: types.Message, state: FSMContext):
    code = message.text.split(":")[1]
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        await session.execute(update(OutputChannel).where(OutputChannel.id == data['current_ch_id']).values(target_lang=code))
        await session.commit()
    await show_channel_settings(message, state, data['current_ch_id'])

@router.message(F.text == "🅰️ Alifbo")
async def edit_ch_alpha_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'current_ch_id' not in data: return
    await state.set_state(ChannelStates.editing_alphabet)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="Alpha:latin"), types.KeyboardButton(text="Alpha:cyrillic"))
    builder.row(types.KeyboardButton(text="⬅️ Bekor qilish"))
    await message.answer("Alifboni tanlang:", reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text.startswith("Alpha:"))
async def edit_ch_alpha_finish(message: types.Message, state: FSMContext):
    alpha = message.text.split(":")[1]
    data = await state.get_data()
    async with AsyncSessionLocal() as session:
        await session.execute(update(OutputChannel).where(OutputChannel.id == data['current_ch_id']).values(alphabet=alpha))
        await session.commit()
    await show_channel_settings(message, state, data['current_ch_id'])

@router.message(F.text == "🗑 Kanalni o'chirish")
async def delete_channel_start(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'current_ch_id' not in data: return
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"del_ch_final_{data['current_ch_id']}"))
    await message.answer(f"⚠️ <b>{data['current_ch_label']}</b> kanalini o'chirasizmi?", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("del_ch_final_"))
async def delete_channel_finish(callback: types.CallbackQuery, state: FSMContext):
    ch_id = int(callback.data.split("_")[-1])
    ch_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        # Ob'ektni olamiz va session orqali o'chiramiz
        res = await session.execute(select(OutputChannel).where(OutputChannel.id == ch_id))
        channel = res.scalar_one_or_none()
        if channel:
            await session.delete(channel)
            await session.commit()
    await callback.message.delete()
    await list_channels(callback.message, state)

@router.message(lambda m: m.text and m.text.startswith("📢 "))
async def view_channel_from_list(message: types.Message, state: FSMContext):
    ch_label = message.text.replace("📢 ", "").strip()
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        result = await session.execute(select(OutputChannel).where(OutputChannel.user_id == user.id, (OutputChannel.channel_name == ch_label) | (OutputChannel.channel_id == ch_label)))
        ch = result.scalar_one_or_none()
    if ch: await show_channel_settings(message, state, ch.id)

@router.message(F.text == "⬅️ Orqaga")
async def back_to_channels(message: types.Message, state: FSMContext): await list_channels(message, state)

@router.message(lambda m: m.text in [get_text('btn_main_menu', 'uz'), get_text('btn_main_menu', 'ru'), get_text('btn_main_menu', 'en')])
async def go_main(message: types.Message, state: FSMContext):
    from bot.utils.keyboards import get_main_menu_keyboard
    lang = await get_user_lang(message.from_user.id)
    await state.clear()
    await message.answer(
        get_text('welcome_msg', lang), 
        reply_markup=get_main_menu_keyboard(lang, user_id=message.from_user.id), 
        parse_mode="HTML"
    )
