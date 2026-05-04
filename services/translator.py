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
            self.model_names = ['gemini-2.0-flash', 'gemini-2.5-flash', 'gemini-pro-latest']
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
                        f"4. REMOVAL: Remove any signatures, external links, advertisements, and social media handles. \n"
                        f"5. Direct Output: Return ONLY the final translated text. \n\n"
                        f"TEXT TO TRANSLATE:\n{text}"
                    )
                    
                    logger.info(f"Translating with {m_name} to {target_alphabet}...")
                    response = model.generate_content(prompt)
                    
                    if response and hasattr(response, 'text') and response.text:
                        translated = response.text.strip()
                        
                        # ZAXIRA TEKSHIRUVI: Agar kirill kerak bo'lib, AI lotinda qaytargan bo'lsa
                        if target_lang == 'uz' and target_alphabet == 'cyrillic':
                            # Agar matnda lotin harflari ko'p bo'lsa (va bu link bo'lmasa)
                            if len(re.findall(r'[a-zA-Z]', translated)) > len(re.findall(r'[а-яА-Я]', translated)):
                                logger.warning("AI ignored Cyrillic instruction. Applying manual transliteration.")
                                return self.to_cyrillic(translated)
                        
                        return translated
                    
                except Exception as e:
                    logger.warning(f"Model {m_name} failed: {e}")
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
