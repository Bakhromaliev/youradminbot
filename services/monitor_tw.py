import logging
import asyncio
import os
import re
import httpx
from telethon import types
from sqlalchemy import select, func
from bot_database.db import AsyncSessionLocal
from bot_database.models import SourceChannelLink, OutputChannel, User, PendingPost, PostMedia, Source
from services.translator import TranslatorService
from aiogram import Bot, types as aiotypes
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from datetime import datetime, date

logger = logging.getLogger(__name__)

class TwitterMonitor:
    def __init__(self, api_key, api_host, bot_token, translator: TranslatorService, aiogram_bot: Bot):
        self.api_key = api_key; self.api_host = api_host; self.bot_token = bot_token
        self.translator = translator; self.bot = aiogram_bot
        self.download_path = "downloads"
        if not os.path.exists(self.download_path): os.makedirs(self.download_path)

    async def check_all_twitter_unique_sources(self):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Source).where(Source.source_type == "twitter"))
            all_sources = result.scalars().all()
            if not all_sources: return
            grouped = {}
            for src in all_sources:
                u = src.source_id.replace("@", "").strip().lower()
                if u not in grouped: grouped[u] = []
                grouped[u].append(src)
            for u, sources in grouped.items():
                await self.fetch_tweets_api_optimized(u, sources); await asyncio.sleep(10)

    async def fetch_tweets_api_optimized(self, username, sources_list):
        url = f"https://{self.api_host}/timeline.php"; params = {"screenname": username}
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.api_host}
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code != 200 or not response.text.strip(): return
                try: data = response.json()
                except Exception: return
                
                tweets = data.get('timeline', []) if isinstance(data, dict) else data
                if not isinstance(tweets, list): return
                async with AsyncSessionLocal() as session:
                    for tweet in tweets[:3]:
                        if tweet.get('retweeted') or 'retweeted_status' in tweet: continue
                        t_id = str(tweet.get('tweet_id') or tweet.get('id_str') or tweet.get('id'))
                        if not t_id: continue
                        
                        # Dublikatni tekshirish
                        existing_res = await session.execute(select(PendingPost).where(PendingPost.source_type == "twitter", PendingPost.original_text.contains(t_id)))
                        if existing_res.first(): continue
                        
                        raw_text = tweet.get('text') or tweet.get('full_text') or ""
                        if not raw_text: continue
                        
                        media_url = self.find_media_recursive(tweet)
                        clean_text = re.sub(r'https?://\S+|t\.me/\S+|tg://\S+|www\.\S+|@\w+', '', raw_text).strip()
                        if not clean_text and not media_url: continue
                        
                        for src in sources_list: 
                            await self.process_unified_tweet(t_id, clean_text, media_url, src)
        except Exception as e: logger.error(f"API Error for @{username}: {e}")

    async def download_twitter_media(self, url):
        """Twitter rasmini serverga yuklab oladi"""
        if not url: return None
        try:
            ext = ".jpg"
            if ".png" in url: ext = ".png"
            elif ".mp4" in url: ext = ".mp4"
            
            filename = f"tw_{int(datetime.now().timestamp())}_{os.urandom(4).hex()}{ext}"
            path = os.path.join(self.download_path, filename)
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, timeout=30)
                if resp.status_code == 200:
                    with open(path, "wb") as f: f.write(resp.content)
                    return path
        except Exception as e:
            logger.error(f"Failed to download Twitter media: {e}")
        return None

    async def process_unified_tweet(self, tweet_id, text, media_url, source_obj):
        async with AsyncSessionLocal() as session:
            links = (await session.execute(select(SourceChannelLink).where(SourceChannelLink.source_id == source_obj.id))).scalars().all()
            if not links: return
            
            user_res = await session.execute(select(User).where(User.id == source_obj.user_id))
            user = user_res.scalars().first()
            if not user or not await self.check_user_access(session, user): return

            translated = await self.translator.translate(text, target_lang='uz', target_alphabet='latin', is_twitter=True)
            db_text = f"{text}\n\n#tw_id:{tweet_id}"
            
            # Medianing o'zini yuklab olish
            local_file_path = None
            if media_url:
                local_file_path = await self.download_twitter_media(media_url)

            new_pending = PendingPost(user_id=user.id, source_id=source_obj.id, source_type="twitter", original_text=db_text, translated_text=translated)
            session.add(new_pending); await session.flush()
            
            media_list = []
            if local_file_path:
                m_type = 'video' if local_file_path.endswith('.mp4') else 'photo'
                pm = PostMedia(post_id=new_pending.id, file_id=local_file_path, media_type=m_type)
                session.add(pm); media_list.append(pm)
            
            await session.commit()

            channel_names = []
            for link in links:
                ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
                ch = ch_res.scalars().first()
                if ch: channel_names.append(f"📢 {ch.channel_name}")
            
            channels_str = "\n".join(channel_names)
            preview_body = (
                f"🆕 <b>SHERIK: Yangi post (Twitter)!</b>\n\n"
                f"📍 <b>Yuboriladigan kanallar:</b>\n{channels_str}\n\n"
                f"📝 <b>Tarjima (Nusxalash uchun):</b>\n<code>{translated}</code>"
            )
            
            chat_id = user.admin_channel_id if user.admin_channel_id else user.telegram_id
            builder = InlineKeyboardBuilder()
            builder.row(aiotypes.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{new_pending.id}"),
                        aiotypes.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{new_pending.id}"))
            builder.row(aiotypes.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{new_pending.id}"))

            try:
                if local_file_path:
                    file = FSInputFile(local_file_path)
                    if local_file_path.endswith('.mp4'):
                        await self.bot.send_video(chat_id, video=file, caption=preview_body, reply_markup=builder.as_markup(), parse_mode="HTML")
                    else:
                        await self.bot.send_photo(chat_id, photo=file, caption=preview_body, reply_markup=builder.as_markup(), parse_mode="HTML")
                else:
                    await self.bot.send_message(chat_id, preview_body, reply_markup=builder.as_markup(), parse_mode="HTML")
            except Exception as e: logger.error(f"Notify error (Twitter): {e}")

    async def check_user_access(self, session, user):
        if user.is_admin or user.is_vip: return True
        today = date.today()
        count_res = await session.execute(select(func.count(PendingPost.id)).where(
            PendingPost.user_id == user.id, 
            PendingPost.created_at >= datetime.combine(today, datetime.min.time())
        ))
        count = count_res.scalar() or 0
        return count < 500 # Pro tarif uchun limitni kengaytirdik

    def find_media_recursive(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ['media_url_https', 'media_url', 'thumbnail_url', 'image_url']: return v
                if isinstance(v, str) and (v.startswith('http') and ('.jpg' in v or '.png' in v or '.jpeg' in v)):
                    if 'profile_images' not in v: return v
                res = self.find_media_recursive(v); 
                if res: return res
        elif isinstance(obj, list):
            for item in obj:
                res = self.find_media_recursive(item)
                if res: return res
        return None
