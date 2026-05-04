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
                    f"Sen futbolni yaxshi ko'radigan, o'zbek tilida yozadigan faol sport blogerisan. "
                    f"Quyidagi xabarni {target_name} tilida ({alphabet_name}) yoz — lekin rasmiy yoki kitobiy emas, "
                    f"oddiy, jonli, ko'cha tilida. Xuddi do'stingga futbol yangiligini aytayotgandek. "
                    f"Emoji va energiya bo'lsin, lekin ortiqcha emas.\n\n"
                    f"QOIDALAR:\n"
                    f"1. Ko'cha tili: 'qayd etdi' o'rniga 'qo'ydi', 'amalga oshirdi' o'rniga 'qildi' de. Tabiiy gapir.\n"
                    f"2. [[emoji_id:...]] kodlarini O'ZGARTIRMA, o'z joyida qoldir.\n"
                    f"3. Linklar, @username va reklamalarni O'CHIR.\n"
                    f"4. Faqat tayyor matnni qaytargin, hech qanday izoh yozma.\n\n"
                    f"XABAR:\n{text}"
                )
                response = model.generate_content(prompt, safety_settings=safety_settings)
                if response and hasattr(response, 'text') and response.text:
                    result = response.text.strip()
                    # Kirill majburiy tekshiruvi: agar kirill kerak bo'lsa va AI lotin qaytargan bo'lsa
                    if target_alphabet == 'cyrillic':
                        latin_count = len(re.findall(r'[a-zA-Z]', result))
                        cyrillic_count = len(re.findall(r'[а-яА-ЯёЁ]', result))
                        if latin_count > cyrillic_count:
                            logger.warning(f"AI returned Latin for Cyrillic request. Force-converting...")
                            result = self.to_cyrillic(result)
                    return result
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
        for k, v in LATIN_TO_CYRILLIC.items():
            res = res.replace(k, v)
        return res
