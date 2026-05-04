import logging
from aiogram import Router, types, F
import os
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, delete
from database.db import AsyncSessionLocal
from database.models import User, Source, SourceChannelLink, OutputChannel
from bot.utils.texts import get_text

logger = logging.getLogger(__name__)
router = Router()

class SourceStates(StatesGroup):
    waiting_for_source_id = State()
    viewing_source = State()
    confirm_unlink = State()

async def get_user_lang(user_id: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == user_id))
        user = result.scalar_one_or_none()
        return user.bot_language if user else 'uz'

# --- 1. MANBALAR RO'YXATI (ASOSIY) ---
@router.message(lambda m: m.text in [get_text('btn_sources', 'uz'), get_text('btn_sources', 'ru'), get_text('btn_sources', 'en')])
@router.message(F.text.contains("Orqaga") | F.text.contains("Назад") | F.text.contains("Back") | F.text.contains("Bekor qilish"))
async def list_sources_msg(message: types.Message, state: FSMContext, override_text=None):
    # Har qanday "Orqaga" yoki "Bekor qilish" bosilganda shu yerga keladi
    await state.clear()
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one_or_none()
        
        if not user:
            # Agar foydalanuvchi bazada yo'q bo'lsa, uni yaratishga harakat qilamiz (fail-safe)
            user = User(telegram_id=message.from_user.id, username=message.from_user.username, is_approved=True)
            session.add(user)
            await session.commit()
            await session.refresh(user)

        lang = user.bot_language or 'uz'
        SUPER_ADMIN_ID = 1400240097
        is_admin = (user.telegram_id == SUPER_ADMIN_ID) or user.is_admin
        sources_res = await session.execute(select(Source).where(Source.user_id == user.id))
        sources = sources_res.scalars().all()

    builder = ReplyKeyboardBuilder()
    for source in sources:
        icon = '📺' if source.source_type == 'telegram' else '🐦'
        builder.row(types.KeyboardButton(text=f"{icon} {source.source_id}"))
    
    builder.row(types.KeyboardButton(text=get_text('btn_add_tg', lang)), types.KeyboardButton(text=get_text('btn_add_tw', lang)))
    builder.row(types.KeyboardButton(text=get_text('btn_main_menu', lang)))

    text = override_text if override_text else get_text('sources_title', lang)
    await message.answer(text, reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

# --- 2. MANBA QO'SHISH ---
@router.message(F.text.contains("manba qo'shish") | F.text.contains("Добавить источник") | F.text.contains("Add Source"))
async def add_source_start(message: types.Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    s_type = "twitter" if "Twitter" in message.text or "🐦" in message.text else "telegram"
    await state.update_data(source_type=s_type)
    await state.set_state(SourceStates.waiting_for_source_id)
    prompt = get_text('add_tw_prompt', lang) if s_type == "twitter" else get_text('add_tg_prompt', lang)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Bekor qilish"))
    await message.answer(prompt, reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

@router.message(SourceStates.waiting_for_source_id)
async def add_src_save(message: types.Message, state: FSMContext, tg_monitor=None):
    # Bekor qilish allaqachon yuqoridagi handler orqali list_sources_msg ga ketadi
    data = await state.get_data()
    src_id = message.text.strip()
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        new_src = Source(user_id=user.id, source_type=data['source_type'], source_id=src_id, source_name=src_id)
        session.add(new_src); await session.commit()
    if data['source_type'] == 'telegram' and tg_monitor:
        await tg_monitor.join_source(src_id)
    await list_sources_msg(message, state, override_text="✅ Manba muvaffaqiyatli qo'shildi!")

# --- 3. MAVJUD MANBANI KO'RISH ---
@router.message(lambda m: m.text and (m.text.startswith('📺') or m.text.startswith('🐦')))
async def view_source_kb(message: types.Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    source_id_text = message.text[2:].strip()
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        source_res = await session.execute(select(Source).where(Source.user_id == user.id, Source.source_id == source_id_text))
        source = source_res.scalar_one_or_none()
        if not source: return
        await state.update_data(current_view_source_id=source.id)
        await state.set_state(SourceStates.viewing_source)
        links_res = await session.execute(select(SourceChannelLink).where(SourceChannelLink.source_id == source.id))
        links = links_res.scalars().all()

    builder = ReplyKeyboardBuilder()
    for link in links:
        async with AsyncSessionLocal() as sess2:
            ch_res = await sess2.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
            ch = ch_res.scalar_one_or_none()
            ch_label = ch.channel_name if ch and ch.channel_name else "Kanal"
        builder.row(types.KeyboardButton(text=f"🔗 {ch_label} (Sozlash)"))
    builder.row(types.KeyboardButton(text=f"➕ {get_text('btn_link_channel', lang)}"))
    builder.row(types.KeyboardButton(text=f"🗑 Manbani o'chirish: {source.source_id}"))
    builder.row(types.KeyboardButton(text="⬅️ Orqaga"))
    await message.answer(f"📦 <b>Manba: {source.source_id}</b>\n\nQaysi kanalni manbadan uzmoqchisiz?", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

# --- 4. UZISH (CONFIRMATION) ---
@router.message(SourceStates.viewing_source, F.text.startswith("🔗 "))
async def unlink_channel_start(message: types.Message, state: FSMContext):
    ch_label = message.text.replace("🔗 ", "").replace("(Sozlash)", "").strip()
    await state.update_data(selected_unlink_ch_label=ch_label)
    await state.set_state(SourceStates.confirm_unlink)
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text="❌ Manbadan uzish"))
    builder.row(types.KeyboardButton(text="⬅️ Orqaga"))
    await message.answer(f"❓ <b>{ch_label}</b> kanalini ushbu manbadan uzmoqchimisiz?", reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

@router.message(SourceStates.confirm_unlink, F.text.contains("uzish"))
async def unlink_channel_confirm(message: types.Message, state: FSMContext):
    data = await state.get_data()
    sid, ch_label = data.get('current_view_source_id'), data.get('selected_unlink_ch_label')
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        ch_res = await session.execute(select(OutputChannel).where(OutputChannel.user_id == user.id, (OutputChannel.channel_name == ch_label) | (OutputChannel.channel_id == ch_label)))
        channel = ch_res.scalar_one_or_none()
        if channel:
            await session.execute(delete(SourceChannelLink).where(SourceChannelLink.source_id == sid, SourceChannelLink.channel_db_id == channel.id))
            await session.commit()
            await message.answer("✅ Kanal manbadan muvaffaqiyatli uzildi!")
    await list_sources_msg(message, state)

# --- 5. QOLGAN HAMMA NARSA ---
@router.message(F.text.contains("Kanalni ulash") | F.text.contains("Привязать kanal") | F.text.contains("Link Channel"))
async def wizard_link_start(message: types.Message, state: FSMContext):
    lang = await get_user_lang(message.from_user.id)
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        channels_res = await session.execute(select(OutputChannel).where(OutputChannel.user_id == user.id))
        channels = channels_res.scalars().all()
    if not channels:
        await message.answer(get_text('channels_empty', lang), parse_mode="HTML"); return
    builder = ReplyKeyboardBuilder()
    for ch in channels: builder.row(types.KeyboardButton(text=f"📌 {ch.channel_name or ch.channel_id}"))
    builder.row(types.KeyboardButton(text="❌ Bekor qilish"))
    await message.answer(get_text('link_channel_prompt', lang), reply_markup=builder.as_markup(resize_keyboard=True), parse_mode="HTML")

@router.message(F.text.startswith('📌 '))
async def finalize_link(message: types.Message, state: FSMContext):
    label, data = message.text.replace('📌', '').strip(), await state.get_data()
    sid = data.get('current_view_source_id')
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        source_res = await session.execute(select(Source).where(Source.id == sid))
        source = source_res.scalar_one()
        ch_res = await session.execute(select(OutputChannel).where(OutputChannel.user_id == user.id, (OutputChannel.channel_name == label) | (OutputChannel.channel_id == label)))
        channel = ch_res.scalar_one_or_none()
        if channel:
            new_link = SourceChannelLink(user_id=user.id, source_id=sid, source_channel_id=source.source_id, channel_db_id=channel.id)
            session.add(new_link); await session.commit()
            await list_sources_msg(message, state, override_text="✅ Kanal muvaffaqiyatli bog'landi!")

@router.message(F.text.startswith('🗑 Manbani o\'chirish'))
async def del_src_start(message: types.Message):
    sid_text = message.text.split(":")[-1].strip()
    async with AsyncSessionLocal() as session:
        user_res = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = user_res.scalar_one()
        source_res = await session.execute(select(Source).where(Source.user_id == user.id, Source.source_id == sid_text))
        source = source_res.scalar_one_or_none()
        if source:
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="✅ Ha, o'chirilsin", callback_data=f"delete_source_{source.id}"))
            await message.answer(f"⚠️ <b>{sid_text}</b> manbasini o'chirasizmi?", reply_markup=builder.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.startswith("delete_source_"))
async def del_src_final(callback: types.CallbackQuery, state: FSMContext):
    sid = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Source).where(Source.id == sid))
        await session.commit()
    await callback.message.delete()
    await list_sources_msg(callback.message, state, override_text="✅ Manba o'chirildi.")

@router.message(lambda m: m.text in [get_text('btn_main_menu', 'uz'), get_text('btn_main_menu', 'ru'), get_text('btn_main_menu', 'en')])
async def go_main(message: types.Message, state: FSMContext):
    from bot.utils.keyboards import get_main_menu_keyboard
    await state.clear()
    lang = await get_user_lang(message.from_user.id)
    await message.answer(
        get_text('welcome_msg', lang), 
        reply_markup=get_main_menu_keyboard(lang, user_id=message.from_user.id), 
        parse_mode="HTML"
    )
