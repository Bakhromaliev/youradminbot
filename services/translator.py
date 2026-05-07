import os
import logging
import asyncio
import re
import traceback
import google.generativeai as genai
import httpx
from bot_database.models import BotSettings

logger = logging.getLogger(__name__)

class TranslatorService:
    def __init__(self):
        # Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key: api_key = api_key.strip()
        self.model_names = []
        if api_key:
            try:
                genai.configure(api_key=api_key)
                models = genai.list_models()
                self.model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
                logger.info(f"Gemini models found: {len(self.model_names)}")
            except Exception as e:
                logger.error(f"Gemini init error: {e}")
        
        # OpenAI
        raw_key = os.getenv("OPENAI_API_KEY")
        self.openai_key = raw_key.strip() if raw_key else None

    async def translate(self, text: str, target_lang: str = 'uz', target_alphabet: str = 'latin') -> str:
        if not text: return text
        
        if not re.search(r'[a-zA-Zа-яА-ЯёЁўЎғҒқҚҳҲ]', text):
            return text

        # Emojilarni HIMOYALASH
        emoji_pattern = r'\[\[emoji_id:[^\]]+\]\]'
        found_emojis = re.findall(emoji_pattern, text)
        protected_text = text
        for i, emoji_code in enumerate(found_emojis):
            protected_text = protected_text.replace(emoji_code, f'____{i}____', 1)

        lang_map = {'uz': 'Uzbek', 'ru': 'Russian', 'en': 'English'}
        target_name = lang_map.get(target_lang, 'Uzbek')
        alphabet_name = "LATIN SCRIPT" if target_alphabet == 'latin' else "CYRILLIC SCRIPT"

        system_instruction = (
            "Siz mashhur o'zbek sport blogerisiz. Vazifangiz futbol yangiliklarini o'zbek tiliga o'ta tabiiy va jonli tarjima qilish.\n"
            "USLUB QOIDALARI:\n"
            "- Kitobiy tildan qoching. Telegram kanaldagi kabi yozing.\n"
            "- Ispancha ismlar: 'Carvajal' -> 'Karvaxal', 'Juan' -> 'Xuan'.\n"
            "- MAJBURIY: Faqat lotin harflarida javob bering."
        )

        prompt = (
            f"Quyidagi xabarni {target_name} tiliga lotin alifbosida tarjima qiling:\n\n"
            f"MATN:\n{protected_text}"
        )

        translated_result = None

        # 1. OpenAI
        if self.openai_key:
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.openai_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.4
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        translated_result = data['choices'][0]['message']['content'].strip()
                        logger.info("✅ SUCCESS: ChatGPT used.")
            except Exception as e:
                logger.error(f"❌ OpenAI Exception: {str(e)}")

        # 2. Gemini Fallback
        if not translated_result and self.model_names:
            priority_models = [m for m in self.model_names if 'flash' in m.lower()] + self.model_names
            for m_name in priority_models:
                try:
                    model = genai.GenerativeModel(m_name, system_instruction=system_instruction)
                    resp = await asyncio.wait_for(
                        asyncio.to_thread(model.generate_content, prompt),
                        timeout=35.0
                    )
                    if resp and hasattr(resp, 'text') and resp.text:
                        translated_result = resp.text.strip()
                        logger.info(f"⚠️ FALLBACK SUCCESS: {m_name} used.")
                        break
                except Exception as ge:
                    logger.warning(f"❌ Gemini {m_name} failed: {ge}")
                    continue

        return self.restore_emojis(translated_result or protected_text, found_emojis, target_alphabet)

    def restore_emojis(self, text: str, original_emojis: list, target_alphabet: str) -> str:
        if target_alphabet == 'cyrillic':
            text = self.to_cyrillic(text)
        elif target_alphabet == 'latin':
            text = self.to_latin(text)
        for i, emoji_code in enumerate(original_emojis):
            text = text.replace(f'____{i}____', emoji_code)
        return text

    def to_latin(self, text: str) -> str:
        replacements = [
            ('ш', 'sh'), ('Ш', 'Sh'), ('ч', 'ch'), ('Ч', 'Ch'),
            ('ё', 'yo'), ('Ё', 'Yo'), ('ю', 'yu'), ('Ю', 'Yu'),
            ('я', 'ya'), ('Я', 'Ya'), ('ж', 'j'),  ('Ж', 'J'),
            ('ў', "o'"), ('Ў', "O'"), ('ғ', "g'"), ('Ғ', "G'"),
            ('қ', 'q'),  ('Қ', 'Q'),  ('ҳ', 'h'),  ('Ҳ', 'H'),
            ('аъ', "a'"), ('АЪ', "A'"), ('ъ', "'"), ('Ъ', "'"), ('ь', ''),
            ('А', 'A'), ('Б', 'B'), ('В', 'V'), ('Г', 'G'), ('Д', 'D'),
            ('Е', 'E'), ('З', 'Z'), ('И', 'I'), ('Й', 'Y'), ('К', 'K'),
            ('Л', 'L'), ('М', 'M'), ('Н', 'N'), ('О', 'O'), ('П', 'P'),
            ('Р', 'R'), ('С', 'S'), ('Т', 'T'), ('У', 'U'), ('Ф', 'F'),
            ('Х', 'X'), ('Ц', 'Ts'),
            ('а', 'a'), ('б', 'b'), ('в', 'v'), ('г', 'g'), ('д', 'd'),
            ('е', 'e'), ('з', 'z'), ('и', 'i'), ('й', 'y'), ('k', 'k'),
            ('л', 'l'), ('м', 'm'), ('n', 'n'), ('o', 'o'), ('p', 'p'),
            ('r', 'r'), ('s', 's'), ('t', 't'), ('u', 'u'), ('f', 'f'),
            ('x', 'x'), ('ts', 'ts'),
        ]
        res = text
        for src, dst in replacements:
            res = res.replace(src, dst)
        return res

    def to_cyrillic(self, text: str) -> str:
        # Har xil turdagi tutuq belgilarini bitta standartga keltirish
        for apostrophe in ["’", "‘", "`", "´", "ʻ"]:
            text = text.replace(apostrophe, "'")

        # 1. So'z boshidagi yoki unlidan keyingi 'E' ni 'Э' ga o'tkazish
        text = re.sub(r'(^|[^a-zA-Z0-9])E', r'\1Э', text)
        text = re.sub(r'(^|[^a-zA-Z0-9])e', r'\1э', text)
        
        res = text
        replacements = [
            ("O'", 'Ў'), ("o'", 'ў'), ("G'", 'Ғ'), ("g'", 'ғ'),
            ("A'", 'АЪ'), ("a'", 'аъ'),
            ('Sh', 'Ш'), ('sh', 'ш'), ('SH', 'Ш'),
            ('Ch', 'Ч'), ('ch', 'ч'), ('CH', 'Ч'),
            ('Yo', 'Ё'), ('yo', 'ё'), ('YO', 'Ё'),
            ('Yu', 'Ю'), ('yu', 'ю'), ('YU', 'Ю'),
            ('Ya', 'Я'), ('ya', 'я'), ('YA', 'Я'),
            ('Ye', 'Е'), ('ye', 'е'), ('YE', 'Е'),
            ('Ts', 'Ц'), ('ts', 'ц'),
            ('A', 'А'), ('B', 'Б'), ('D', 'Д'), ('E', 'Е'), ('F', 'Ф'),
            ('G', 'Г'), ('H', 'Ҳ'), ('I', 'И'), ('J', 'Ж'), ('K', 'К'),
            ('L', 'Л'), ('M', 'М'), ('N', 'Н'), ('O', 'О'), ('P', 'П'),
            ('Q', 'Қ'), ('R', 'Р'), ('S', 'С'), ('T', 'Т'), ('U', 'У'),
            ('V', 'В'), ('X', 'Х'), ('Y', 'Й'), ('Z', 'З'),
            ('а', 'а'), ('б', 'б'), ('д', 'д'), ('е', 'е'), ('ф', 'ф'),
            ('г', 'г'), ('ҳ', 'ҳ'), ('и', 'и'), ('ж', 'ж'), ('к', 'к'),
            ('л', 'л'), ('м', 'м'), ('н', 'н'), ('о', 'о'), ('п', 'п'),
            ('қ', 'қ'), ('r', 'р'), ('s', 'с'), ('t', 'т'), ('u', 'у'),
            ('v', 'в'), ('x', 'х'), ('y', 'й'), ('z', 'з'),
            ("'", 'ъ'),
        ]
        for src, dst in replacements:
            res = res.replace(src, dst)
        return res
