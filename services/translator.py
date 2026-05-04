import os
import logging
import asyncio
import re
import google.generativeai as genai
from bot.utils.texts import CYRILLIC_TO_LATIN, LATIN_TO_CYRILLIC

logger = logging.getLogger(__name__)

class TranslatorService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model_names = ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
        else:
            self.model_names = []
        
        logger.info("Translator Service updated with script-enforcement safety.")

    async def translate(self, text: str, target_lang: str = 'uz', target_alphabet: str = 'latin') -> str:
        if not text: return ""
        
        if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', text):
            return text

        lang_map = {'uz': 'Uzbek', 'ru': 'Russian', 'en': 'English'}
        target_name = lang_map.get(target_lang, 'Uzbek')
        
        # Alifbo buyrug'ini kuchaytiramiz
        alphabet_name = "LATIN SCRIPT (LOTIN ALIFBOSI)" if target_alphabet == 'latin' else "CYRILLIC SCRIPT (КРИЛЛ АЛИФБОСИ)"

        # Xavfsizlik sozlamalarini o'chiramiz (Futbol xabarlari ba'zida blocklanib qolmasligi uchun)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        for attempt in range(2):
            for m_name in self.model_names:
                try:
                    model = genai.GenerativeModel(m_name)
                    prompt = (
                        f"You are a master Sports Journalist and expert Uzbek linguist. \n"
                        f"TASK: Translate the sports post below into {target_name}. \n"
                        f"CRITICAL SCRIPT REQUIREMENT: You MUST use ONLY {alphabet_name}. Do NOT use any other script. \n"
                        f"STRICT RULES: \n"
                        f"1. STYLE: Native, professional football terminology. \n"
                        f"2. CYRILLIC RULES: If Cyrillic, ensure 'E' at start of words is 'Э'. \n"
                        f"3. FORMAT: Keep all spacing and empty lines exactly as they are. \n"
                        f"4. CLEANING (URGENT): You MUST REMOVE any source signatures, advertising slogans, and calls to action. \n"
                        f"   - REMOVE sentences like: 'Everything about Real Madrid in our channel', 'Join us', 'Subscribe'. \n"
                        f"   - REMOVE all Telegram links (e.g., t.me/...) and social media handles (@...). \n"
                        f"   - DO NOT translate advertisements. Just delete them from the text. \n"
                        f"5. Direct Output: Return ONLY the final translated news text. \n\n"
                        f"TEXT TO TRANSLATE:\n{text}"
                    )
                    
                    logger.info(f"Translating with {m_name} to {target_alphabet}...")
                    response = model.generate_content(prompt, safety_settings=safety_settings)
                    
                    if response and hasattr(response, 'text') and response.text:
                        translated = response.text.strip()
                        return translated
                    else:
                        logger.warning(f"Empty response from {m_name}. Safety reason: {response.prompt_feedback if hasattr(response, 'prompt_feedback') else 'Unknown'}")
                    
                except Exception as e:
                    err_msg = f"❌ Model {m_name} error: {e}"
                    logger.error(err_msg)
                    # Adminga xatolikni ko'rsatish uchun (vaqtinchalik debugging)
                    return f"DEBUG ERROR: {err_msg}\n\nORIGINAL TEXT:\n{text}"

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
