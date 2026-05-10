import logging
import html
import os
import re as _re
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from bot_database.db import AsyncSessionLocal
from bot_database.models import PendingPost, SourceChannelLink, OutputChannel, User, PostMedia, Source
from bot.utils.texts import get_text
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from aiogram.utils.markdown import html_decoration as hd
from services.translator import TranslatorService

logger = logging.getLogger(__name__)
router = Router()

translator_service = TranslatorService(gemini_key="dummy", openai_key="dummy")

class EditPostStates(StatesGroup):
    waiting_for_new_text = State()

def get_preview_keyboard(post_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{post_id}"),
                types.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{post_id}"))
    builder.row(types.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{post_id}"))
    return builder.as_markup()

def apply_final_formatting(text: str, alphabet: str) -> str:
    # 1. Kalit so'zlarni himoya qilish
    keywords = ["JUST IN", "BREAKING", "CONFIRMED"]
    protected_text = text
    for i, kw in enumerate(keywords):
        protected_text = _re.sub(kw, f"____KW_{i}____", protected_text, flags=_re.IGNORECASE)

    # 2. Alifboni o'girish
    if alphabet == 'cyrillic':
        final_text = translator_service.to_cyrillic(protected_text)
    else:
        final_text = translator_service.to_latin(protected_text)
    
    # 3. HTML xavfsiz qilish (Escape)
    safe_text = hd.quote(final_text)

    # 4. Kalit so'zlarni qaytarish va QALIN qilish
    for i, kw in enumerate(keywords):
        safe_text = safe_text.replace(f"____KW_{i}____", f"<b>{kw}</b>")

    # 5. Premium emojilarni joylashtirish
    safe_text = _re.sub(r'\[\[emoji_id:(\d+):(.+?)\]\]', r'<tg-emoji emoji-id="\1">\2</tg-emoji>', safe_text)
    
    return safe_text

@router.callback_query(F.data.startswith("approve_post_"))
async def approve_post(callback: types.CallbackQuery, bot: Bot):
    post_id = int(callback.data.split("_")[-1])
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(PendingPost).where(PendingPost.id == post_id).options(selectinload(PendingPost.media)))
            post = result.scalar_one_or_none()
            if not post or post.status != "pending": return await callback.answer("⚠️ Qayta ishlangan.")

            stmt = select(SourceChannelLink).where(SourceChannelLink.source_id == post.source_id, SourceChannelLink.user_id == post.user_id)
            links = (await session.execute(stmt)).scalars().all()
            if not links: return await callback.answer("❌ Kanallar topilmadi.", show_alert=True)

            count = 0
            for link in links:
                ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
                channel = ch_res.scalar_one_or_none()
                if not channel: continue
                
                # Formatlashni qo'llash
                final_text = apply_final_formatting(post.translated_text, channel.alphabet)
                
                # Imzoni qo'shish
                if channel.signature:
                    sig = hd.quote(channel.signature)
                    if channel.is_bold_signature: sig = f"<b>{sig}</b>"
                    final_text += ("\n" * (channel.signature_spacing + 1)) + sig

                try:
                    target_chat = int(channel.channel_id) if (channel.channel_id.startswith('-100') or channel.channel_id.lstrip('-').isdigit()) else channel.channel_id
                    if post.media_url:
                        await bot.send_photo(chat_id=target_chat, photo=post.media_url, caption=final_text, parse_mode="HTML")
                    elif not post.media:
                        await bot.send_message(chat_id=target_chat, text=final_text, parse_mode="HTML")
                    elif len(post.media) == 1:
                        m = post.media[0]
                        if m.media_type == 'photo': await bot.send_photo(chat_id=target_chat, photo=m.file_id, caption=final_text, parse_mode="HTML")
                        else: await bot.send_video(chat_id=target_chat, video=m.file_id, caption=final_text, parse_mode="HTML")
                    else:
                        media_group = []
                        for i, m in enumerate(post.media):
                            if m.media_type == 'photo': media_group.append(types.InputMediaPhoto(media=m.file_id, caption=final_text if i == 0 else "", parse_mode="HTML"))
                            else: media_group.append(types.InputMediaVideo(media=m.file_id, caption=final_text if i == 0 else "", parse_mode="HTML"))
                        await bot.send_media_group(chat_id=target_chat, media=media_group)
                    count += 1
                except Exception as e:
                    logger.error(f"Error sending to {channel.channel_name}: {e}")

            if count > 0:
                await session.execute(update(PendingPost).where(PendingPost.id == post_id).values(status="approved"))
                await session.commit()
                try: await callback.message.delete()
                except: pass
                await callback.answer(f"✅ {count} ta kanalga yuborildi!")
            else:
                await callback.answer("❌ Yuborib bo'lmadi.", show_alert=True)
        except Exception as outer_e:
            logger.error(f"Approval critical error: {outer_e}", exc_info=True)
            await callback.answer("❌ Tizim xatosi.", show_alert=True)

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
    await state.update_data(editing_post_id=post_id)
    await state.set_state(EditPostStates.waiting_for_new_text)
    instruction = await callback.message.answer("⌨️ Yangi matnni yuboring:")
    await state.update_data(instruction_msg_id=instruction.message_id)
    await callback.answer()

@router.message(EditPostStates.waiting_for_new_text)
async def edit_post_finish(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data(); post_id = data['editing_post_id']
    instruction_id = data.get('instruction_msg_id'); new_text = message.text
    try:
        await bot.delete_message(message.chat.id, instruction_id); await message.delete()
    except: pass

    async with AsyncSessionLocal() as session:
        await session.execute(update(PendingPost).where(PendingPost.id == post_id).values(translated_text=new_text))
        await session.commit()
        
        post = (await session.execute(select(PendingPost).where(PendingPost.id == post_id).options(selectinload(PendingPost.media)))).scalar_one()
        links = (await session.execute(select(SourceChannelLink).where(SourceChannelLink.source_id == post.source_id, SourceChannelLink.user_id == post.user_id))).scalars().all()
        
        channel_names = []
        for link in links:
            ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
            ch = ch_res.scalar_one_or_none()
            if ch: channel_names.append(f"📢 {ch.channel_name}")
        
        channels_str = "\n".join(channel_names)
        preview_body = (
            f"📝 <b>Tarjima (Tahrirlangan):</b>\n\n"
            f"📍 <b>Yuboriladigan kanallar:</b>\n{channels_str}\n\n"
            f"<code>{new_text}</code>"
        )
        
        if post.media_url:
            await message.answer_photo(post.media_url, caption=preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
        elif not post.media:
            await message.answer(preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
        elif len(post.media) == 1:
            m = post.media[0]
            if m.media_type == 'photo': await message.answer_photo(m.file_id, caption=preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
            else: await message.answer_video(m.file_id, caption=preview_body, reply_markup=get_preview_keyboard(post.id), parse_mode="HTML")
        else:
            media_group = []
            for i, m in enumerate(post.media):
                if m.media_type == 'photo': media_group.append(types.InputMediaPhoto(media=m.file_id, caption=preview_body if i == 0 else "", parse_mode="HTML"))
                else: media_group.append(types.InputMediaVideo(media=m.file_id, caption=preview_body if i == 0 else "", parse_mode="HTML"))
            await message.answer_media_group(media=media_group)
            await message.answer("👆 Tahrirlangan albomni tasdiqlaysizmi?", reply_markup=get_preview_keyboard(post.id))
    await state.clear()
