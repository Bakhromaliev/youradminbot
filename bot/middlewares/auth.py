import os
import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, types
from sqlalchemy import select
from database.db import AsyncSessionLocal
from database.models import User
from bot.utils.texts import get_text
from aiogram.utils.keyboard import InlineKeyboardBuilder

SUPER_ADMIN_ID = int(os.getenv("ADMIN_ID", "1400240097"))
logger = logging.getLogger(__name__)

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, (types.Message, types.CallbackQuery)):
            return await handler(event, data)

        user_id = event.from_user.id
        
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(User).where(User.telegram_id == user_id))
                user = result.scalar_one_or_none()
                
                # Yangi: Har doim state-ni tozalash (Menyu tugmalari bosilganda)
                if isinstance(event, types.Message) and event.text:
                    menu_buttons = [
                        get_text('btn_sources', 'uz'), get_text('btn_sources', 'ru'), get_text('btn_sources', 'en'),
                        get_text('btn_my_channels', 'uz'), get_text('btn_my_channels', 'ru'), get_text('btn_my_channels', 'en'),
                        get_text('btn_settings', 'uz'), get_text('btn_settings', 'ru'), get_text('btn_settings', 'en'),
                        get_text('btn_stats', 'uz'), get_text('btn_stats', 'ru'), get_text('btn_stats', 'en'),
                        get_text('btn_vip', 'uz'), get_text('btn_vip', 'ru'), get_text('btn_vip', 'en'),
                        "🛠 Boshqaruv", "🏠 Asosiy menyu", "❌ Bekor qilish"
                    ]
                    if any(btn in event.text for btn in menu_buttons) or event.text.startswith('/'):
                        state = data.get('state')
                        if state: await state.clear()

                if not user:
                    user = User(telegram_id=user_id, username=event.from_user.username, is_approved=True)
                    if user_id == SUPER_ADMIN_ID: user.is_admin = True; user.is_vip = True
                    session.add(user)
                    await session.commit()
                elif user_id == SUPER_ADMIN_ID and not user.is_admin:
                    user.is_admin = True; user.is_vip = True
                    await session.commit()
        except Exception as e:
            logger.error(f"❌ AuthMiddleware Error: {e}")
        
        return await handler(event, data)
