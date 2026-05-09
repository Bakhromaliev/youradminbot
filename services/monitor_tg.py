import logging
import asyncio
import os
import re
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from sqlalchemy import select, func
from bot_database.db import AsyncSessionLocal
from bot_database.models import SourceChannelLink, OutputChannel, User, PendingPost, PostMedia, Source
from services.translator import TranslatorService
from aiogram import Bot, types as aiotypes
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from datetime import datetime, date
from bot.utils.texts import get_text
import re as _re

def _decode_premium_emojis(text: str) -> str:
    if not text: return text
    text = _re.sub(r'\[\[emoji_id:(\d+):(.+?)\]\]', r'<tg-emoji emoji-id="\1">\2</tg-emoji>', text)
    text = _re.sub(r'\[\[emoji_id:[^\]]+\]\]', '', text)
    return text.strip()

logger = logging.getLogger(__name__)

class TelegramMonitor:
    def __init__(self, api_id, api_hash, bot_token, translator: TranslatorService, aiogram_bot: Bot, session_string: str = None):
        self.api_id = api_id; self.api_hash = api_hash; self.bot_token = bot_token
        self.translator = translator; self.bot = aiogram_bot; self.session_string = session_string
        self.media_groups = {}; self.download_path = "downloads"
        if not os.path.exists(self.download_path): os.makedirs(self.download_path)
        self.client = TelegramClient(StringSession(session_string) if session_string else 'bot_session', api_id, api_hash)

    async def check_source_access(self, source_id: str):
        if not self.client or not self.client.is_connected(): return "❌ Telethon ulanmagan"
        try:
            entity = await self.client.get_entity(source_id)
            return f"✅ OK ({entity.title})"
        except Exception as e: return f"❌ Xato: {str(e)}"

    async def start(self):
        try:
            if self.session_string: await self.client.start()
            else: await self.client.start(bot_token=self.bot_token)
            me = await self.client.get_me()
            logger.info(f"Telegram Monitor logged in as: {me.first_name}")
        except Exception as e:
            logger.error(f"Telegram connection FATAL ERROR: {e}"); return

        @self.client.on(events.NewMessage)
        async def handle_new_post(event):
            try:
                if event.grouped_id:
                    gid = event.grouped_id
                    if gid not in self.media_groups:
                        self.media_groups[gid] = []
                        asyncio.create_task(self.process_media_group_after_delay(gid))
                    self.media_groups[gid].append(event.message); return
                asyncio.create_task(self.safe_process_message(event.message))
            except Exception as e: logger.error(f"handle_new_post error: {e}")

        asyncio.create_task(self.sync_sources_periodically())
        await self.client.run_until_disconnected()

    async def sync_sources_periodically(self):
        from telethon.tl.functions.channels import JoinChannelRequest
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    result = await session.execute(select(SourceChannelLink.source_channel_id))
                    unique_sources = set(result.scalars().all())
                    for s in unique_sources:
                        if s and (s.startswith('@') or 't.me' in s):
                            clean_id = s.replace('https://t.me/', '').replace('t.me/', '').replace('@', '').strip()
                            try: await self.client(JoinChannelRequest(clean_id))
                            except: pass
            except Exception as e: logger.error(f"Sync error: {e}")
            await asyncio.sleep(600)

    async def safe_process_message(self, message):
        try: await self.process_single_message(message)
        except Exception as e: logger.error(f"Process error: {e}", exc_info=True)

    async def check_user_access(self, session, user):
        """Foydalanuvchi tasdiqlanganligi va limitini tekshiradi"""
        if user.is_admin or user.is_vip: return True
        if not user.is_approved: return False
        
        today = date.today()
        count_res = await session.execute(select(func.count(PendingPost.id)).where(
            PendingPost.user_id == user.id, 
            PendingPost.created_at >= datetime.combine(today, datetime.min.time())
        ))
        count = count_res.scalar() or 0
        if count >= 5:
            try: await self.bot.send_message(user.telegram_id, get_text('limit_reached', user.bot_language or 'uz'), parse_mode="HTML")
            except: pass
            return False
        return True

    async def process_media_group_after_delay(self, gid):
        await asyncio.sleep(3.0)
        messages = self.media_groups.pop(gid, [])
        if not messages: return
        text = next((m.message for m in messages if m.message), "")
        chat = await messages[0].get_chat()
        variants = [str(chat.id), f"-100{str(chat.id).lstrip('-')}", getattr(chat, 'username', ''), f"@{getattr(chat, 'username', '')}"]
        
        async with AsyncSessionLocal() as session:
            lower_variants = [v.lower() for v in variants if v]
            stmt = select(SourceChannelLink).where(func.lower(SourceChannelLink.source_channel_id).in_(lower_variants))
            links = (await session.execute(stmt)).scalars().all()
            if not links: return

            user_sources = {}
            for link in links:
                key = (link.user_id, link.source_id)
                if key not in user_sources: user_sources[key] = []
                user_sources[key].append(link)

            for (u_id, s_id), user_links in user_sources.items():
                user = (await session.execute(select(User).where(User.id == u_id))).scalar_one()
                if not await self.check_user_access(session, user): continue

                clean_text = re.sub(r'https?://\S+|t\.me/\S+|tg://\S+|www\.\S+|@\w+', '', text).strip()
                translated = await self.translator.translate(clean_text, target_lang='uz', target_alphabet='latin')
                
                new_pending = PendingPost(user_id=u_id, source_id=s_id, source_type="telegram", original_text=text, translated_text=translated, media_group_id=str(gid))
                session.add(new_pending); await session.flush()
                
                media_list = []
                for m in messages:
                    if m.media:
                        path = await m.download_media(file=f"{self.download_path}/")
                        m_type = 'photo' if hasattr(m.media, 'photo') else 'video'
                        pm = PostMedia(post_id=new_pending.id, file_id=path, media_type=m_type)
                        session.add(pm); media_list.append(pm)
                await session.commit()
                await self.send_preview(user, new_pending, user_links, media_list)

    async def process_single_message(self, message):
        chat = await message.get_chat()
        variants = [str(chat.id), f"-100{str(chat.id).lstrip('-')}", getattr(chat, 'username', ''), f"@{getattr(chat, 'username', '')}"]
        async with AsyncSessionLocal() as session:
            lower_variants = [v.lower() for v in variants if v]
            links = (await session.execute(select(SourceChannelLink).where(func.lower(SourceChannelLink.source_channel_id).in_(lower_variants)))).scalars().all()
            if not links: return
            
            text = message.message or message.text or ""
            from telethon.tl.types import MessageEntityCustomEmoji
            if message.entities:
                for ent in sorted(message.entities, key=lambda e: e.offset, reverse=True):
                    if isinstance(ent, MessageEntityCustomEmoji):
                        text = text[:ent.offset] + f"[[emoji_id:{ent.document_id}:{text[ent.offset:ent.offset+ent.length]}]]" + text[ent.offset+ent.length:]
            
            file_path = None; m_type = None
            if message.media:
                file_path = await message.download_media(file=f"{self.download_path}/"); m_type = 'photo' if hasattr(message.media, 'photo') else 'video'
            
            user_sources = {}
            for link in links:
                key = (link.user_id, link.source_id); 
                if key not in user_sources: user_sources[key] = []
                user_sources[key].append(link)

            for (u_id, s_id), user_links in user_sources.items():
                user = (await session.execute(select(User).where(User.id == u_id))).scalar_one()
                if not await self.check_user_access(session, user): continue

                clean_text = re.sub(r'https?://\S+|t\.me/\S+|tg://\S+|www\.\S+|@\w+', '', text).strip()
                translated = await self.translator.translate(clean_text, target_lang='uz', target_alphabet='latin')
                translated = _decode_premium_emojis(translated)
                
                new_pending = PendingPost(user_id=u_id, source_id=s_id, source_type="telegram", original_text=text, translated_text=translated)
                session.add(new_pending); await session.flush()
                media_list = []
                if file_path:
                    pm = PostMedia(post_id=new_pending.id, file_id=file_path, media_type=m_type)
                    session.add(pm); media_list.append(pm)
                await session.commit()
                await self.send_preview(user, new_pending, user_links, media_list)

    async def send_preview(self, user, post, links, media_list):
        chat_id = user.admin_channel_id if user.admin_channel_id else user.telegram_id
        builder = InlineKeyboardBuilder()
        builder.row(aiotypes.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{post.id}"),
                    aiotypes.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{post.id}"))
        builder.row(aiotypes.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{post.id}"))

        async with AsyncSessionLocal() as session:
            channel_names = []
            for link in links:
                ch = (await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))).scalar_one()
                channel_names.append(f"📢 {ch.channel_name}")
        
        channels_str = "\n".join(channel_names)
        caption = (
            f"🆕 <b>SHERIK: Yangi post!</b>\n\n"
            f"📍 <b>Yuboriladigan kanallar:</b>\n{channels_str}\n\n"
            f"📝 <b>Tarjima (Nusxalash uchun):</b>\n<code>{post.translated_text}</code>"
        )

        try:
            if len(caption) <= 1000:
                if not media_list: await self.bot.send_message(chat_id, caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                elif len(media_list) == 1:
                    m = media_list[0]; file = FSInputFile(m.file_id)
                    if m.media_type == 'photo': await self.bot.send_photo(chat_id, file, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                    else: await self.bot.send_video(chat_id, file, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                else:
                    media_group = []
                    for i, m in enumerate(media_list):
                        file = FSInputFile(m.file_id)
                        if m.media_type == 'photo': media_group.append(aiotypes.InputMediaPhoto(media=file, caption=caption if i == 0 else "", parse_mode="HTML"))
                        else: media_group.append(aiotypes.InputMediaVideo(media=file, caption=caption if i == 0 else "", parse_mode="HTML"))
                    await self.bot.send_media_group(chat_id, media_group)
                    await self.bot.send_message(chat_id, "👆 Yuqoridagi albomni tasdiqlaysizmi?", reply_markup=builder.as_markup())
            else:
                await self.bot.send_message(chat_id, caption, reply_markup=builder.as_markup(), parse_mode="HTML")
        except Exception as e: logger.error(f"Notify error: {e}")
