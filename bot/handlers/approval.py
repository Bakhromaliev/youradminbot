import logging
import html
import os
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from database.db import AsyncSessionLocal
from database.models import PendingPost, SourceChannelLink, OutputChannel, User, PostMedia
from bot.utils.texts import get_text
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)
router = Router()

class EditPostStates(StatesGroup):
    waiting_for_new_text = State()

def get_preview_keyboard(post_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{post_id}"),
        types.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{post_id}")
    )
    builder.row(types.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{post_id}"))
    return builder.as_markup()

@router.callback_query(F.data.startswith("approve_post_"))
async def approve_post(callback: types.CallbackQuery, bot: Bot):
    post_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(PendingPost).where(PendingPost.id == post_id).options(selectinload(PendingPost.media))
        )
        post = result.scalar_one_or_none()
        if not post or post.status != "pending": return

        link_res = await session.execute(select(SourceChannelLink).where(SourceChannelLink.id == post.link_id))
        link = link_res.scalar_one()
        ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
        channel = ch_res.scalar_one()
        
        dest_id = channel.channel_id
        final_text = post.translated_text
        if channel.signature:
            sig = channel.signature
            if channel.is_bold_signature: sig = f"<b>{sig}</b>"
            spacing = "\n" * (channel.signature_spacing + 1)
            final_text += spacing + sig

        try:
            if post.media_url:
                # Twitter dan kelgan rasm URL orqali yuboriladi
                await bot.send_photo(chat_id=dest_id, photo=post.media_url, caption=final_text, parse_mode="HTML")
            elif not post.media:
                await bot.send_message(chat_id=dest_id, text=final_text, parse_mode="HTML")
            elif len(post.media) == 1:
                m = post.media[0]
                file = FSInputFile(m.file_id)
                if m.media_type == 'photo':
                    await bot.send_photo(chat_id=dest_id, photo=file, caption=final_text, parse_mode="HTML")
                else:
                    await bot.send_video(chat_id=dest_id, video=file, caption=final_text, parse_mode="HTML")
            else:
                media_group = []
                for i, m in enumerate(post.media):
                    file = FSInputFile(m.file_id)
                    if m.media_type == 'photo':
                        media_group.append(types.InputMediaPhoto(media=file, caption=final_text if i == 0 else "", parse_mode="HTML"))
                    else:
                        media_group.append(types.InputMediaVideo(media=file, caption=final_text if i == 0 else "", parse_mode="HTML"))
                await bot.send_media_group(chat_id=dest_id, media=media_group)
            
            await session.execute(update(PendingPost).where(PendingPost.id == post_id).values(status="approved"))
            await session.commit()
            
            try: await callback.message.delete()
            except: pass
            await callback.answer("✅ Kanalga yuborildi!")
        except Exception as e:
            logger.error(f"Approval error: {e}")
            await callback.answer(f"Xatolik: {e}", show_alert=True)

@router.callback_query(F.data.startswith("reject_post_"))
async def reject_post(callback: types.CallbackQuery):
    post_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PendingPost).where(PendingPost.id == post_id).options(selectinload(PendingPost.media)))
        post = result.scalar_one_or_none()
        if post:
            for m in post.media:
                if os.path.exists(m.file_id): 
                    try: os.remove(m.file_id)
                    except: pass
            await session.execute(update(PendingPost).where(PendingPost.id == post_id).values(status="rejected"))
            await session.commit()
    try: await callback.message.delete()
    except: pass
    await callback.answer("❌ Rad etildi")

@router.callback_query(F.data.startswith("edit_post_"))
async def edit_post_start(callback: types.CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split("_")[-1])
    # Eski xabarni o'chirmaymiz (user so'ragandek)
    await state.update_data(editing_post_id=post_id)
    await state.set_state(EditPostStates.waiting_for_new_text)
    instruction = await callback.message.answer("⌨️ Yangi matnni yuboring (imzosiz):")
    await state.update_data(instruction_msg_id=instruction.message_id)
    await callback.answer()

@router.message(EditPostStates.waiting_for_new_text)
async def edit_post_finish(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    post_id = data['editing_post_id']
    instruction_id = data.get('instruction_msg_id')
    new_text = message.text
    try:
        await bot.delete_message(message.chat.id, instruction_id)
        await message.delete()
    except: pass

    async with AsyncSessionLocal() as session:
        await session.execute(update(PendingPost).where(PendingPost.id == post_id).values(translated_text=new_text))
        await session.commit()
        
        # Link va Kanalni qayta yuklaymiz (Imzoni ko'rsatish uchun)
        result = await session.execute(
            select(PendingPost).where(PendingPost.id == post_id).options(selectinload(PendingPost.media))
        )
        post = result.scalar_one()
        link_res = await session.execute(select(SourceChannelLink).where(SourceChannelLink.id == post.link_id))
        link = link_res.scalar_one()
        ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
        channel = ch_res.scalar_one()

        # Imzoni tayyorlaymiz
        display_text = new_text
        if channel.signature:
            sig = channel.signature
            if channel.is_bold_signature: sig = f"<b>{sig}</b>"
            spacing = "\n" * (channel.signature_spacing + 1)
            display_text += spacing + sig

        preview_body = (
            f"📝 <b>Tarjima (Tahrirlangan):</b>\n\n"
            f"👇 Nusxalash uchun ustiga bosing:\n<code>{display_text}</code>"
        )
        
        if post.media_url:
            await message.answer_photo(post.media_url, caption=preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
        elif not post.media:
            await message.answer(preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
        elif len(post.media) == 1:
            m = post.media[0]
            file = FSInputFile(m.file_id)
            if m.media_type == 'photo':
                await message.answer_photo(file, caption=preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
            else:
                await message.answer_video(file, caption=preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
        else:
            media_group = []
            for i, m in enumerate(post.media):
                file = FSInputFile(m.file_id)
                if m.media_type == 'photo':
                    media_group.append(types.InputMediaPhoto(media=file, caption=preview_body if i == 0 else "", parse_mode="HTML"))
                else:
                    media_group.append(types.InputMediaVideo(media=file, caption=preview_body if i == 0 else "", parse_mode="HTML"))
            await message.answer_media_group(media=media_group)
            await message.answer("👆 Tahrirlangan albomni tasdiqlaysizmi?", reply_markup=get_preview_keyboard(post.id))
    await state.clear()
