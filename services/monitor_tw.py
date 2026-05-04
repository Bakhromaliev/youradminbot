import os
import logging
import asyncio
import httpx
import re
from datetime import datetime
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import Source, SourceChannelLink, OutputChannel, User, PendingPost
from services.translator import TranslatorService
from aiogram import Bot, types as aiotypes
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.utils.texts import get_text

logger = logging.getLogger(__name__)

class TwitterMonitor:
    def __init__(self, translator: TranslatorService, bot: Bot, interval: int = 1800):
        self.translator = translator
        self.bot = bot
        self.interval = interval
        self.processed_tweets = set()
        self.initialized_sources = set()
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.api_host = os.getenv("RAPIDAPI_HOST")

    async def start(self):
        logger.info("Twitter Monitor starting (Optimized Deep Scanner)...")
        if not self.api_key: return
        while True:
            try:
                await self.check_all_twitter_unique_sources()
            except Exception as e:
                logger.error(f"Twitter loop error: {e}")
            await asyncio.sleep(self.interval) 

    async def check_all_twitter_unique_sources(self):
        async with AsyncSessionLocal() as session:
            # Barcha Twitter manbalarini va ularning egalarini yig'amiz
            result = await session.execute(select(Source).where(Source.source_type == "twitter"))
            all_sources = result.scalars().all()
            
            if not all_sources: return
            
            # Manbalarni handle (username) bo'yicha guruhlaymiz
            grouped_sources = {}
            for src in all_sources:
                username = src.source_id.replace("@", "").strip().lower()
                if username not in grouped_sources:
                    grouped_sources[username] = []
                grouped_sources[username].append(src)
            
            # Har bir unikal username uchun 1 marta API chaqiramiz
            for username, sources in grouped_sources.items():
                await self.fetch_tweets_api_optimized(username, sources)
                await asyncio.sleep(5) # API orasida kichik to'xtalish

    async def fetch_tweets_api_optimized(self, username, sources_list):
        url = f"https://{self.api_host}/timeline.php"
        params = {"screenname": username}
        headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }

        try:
            async with httpx.AsyncClient(timeout=40) as client:
                response = await client.get(url, headers=headers, params=params)
                if response.status_code != 200: return
                data = response.json()
                
                # 'timeline' yoki 'results' kalitini qidiramiz
                tweets = data.get('timeline', []) if isinstance(data, dict) else data
                if not isinstance(tweets, list): return

                # Eng so'nggi 3 ta tweetni tekshiramiz
                async with AsyncSessionLocal() as session:
                    for tweet in tweets[:3]:
                        if tweet.get('retweeted') or 'retweeted_status' in tweet: continue
                        
                        tweet_id = str(tweet.get('tweet_id') or tweet.get('id_str') or tweet.get('id'))
                        if not tweet_id: continue
                        
                        # Dublikatni tekshirish (Bazadan qidiramiz)
                        existing = await session.execute(
                            select(PendingPost).where(PendingPost.source_type == "twitter", PendingPost.original_text.contains(tweet_id))
                        )
                        if existing.scalar_one_or_none(): continue
                        
                        raw_text = tweet.get('text') or tweet.get('full_text') or ""
                        if not raw_text: continue
                    
                    raw_text = tweet.get('text') or tweet.get('full_text') or ""
                    media_url = self.find_media_recursive(tweet)
                    
                    # Agressiv tozalash (Barcha turdagi linklar va username'lar)
                    clean_text = re.sub(r'https?://\S+', '', raw_text)
                    clean_text = re.sub(r't\.me/\S+', '', clean_text)
                    clean_text = re.sub(r'tg://\S+', '', clean_text)
                    clean_text = re.sub(r'www\.\S+', '', clean_text)
                    clean_text = re.sub(r'@\w+', '', clean_text)
                    clean_text = clean_text.strip()

                    if not clean_text and not media_url: continue

                    # ENDI: Ushbu tweetni barcha ushbu manbani kuzatuvchi foydalanuvchilarga tarqatamiz
                    for source_record in sources_list:
                        await self.process_single_tweet_for_user(tweet_id, clean_text, media_url, source_record)
                        
        except Exception as e:
            logger.error(f"API Error for @{username}: {e}")

    async def process_single_tweet_for_user(self, tweet_id, text, media_url, source_obj):
        async with AsyncSessionLocal() as session:
            # Ushbu manbaga bog'langan barcha kanallarni olamiz
            stmt = select(SourceChannelLink).where(SourceChannelLink.source_id == source_obj.id)
            result = await session.execute(stmt)
            links = result.scalars().all()
            
            if not links: return

            user_res = await session.execute(select(User).where(User.id == source_obj.user_id))
            user = user_res.scalar_one_or_none()
            if not user: return

            # LIMIT TEKSHIRISH
            if not user.is_vip and not user.is_admin:
                today = datetime.utcnow().strftime('%Y-%m-%d')
                if user.last_post_date != today:
                    user.daily_post_count = 0
                    user.last_post_date = today
                
                if user.daily_post_count >= 5:
                    if user.daily_post_count == 5:
                        try: await self.bot.send_message(user.telegram_id, get_text('limit_reached', user.bot_language), parse_mode="HTML")
                        except: pass
                        user.daily_post_count += 1
                        await session.commit()
                    return
                
                user.daily_post_count += 1

            for link in links:
                ch_res = await session.execute(select(OutputChannel).where(OutputChannel.id == link.channel_db_id))
                channel = ch_res.scalar_one()

                translated = await self.translator.translate(text, target_lang=channel.target_lang, target_alphabet=channel.alphabet)
                
                final_text = translated
                if channel.signature:
                    sig = channel.signature
                    if channel.is_bold_signature: sig = f"<b>{sig}</b>"
                    spacing = "\n" * (channel.signature_spacing + 1)
                    final_text += spacing + sig

                # DB ga saqlash (tweet_id bilan birga)
                db_text = f"{text}\n\n#tw_id:{tweet_id}"
                new_pending = PendingPost(
                    user_id=user.id, 
                    link_id=link.id, 
                    source_type="twitter", 
                    original_text=db_text, 
                    translated_text=translated, 
                    media_url=media_url
                )
                session.add(new_pending)
                await session.commit()

                builder = InlineKeyboardBuilder()
                builder.row(aiotypes.InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_post_{new_pending.id}"),
                            aiotypes.InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_post_{new_pending.id}"),
                            aiotypes.InlineKeyboardButton(text="📝 Tahrirlash", callback_data=f"edit_post_{new_pending.id}"))

                try:
                    if media_url:
                        await self.bot.send_photo(user.telegram_id, photo=media_url, caption=final_text, reply_markup=builder.as_markup(), parse_mode="HTML")
                    else:
                        await self.bot.send_message(user.telegram_id, final_text, reply_markup=builder.as_markup(), parse_mode="HTML")
                except Exception as e:
                    logger.error(f"Notify error: {e}")

    def find_media_recursive(self, obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ['media_url_https', 'media_url', 'thumbnail_url', 'image_url']:
                    return v
                if isinstance(v, str) and (v.startswith('http') and ('.jpg' in v or '.png' in v or '.jpeg' in v)):
                    if 'profile_images' not in v:
                        return v
                res = self.find_media_recursive(v)
                if res: return res
        elif isinstance(obj, list):
            for item in obj:
                res = self.find_media_recursive(item)
                if res: return res
        return None
