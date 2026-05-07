import os
import logging
import asyncio
import re
import google.generativeai as genai
from openai import AsyncOpenAI
from bot_database.models import BotSettings

logger = logging.getLogger(__name__)

class TranslatorService:
    def __init__(self):
        # Gemini sozlamalari
        api_key = os.getenv("GEMINI_API_KEY")
        self.model_names = []
        if api_key:
            try:
                genai.configure(api_key=api_key)
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                priority = ['models/gemini-1.5-flash', 'models/gemini-1.5-pro']
                for p in priority:
                    if p in available_models: 
                        self.model_names.append(p)
                if not self.model_names and available_models: 
                    self.model_names = [available_models[0]]
                logger.info(f"Translator Service: Gemini models: {self.model_names}")
            except Exception as e:
                logger.error(f"Failed to list Gemini models: {e}")
        
        # OpenAI sozlamalari
        self.openai_client = None
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = AsyncOpenAI(api_key=openai_key)
            logger.info("Translator Service: OpenAI ChatGPT initialized.")

    def post_process(self, result: str, target_alphabet: str, original_text: str) -> str:
        """Tarjimadan keyingi ishlov berish (alifbo va emojilar)"""
        # [[emoji_id:...]] larni saqlab qolamiz
        emoji_pattern = r'\[\[emoji_id:[^\]]+\]\]'
        placeholders = re.findall(emoji_pattern, result)
        
        for i, ph in enumerate(placeholders):
            result = result.replace(ph, f'§{i}§', 1)
        
        # Alifboni o'girish
        if target_alphabet == 'cyrillic':
            result = self.to_cyrillic(result)
        elif target_alphabet == 'latin':
            result = self.to_latin(result)
            
        # Emojilarni qaytarish
        for i, ph in enumerate(placeholders):
            result = result.replace(f'§{i}§', ph)
            
        return result

    async def translate(self, text: str, target_lang: str = 'uz', target_alphabet: str = 'latin') -> str:
        if not text: return text
        
        # Faqat harflar bor matnlarni tarjima qilamiz
        if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', text):
            return text

        lang_map = {'uz': 'Uzbek', 'ru': 'Russian', 'en': 'English'}
        target_name = lang_map.get(target_lang, 'Uzbek')
        alphabet_name = "LATIN SCRIPT" if target_alphabet == 'latin' else "CYRILLIC SCRIPT"

        prompt = (
            f"Siz O'zbek tilida yozadigan tajribali sport muxbirisiz.\n"
            f"Quyidagi xabarni {target_name} tiliga tarjima qiling.\n\n"
            f"MAJBURIY ALIFBO: Faqat {alphabet_name} ishlating. "
            f"Hech qanday aralash yozuv bo'lmasin.\n\n"
            f"QOIDALAR:\n"
            f"1. Tarjimani tushunarli, ravon va ma'noli qiling. Sport muxbiri uslubida bo'lsin.\n"
            f"2. Futbol atamalarini to'g'ri ishlating.\n"
            f"3. [[emoji_id:...]] formatidagi kodlarni o'zgartirmang.\n"
            f"4. Linklar va reklamalarni o'chiring.\n"
            f"5. Faqat tayyor tarjima matnini qaytaring.\n\n"
            f"MATN:\n{text}"
        )

        # 1. ChatGPT orqali tarjima (Asosiy)
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Siz sport muxbirisiz."}, {"role": "user", "content": prompt}],
                    temperature=0.3
                )
                result = response.choices[0].message.content.strip()
                return self.post_process(result, target_alphabet, text)
            except Exception as e:
                logger.error(f"OpenAI translation failed: {e}")

        # 2. Gemini orqali tarjima (Fallback)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        for m_name in self.model_names:
            try:
                model = genai.GenerativeModel(m_name)
                response = model.generate_content(prompt, safety_settings=safety_settings)
                if response and hasattr(response, 'text') and response.text:
                    result = response.text.strip()
                    return self.post_process(result, target_alphabet, text)
            except Exception as e:
                logger.warning(f"Gemini {m_name} failed: {e}")
                continue

        return text

    def to_latin(self, text: str) -> str:
        """Kirillni lotinga o'giradi"""
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
        """Lotinni kirillga o'giradi"""
        res = text
        for apostrophe in ["’", "‘", "`", "´", "ʻ"]:
            res = res.replace(apostrophe, "'")
        
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
            ('a', 'а'), ('b', 'б'), ('d', 'д'), ('e', 'е'), ('f', 'ф'),
            ('g', 'г'), ('h', 'ҳ'), ('i', 'и'), ('j', 'ж'), ('k', 'к'),
            ('l', 'л'), ('m', 'м'), ('n', 'н'), ('o', 'о'), ('p', 'п'),
            ('q', 'қ'), ('r', 'р'), ('s', 'с'), ('t', 'т'), ('u', 'у'),
            ('v', 'в'), ('x', 'х'), ('y', 'й'), ('z', 'з'),
            ("'", 'ъ'),
        ]
        for src, dst in replacements:
            res = res.replace(src, dst)
        return res
