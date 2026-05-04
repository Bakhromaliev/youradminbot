import logging
import asyncio
import os
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import SourceChannelLink, OutputChannel, User, PendingPost, PostMedia
from services.translator import TranslatorService
from aiogram import Bot, types as aiotypes
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from datetime import datetime, date
from bot.utils.texts import get_text
import re as _re

def _decode_premium_emojis(text: str) -> str:
    """[[emoji_id:12345:😅]] -> <tg-emoji emoji-id="12345">😅</tg-emoji>"""
    if not text: return text
    return _re.sub(
        r'\[\[emoji_id:(\d+):(.+?)\]\]',
        r'<tg-emoji emoji-id="\1">\2</tg-emoji>',
        text
    )

logger = logging.getLogger(__name__)

class TelegramMonitor:
    def __init__(self, api_id, api_hash, bot_token, translator: TranslatorService, aiogram_bot: Bot, session_string: str = None):
        self.client = TelegramClient(StringSession(session_string), api_id, api_hash)
        self.bot_token = bot_token
        self.translator = translator
        self.bot = aiogram_bot
        self.media_groups = {}
        self.download_path = "downloads"
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    async def start(self):
        await self.client.start()
        
        # Manbalarga qo'shilish
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SourceChannelLink.source_channel_id))
            sources = result.scalars().all()
            for s in set(sources):
                if s and s.startswith('@'):
                    await self.join_source(s)

        # Yangi xabarlarni tutish — FAQAT kanallardan
        @self.client.on(events.NewMessage)
        async def handle_new_post(event):
            try:
                # Faqat kanal postlarini olamiz
                if not event.is_channel:
                    return
                if event.grouped_id:
                    gid = event.grouped_id
                    if gid not in self.media_groups:
                        self.media_groups[gid] = []
                        asyncio.create_task(self.process_media_group_after_delay(gid))
                    self.media_groups[gid].append(event.message)
                    return
                # MUHIM: create_task orqali chiqaramiz — bot event loop ni bloklab qolmasin!
                asyncio.create_task(self.safe_process_message(event.message))
            except Exception as e:
                logger.error(f"handle_new_post error: {e}")

        logger.info("Telegram Monitor (Telethon) started successfully.")

    async def safe_process_message(self, message):
        """Xatolarni ushlab, process_single_message ni xavfsiz ishga tushiruvchi wrapper."""
        try:
            await self.process_single_message(message)
        except Exception as e:
            logger.error(f"safe_process_message error: {e}", exc_info=True)

    async def join_source(self, source_id: str):
        if not source_id: return False
        clean_id = source_id.replace('https://t.me/', '').replace('t.me/', '').replace('@', '').strip()
        try:
            from telethon.tl.functions.channels import JoinChannelRequest
            await self.client(JoinChannelRequest(clean_id))
            logger.info(f"Successfully joined source: @{clean_id}")
            return True
        except Exception as e:
            logger.warning(f"Could not join @{clean_id}: {e}")
            return False

    async def process_media_group_after_delay(self, gid):
        await asyncio.sleep(3.0)
        messages = self.media_groups.pop(gid, [])
        if not messages: return

        text = ""
        for m in messages:
            if m.message: text = m.message; break
        
        msg = messages[0]
        chat = await msg.get_chat()
        variants = [str(chat.id)]
        if hasattr(chat, 'username') and chat.username:
            variants.extend([chat.username, f"@{chat.username}"])

        async with AsyncSessionLocal() as session:
            stmt = select(SourceChannelLink).where(SourceChannelLink.source_channel_id.in_(variants))
            result = await session.execute(stmt)
            links = result.scalars().all()
            if not links: return

            translated_text = ""
            for link in links:
                user_res = await session.execute(select(User).where(User.id == link.user_id))
                user = user_res.scalar_one()
                ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
                channel = ch_res.scalar_one()

                # Agressiv tozalash (Barcha turdagi linklar va username'lar)
                clean_text = re.sub(r'https?://\S+', '', text)
                clean_text = re.sub(r't\.me/\S+', '', clean_text)
                clean_text = re.sub(r'tg://\S+', '', clean_text)
                clean_text = re.sub(r'www\.\S+', '', clean_text)
                clean_text = re.sub(r'@\w+', '', clean_text)
                clean_text = clean_text.strip()

                if not translated_text:
                    translated_text = await self.translator.translate(clean_text, target_lang=channel.target_lang, target_alphabet=channel.alphabet)

                new_pending = PendingPost(user_id=user.id, link_id=link.id, source_type="telegram", original_text=text, translated_text=translated_text, media_group_id=str(gid))
                session.add(new_pending)
                await session.flush()

                media_list = []
                for m in messages:
                    if m.media:
                        path = await m.download_media(file=f"{self.download_path}/")
                        m_type = 'photo' if hasattr(m.media, 'photo') else 'video'
                        pm = PostMedia(post_id=new_pending.id, file_id=path, media_type=m_type)
                        session.add(pm)
                        media_list.append(pm)
                
                await session.commit()
                await self.send_preview(user.telegram_id, new_pending, channel, media_list)

    async def process_single_message(self, message):
        try:
            chat = await message.get_chat()
            chat_id_num = getattr(chat, 'id', None)
            variants = []
            if chat_id_num:
                variants.append(str(chat_id_num))
                variants.append(f"-100{str(chat_id_num).lstrip('-')}")
            if hasattr(chat, 'username') and chat.username:
                variants.extend([chat.username, f"@{chat.username}"])
            
            logger.info(f"New TG channel message. Chat variants for DB lookup: {variants}")
            
            async with AsyncSessionLocal() as session:
                # Barcha telegram manbalarini olib, variantlar bilan solishtirish
                all_links = await session.execute(
                    select(SourceChannelLink).where(
                        SourceChannelLink.source_channel_id.in_(variants)
                    )
                )
                links = all_links.scalars().all()
                
                if not links:
                    # Logda ko'rsatamiz (debug uchun)
                    logger.warning(f"No matching links for variants: {variants}")
                    return
                
                logger.info(f"Found {len(links)} matching links for this message.")
                text = message.message or message.text or ""
                logger.info(f"Message text length: {len(text)} chars")
                
                # --- PREMIUM EMOJILARNI SAQLASH ---
                from telethon.tl.types import MessageEntityCustomEmoji
                if message.entities:
                    sorted_entities = sorted(message.entities, key=lambda e: e.offset, reverse=True)
                    for ent in sorted_entities:
                        if isinstance(ent, MessageEntityCustomEmoji):
                            emoji_id = ent.document_id
                            original_emoji = text[ent.offset : ent.offset + ent.length]
                            replacement = f"[[emoji_id:{emoji_id}:{original_emoji}]]"
                            text = text[:ent.offset] + replacement + text[ent.offset + ent.length:]
                # -----------------------------------
                
                file_path = None
                m_type = None
                if message.media:
                    file_path = await message.download_media(file=f"{self.download_path}/")
                    m_type = 'photo' if hasattr(message.media, 'photo') else 'video'
                
                # Tozalash (linklar va username'lar)
                clean_text = re.sub(r'https?://\S+', '', text)
                clean_text = re.sub(r't\.me/\S+', '', clean_text)
                clean_text = re.sub(r'tg://\S+', '', clean_text)
                clean_text = re.sub(r'www\.\S+', '', clean_text)
                clean_text = re.sub(r'@\w+', '', clean_text)
                clean_text = clean_text.strip()

                for link in links:
                    user_res = await session.execute(select(User).where(User.id == link.user_id))
                    user = user_res.scalar_one()
                    ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
                    channel = ch_res.scalar_one()

                    # --- LIMIT TEKSHIRUVI ---
                    if not user.is_vip and user.telegram_id != 1400240097:
                        today = date.today()
                        count_res = await session.execute(
                            select(PendingPost).where(
                                PendingPost.user_id == user.id,
                                PendingPost.created_at >= datetime.combine(today, datetime.min.time())
                            )
                        )
                        daily_count = len(count_res.scalars().all())
                        if daily_count >= 5:
                            await self.bot.send_message(user.telegram_id, get_text('limit_reached', user.bot_language or 'uz'), parse_mode="HTML")
                            continue
                    # -------------------------

                    try:
                        translated = await asyncio.wait_for(
                            self.translator.translate(clean_text, target_lang=channel.target_lang, target_alphabet=channel.alphabet),
                            timeout=45.0
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"Translation timed out for long post ({len(clean_text)} chars). Using original.")
                        translated = clean_text
                    translated = _decode_premium_emojis(translated)
                    
                    new_pending = PendingPost(user_id=user.id, link_id=link.id, source_type="telegram", original_text=text, translated_text=translated)
                    session.add(new_pending)
                    await session.flush()

                    media_list = []
                    if file_path:
                        pm = PostMedia(post_id=new_pending.id, file_id=file_path, media_type=m_type)
                        session.add(pm); media_list.append(pm)

                    await session.commit()
                    await self.send_preview(user.telegram_id, new_pending, channel, media_list)

        except Exception as e:
            logger.error(f"process_single_message error: {e}", exc_info=True)

    async def send_preview(self, chat_id, post, channel, media_list):
        builder = InlineKeyboardBuilder()
        builder.row(aiotypes.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{post.id}"),
                    aiotypes.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{post.id}"))
        builder.row(aiotypes.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{post.id}"))

        display_text = post.translated_text
        if channel.signature:
            sig = channel.signature
            if channel.is_bold_signature: sig = f"<b>{sig}</b>"
            display_text += ("\n" * (channel.signature_spacing + 1)) + sig

        caption = (
            f"🆕 <b>SHERIK: Yangi post! (Telegram)</b>\n\n"
            f"📝 Tarjima (nusxalash uchun ustiga bosing):\n<code>{display_text}</code>"
        )

        try:
            if not media_list:
                await self.bot.send_message(chat_id, caption, reply_markup=builder.as_markup(), parse_mode="HTML")
            elif len(media_list) == 1:
                m = media_list[0]
                await self.bot.send_photo(chat_id, FSInputFile(m.file_id), caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML") if m.media_type == 'photo' else await self.bot.send_video(chat_id, FSInputFile(m.file_id), caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
            else:
                media_group = []
                for i, m in enumerate(media_list):
                    file = FSInputFile(m.file_id)
                    if m.media_type == 'photo': media_group.append(aiotypes.InputMediaPhoto(media=file, caption=caption if i == 0 else "", parse_mode="HTML"))
                    else: media_group.append(aiotypes.InputMediaVideo(media=file, caption=caption if i == 0 else "", parse_mode="HTML"))
                await self.bot.send_media_group(chat_id, media_group)
                await self.bot.send_message(chat_id, "👆 Yuqoridagi albomni tasdiqlaysizmi?", reply_markup=builder.as_markup())
        except Exception as e:
            logger.error(f"Notify error: {e}")
