from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from bot.utils.texts import get_text

def get_main_menu_keyboard(lang='uz', is_vip=False, is_admin=False):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text=get_text('btn_sources', lang)))
    builder.row(types.KeyboardButton(text=get_text('btn_my_channels', lang)))
    
    # Admin uchun faqat Boshqaruv, oddiy foydalanuvchi uchun VIP
    if is_admin:
        builder.row(types.KeyboardButton(text="🛠 Boshqaruv"))
    else:
        builder.row(types.KeyboardButton(text=get_text('btn_vip', lang)))

    builder.row(
        types.KeyboardButton(text=get_text('btn_settings', lang)),
        types.KeyboardButton(text=get_text('btn_stats', lang))
    )
    return builder.as_markup(resize_keyboard=True)

def get_settings_keyboard(lang='uz'):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text=get_text('btn_change_lang', lang)))
    builder.row(types.KeyboardButton(text=get_text('btn_main_menu', lang)))
    return builder.as_markup(resize_keyboard=True)

def get_cancel_keyboard(lang='uz'):
    builder = ReplyKeyboardBuilder()
    builder.row(types.KeyboardButton(text=get_text('btn_cancel', lang)))
    return builder.as_markup(resize_keyboard=True)
