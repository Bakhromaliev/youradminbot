import os
import logging
import asyncio
import re
import google.generativeai as genai
from bot.utils.texts import CYRILLIC_TO_LATIN, LATIN_TO_CYRILLIC

logger = logging.getLogger(__name__)

from deep_translator import GoogleTranslator

class TranslatorService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self.model_names = []
        if api_key:
            try:
                genai.configure(api_key=api_key)
                # Mavjud modellarni tekshiramiz
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Eng yaxshi modellarni saralab olamiz (ustuvorlik bo'yicha)
                priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro', 'models/gemini-1.0-pro']
                for p in priority:
                    if p in available_models:
                        self.model_names.append(p)
                
                if not self.model_names and available_models:
                    self.model_names = [available_models[0]] # Hech bo'lmasa bittasini olamiz
                
                logger.info(f"Translator Service: Available models discovered: {self.model_names}")
            except Exception as e:
                logger.error(f"Failed to list Gemini models: {e}")
        
    async def translate(self, text: str, target_lang: str = 'uz', target_alphabet: str = 'latin') -> str:
        if not text or not self.model_names: return text
        
        if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', text):
            return text

        lang_map = {'uz': 'Uzbek', 'ru': 'Russian', 'en': 'English'}
        target_name = lang_map.get(target_lang, 'Uzbek')
        alphabet_name = "LATIN SCRIPT" if target_alphabet == 'latin' else "CYRILLIC SCRIPT"

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        # Faqat Gemini bilan tarjima qilamiz
        for m_name in self.model_names:
            try:
                model = genai.GenerativeModel(m_name)
                prompt = (
                    f"Siz professional O'zbek sport jurnalisti va master blogersiz. \n"
                    f"VAZIFA: Quyidagi sport xabarini {target_name} ({alphabet_name}) tiliga shunday tarjima qilingki, u shunchaki tarjima emas, balki jonli va qiziqarli sport posti bo'lsin. \n"
                    f"QOIDALAR: \n"
                    f"1. SO'ZMA-SO'Z TARJIMA QILMANG: Gaplarni o'zbek tili tabiatiga moslab, ma'noli va chiroyli qilib qayta tuzing. \n"
                    f"2. FUTBOL TERMINOLOGIYASI: Professional futbol terminlaridan foydalaning (masalan: 'dubl qayd etdi', 'darvoza to'rini larzaga keltirdi', 'transfer bozorida shov-shuv'). \n"
                    f"3. PREMIUM EMOJILAR: Matndagi '[[emoji_id:...]]' formatidagi kodlarga mutlaqo tegmang va ularni tarjima qilmang. Ularni o'z joyida o'z holicha qoldiring. \n"
                    f"4. TOZALASH: Barcha begona linklar (@..., t.me/...) va reklamalarni olib tashlang. \n"
                    f"5. USLUB: Muxlislarga yoqadigan, hayajonli va professional uslubda yozing. \n"
                    f"6. FAQAT NATIJA: Hech qanday ortiqcha izohsiz, faqat tayyor post matnini qaytaring. \n\n"
                    f"XABAR MATNI:\n{text}"
                )
                response = model.generate_content(prompt, safety_settings=safety_settings)
                if response and hasattr(response, 'text') and response.text:
                    return response.text.strip()
            except Exception as e:
                logger.warning(f"Gemini {m_name} failed: {e}")
                continue

        return text

    def to_latin(self, text: str) -> str:
        res = text
        for k, v in CYRILLIC_TO_LATIN.items():
            res = res.replace(k, v)
        return res

    def to_cyrillic(self, text: str) -> str:
        res = text
        # Word-initial 'E' fix
        words = res.split()
        fixed_words = []
        for w in words:
            if w.lower().startswith('e'):
                # Bu yerda oddiy almashtirish biroz qiyin, shuning uchun bazaviy o'girishdan foydalanamiz
                pass
        
        for k, v in LATIN_TO_CYRILLIC.items():
            res = res.replace(k, v)
        return res
