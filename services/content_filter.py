"""
content_filter.py — Reklama va qimor targ'ibotlarini filterlash moduli.
Bu modul ikkala monitor (Telegram va Twitter) tomonidan ishlatiladi.
"""

import re

# =====================================================================
# QIMOR VA REKLAMA SO'ZLARI RO'YXATI
# =====================================================================
BLOCKED_KEYWORDS = [
    # --- Qimor saytlari (brendlar) ---
    "1xbet", "1x bet", "1хбет", "mostbet", "most bet", "мостбет",
    "melbet", "mel bet", "мелбет", "pinup", "pin-up", "pin up", "пин ап",
    "betway", "bet365", "betwinner", "bet winner", "winline", "leon bet",
    "fonbet", "fonbet", "фонбет", "parimatch", "pari match", "пари матч",
    "ggbet", "gg bet", "888casino", "vulkan", "вулкан казино",
    "olimpbet", "olimp bet", "олимп", "favbet", "fav bet",
    "vbet", "v bet", "betmaster", "linebet", "line bet",

    # --- Qimor so'zlari (o'zbek, rus, ingliz) ---
    "qimor", "qimorxona", "kazino", "casino", "каzino", "казино",
    "букмекер", "буkmeker", "букмейкер", "bukmeyer",
    "ставк", "stavka", "stavkalar", "tikish", "garov",
    "slotlar", "slot machine", "слот", "poker", "покер",
    "ruletka", "ruletka", "рулетка", "jackpot", "джекпот",
    "freespin", "free spin", "фриспин",
    "depozit bonus", "депозит бонус", "cashback bonus",
    "stavkangiz", "yutish kafolat", "yutib oling",

    # --- Reklama so'zlari ---
    "реклама", "reklama", "reklama uchun", "advertisement",
    "промокод", "promokod", "promo kod", "promo code", "promocode",
    "скидка", "chegirma", "discount",
    "перейти по ссылке", "havolaga o'ting", "linkga o'ting",
    "подписывайся", "obuna bo'ling", "subscribe now",
    "партнёр", "partner link", "affiliate",
    "зарабатывай", "ishlang va toping", "earn money",
    "пополни счёт", "hisob to'ldiring", "top up now",
    "ставь на спорт", "sportga tikish", "bet on sport",
]

# Tez tekshirish uchun kichik harfga o'tkazilgan ro'yxat
_BLOCKED_LOWER = [kw.lower() for kw in BLOCKED_KEYWORDS]


def is_spam_or_gambling(text: str) -> bool:
    """
    Matnda reklama yoki qimor kalit so'zlari borligini tekshiradi.
    True qaytarsa — post bloklangan, o'tkazib yuborilsin.
    """
    if not text:
        return False
    
    text_lower = text.lower()
    
    for keyword in _BLOCKED_LOWER:
        if keyword in text_lower:
            return True
    
    return False
