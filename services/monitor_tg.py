import logging
import asyncio
import os
from pyrogram import Client, filters, types as pytypes
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import SourceChannelLink, OutputChannel, User, PendingPost, PostMedia
from services.translator import TranslatorService
from aiogram import Bot, types as aiotypes
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from datetime import datetime
from bot.utils.texts import get_text

logger = logging.getLogger(__name__)

class TelegramMonitor:
    def __init__(self, api_id, api_hash, bot_token, translator: TranslatorService, aiogram_bot: Bot):
        self.client = Client("user_session", api_id=api_id, api_hash=api_hash)
        self.bot_token = bot_token
        self.translator = translator
        self.bot = aiogram_bot
        self.media_groups = {}
        # Yuklash uchun papka
        self.download_path = "downloads"
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    async def start(self):
        await self.client.start()
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SourceChannelLink.source_channel_id))
            sources = result.scalars().all()
            for s in set(sources):
                if s and s.startswith('@'):
                    await self.join_source(s)

        @self.client.on_message()
        async def handle_new_post(client, message):
            if message.media_group_id:
                mg_id = message.media_group_id
                if mg_id not in self.media_groups:
                    self.media_groups[mg_id] = []
                    asyncio.create_task(self.process_media_group_after_delay(mg_id))
                self.media_groups[mg_id].append(message)
                return
            await self.process_single_message(message)

        logger.info("Telegram Monitor started with File-Relay support.")

    async def join_source(self, source_id: str):
        try:
            await self.client.join_chat(source_id)
            return True
        except: return False

    async def process_media_group_after_delay(self, mg_id):
        await asyncio.sleep(2.5)
        messages = self.media_groups.pop(mg_id, [])
        if not messages: return

        text = ""
        for m in messages:
            if m.caption: text = m.caption; break
            elif m.text: text = m.text; break
        
        first_msg = messages[0]
        variants = [str(first_msg.chat.id)]
        if first_msg.chat.username:
            variants.append(first_msg.chat.username)
            variants.append(f"@{first_msg.chat.username}")

        async with AsyncSessionLocal() as session:
            stmt = select(SourceChannelLink).where(SourceChannelLink.source_channel_id.in_(variants))
            result = await session.execute(stmt)
            links = result.scalars().all()
            if not links: return

            for link in links:
                user_res = await session.execute(select(User).where(User.id == link.user_id))
                user = user_res.scalar_one()
                ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
                channel = ch_res.scalar_one()

                # LIMIT TEKSHIRISH
                if not user.is_vip and not user.is_admin:
                    today = datetime.utcnow().strftime('%Y-%m-%d')
                    if user.last_post_date != today:
                        user.daily_post_count = 0
                        user.last_post_date = today
                    
                    if user.daily_post_count >= 5:
                        if user.daily_post_count == 5:
                            await self.bot.send_message(user.telegram_id, get_text('limit_reached', user.bot_language), parse_mode="HTML")
                            user.daily_post_count += 1
                            await session.commit()
                        continue
                    user.daily_post_count += 1

                translated_text = await self.translator.translate(text, target_lang=channel.target_lang, target_alphabet=channel.alphabet)
                
                new_pending = PendingPost(
                    user_id=user.id, link_id=link.id, source_type="telegram", 
                    original_text=text, translated_text=translated_text, media_group_id=mg_id
                )
                session.add(new_pending)
                await session.flush()

                # Albomdagi har bir faylni yuklab olamiz
                media_for_preview = []
                for m in messages:
                    file_path = await self.client.download_media(m, file_name=f"{self.download_path}/")
                    m_type = 'photo' if m.photo else 'video'
                    pm = PostMedia(post_id=new_pending.id, file_id=file_path, media_type=m_type)
                    session.add(pm)
                    media_for_preview.append(pm)

                await session.commit()
                await self.send_preview(user.telegram_id, new_pending, channel, media_for_preview)

    async def process_single_message(self, message):
        variants = [str(message.chat.id)]
        if message.chat.username:
            variants.append(message.chat.username)
            variants.append(f"@{message.chat.username}")
        
        async with AsyncSessionLocal() as session:
            stmt = select(SourceChannelLink).where(SourceChannelLink.source_channel_id.in_(variants))
            result = await session.execute(stmt)
            links = result.scalars().all()
            if not links: return

            text = message.text or message.caption or ""
            file_path = None
            m_type = None
            if message.photo or message.video:
                file_path = await self.client.download_media(message, file_name=f"{self.download_path}/")
                m_type = 'photo' if message.photo else 'video'

            for link in links:
                user_res = await session.execute(select(User).where(User.id == link.user_id))
                user = user_res.scalar_one()
                ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
                channel = ch_res.scalar_one()

                # LIMIT TEKSHIRISH
                if not user.is_vip and not user.is_admin:
                    today = datetime.utcnow().strftime('%Y-%m-%d')
                    if user.last_post_date != today:
                        user.daily_post_count = 0
                        user.last_post_date = today
                    
                    if user.daily_post_count >= 5:
                        if user.daily_post_count == 5:
                            await self.bot.send_message(user.telegram_id, get_text('limit_reached', user.bot_language), parse_mode="HTML")
                            user.daily_post_count += 1
                            await session.commit()
                        continue
                    user.daily_post_count += 1

                translated_text = await self.translator.translate(text, target_lang=channel.target_lang, target_alphabet=channel.alphabet)
                
                new_pending = PendingPost(user_id=user.id, link_id=link.id, source_type="telegram", original_text=text, translated_text=translated_text)
                session.add(new_pending)
                await session.flush()

                media_list = []
                if file_path:
                    pm = PostMedia(post_id=new_pending.id, file_id=file_path, media_type=m_type)
                    session.add(pm); media_list.append(pm)

                await session.commit()
                await self.send_preview(user.telegram_id, new_pending, channel, media_list)

    async def send_preview(self, chat_id, post, channel, media_list):
        builder = InlineKeyboardBuilder()
        builder.row(aiotypes.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{post.id}"),
                    aiotypes.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{post.id}"))
        builder.row(aiotypes.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{post.id}"))

        # Imzoni tayyorlaymiz
        display_text = post.translated_text
        if channel.signature:
            sig = channel.signature
            if channel.is_bold_signature: sig = f"<b>{sig}</b>"
            spacing = "\n" * (channel.signature_spacing + 1)
            display_text += spacing + sig

        caption = (
            f"🆕 <b>Yangi post!</b>\n\n"
            f"📡 Manba: <b>{post.original_text[:30]}...</b>\n"
            f"📢 Kanal: <b>{channel.channel_name}</b>\n"
            f"🅰️ Alifbo: <b>{channel.alphabet}</b>\n\n"
            f"📝 Tarjima:\n{display_text}"
        )

        if not media_list:
            await self.bot.send_message(chat_id, caption, reply_markup=builder.as_markup(), parse_mode="HTML")
        elif len(media_list) == 1:
            m = media_list[0]
            file = FSInputFile(m.file_id)
            if m.media_type == 'photo':
                await self.bot.send_photo(chat_id, file, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
            else:
                await self.bot.send_video(chat_id, file, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
        else:
            media_group = []
            for i, m in enumerate(media_list):
                file = FSInputFile(m.file_id)
                if m.media_type == 'photo':
                    media_group.append(aiotypes.InputMediaPhoto(media=file, caption=caption if i == 0 else "", parse_mode="HTML"))
                else:
                    media_group.append(aiotypes.InputMediaVideo(media=file, caption=caption if i == 0 else "", parse_mode="HTML"))
            await self.bot.send_media_group(chat_id, media_group)
            await self.bot.send_message(chat_id, "👆 Yuqoridagi albomni tasdiqlaysizmi?", reply_markup=builder.as_markup())
