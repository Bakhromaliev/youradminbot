import os
import logging
import asyncio
import httpx
import re
from datetime import datetime
from sqlalchemy import select
from bot_database.db import AsyncSessionLocal
from bot_database.models import Source, SourceChannelLink, OutputChannel, User, PendingPost
from services.translator import TranslatorService
from aiogram import Bot, types as aiotypes
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.texts import get_text

logger = logging.getLogger(__name__)

class TwitterMonitor:
    def __init__(self, translator: TranslatorService, bot: Bot, interval: int = 1800):
        self.translator = translator; self.bot = bot; self.interval = interval
        self.api_key = os.getenv("RAPIDAPI_KEY"); self.api_host = os.getenv("RAPIDAPI_HOST")

    async def start(self):
        if not self.api_key: return
        while True:
            try: await self.check_all_twitter_unique_sources()
            except Exception as e: logger.error(f"Twitter loop error: {e}")
            await asyncio.sleep(self.interval) 

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
                await self.fetch_tweets_api_optimized(u, sources); await asyncio.sleep(5)

    async def fetch_tweets_api_optimized(self, username, sources_list):
        url = f"https://{self.api_host}/timeline.php"; params = {"screenname": username}
        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.api_host}
        try:
            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code != 200: return
                data = response.json(); tweets = data.get('timeline', []) if isinstance(data, dict) else data
                if not isinstance(tweets, list): return
                async with AsyncSessionLocal() as session:
                    for tweet in tweets[:3]:
                        if tweet.get('retweeted') or 'retweeted_status' in tweet: continue
                        t_id = str(tweet.get('tweet_id') or tweet.get('id_str') or tweet.get('id'))
                        if not t_id: continue
                        existing = await session.execute(select(PendingPost).where(PendingPost.source_type == "twitter", PendingPost.original_text.contains(t_id)))
                        if existing.scalar_one_or_none(): continue
                        raw_text = tweet.get('text') or tweet.get('full_text') or ""
                        if not raw_text: continue
                        media_url = self.find_media_recursive(tweet)
                        clean_text = re.sub(r'https?://\S+|t\.me/\S+|tg://\S+|www\.\S+|@\w+', '', raw_text).strip()
                        if not clean_text and not media_url: continue
                        for src in sources_list: await self.process_unified_tweet(t_id, clean_text, media_url, src)
        except Exception as e: logger.error(f"API Error for @{username}: {e}")

    async def process_unified_tweet(self, tweet_id, text, media_url, source_obj):
        async with AsyncSessionLocal() as session:
            links = (await session.execute(select(SourceChannelLink).where(SourceChannelLink.source_id == source_obj.id))).scalars().all()
            if not links: return
            user = (await session.execute(select(User).where(User.id == source_obj.user_id))).scalar_one_or_none()
            if not user: return

            translated = await self.translator.translate(text, target_lang='uz', target_alphabet='latin', is_twitter=True)
            db_text = f"{text}\n\n#tw_id:{tweet_id}"
            new_pending = PendingPost(user_id=user.id, source_id=source_obj.id, source_type="twitter", original_text=db_text, translated_text=translated, media_url=media_url)
            session.add(new_pending); await session.commit()

            channel_names = []
            for link in links:
                ch = (await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))).scalar_one()
                channel_names.append(f"📢 {ch.channel_name}")
            
            channels_str = "\n".join(channel_names)
            header = f"🆕 <b>SHERIK: Yangi post (Twitter)!</b>\n\n📍 <b>Yuboriladigan kanallar:</b>\n{channels_str}\n\n"
            caption = f"{header}📝 <b>Tarjima (Nusxalash uchun):</b>\n<code>{translated}</code>"
            
            chat_id = user.admin_channel_id if user.admin_channel_id else user.telegram_id
            builder = InlineKeyboardBuilder()
            builder.row(aiotypes.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{new_pending.id}"),
                        aiotypes.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{new_pending.id}"))
            builder.row(aiotypes.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{new_pending.id}"))

            try:
                if len(caption) <= 1000:
                    if media_url: await self.bot.send_photo(chat_id, photo=media_url, caption=caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                    else: await self.bot.send_message(chat_id, caption, reply_markup=builder.as_markup(), parse_mode="HTML")
                else:
                    if media_url: await self.bot.send_photo(chat_id, photo=media_url)
                    await self.bot.send_message(chat_id, caption, reply_markup=builder.as_markup(), parse_mode="HTML")
            except Exception as e: logger.error(f"Notify error (Twitter): {e}")

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
