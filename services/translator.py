import os
import logging
import asyncio
import re
import google.generativeai as genai
from openai import AsyncOpenAI
from bot_database.models import BotSettings
import httpx

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
            except Exception as e:
                logger.error(f"Failed to list Gemini models: {e}")
        
        # OpenAI sozlamalari (HTTP/1.1 ga majburlaymiz, aloqa barqaror bo'lishi uchun)
        self.openai_client = None
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            self.openai_client = AsyncOpenAI(
                api_key=openai_key,
                timeout=httpx.Timeout(60.0, connect=15.0),
                http_client=httpx.AsyncClient(http1=True) # Barqarorlik uchun HTTP/1.1
            )
            logger.info("Translator Service: OpenAI ChatGPT initialized (HTTP/1.1).")

    async def translate(self, text: str, target_lang: str = 'uz', target_alphabet: str = 'latin') -> str:
        if not text: return text
        
        # 1. Emojilarni HIMOYALASH
        emoji_pattern = r'\[\[emoji_id:[^\]]+\]\]'
        found_emojis = re.findall(emoji_pattern, text)
        protected_text = text
        for i, emoji_code in enumerate(found_emojis):
            protected_text = protected_text.replace(emoji_code, f'____{i}____', 1)

        if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', protected_text):
            return self.restore_emojis(protected_text, found_emojis, target_alphabet)

        lang_map = {'uz': 'Uzbek', 'ru': 'Russian', 'en': 'English'}
        target_name = lang_map.get(target_lang, 'Uzbek')
        alphabet_name = "LATIN SCRIPT" if target_alphabet == 'latin' else "CYRILLIC SCRIPT"

        prompt = (
            f"Siz O'zbek tilida yozadigan tajribali sport muxbirisiz.\n"
            f"Quyidagi xabarni {target_name} tiliga tarjima qiling.\n\n"
            f"MAJBURIY ALIFBO: Faqat {alphabet_name} ishlating. "
            f"Hech qanday aralash yozuv bo'lmasin.\n\n"
            f"QOIDALAR:\n"
            f"1. Tarjimani tushunarli va ravon qiling. Sport muxbiri uslubida bo'lsin.\n"
            f"2. Futbol atamalarini to'g'ri ishlating.\n"
            f"3. ____0____, ____1____ kabi kodlarni o'zgartirmang.\n"
            f"4. Linklar va reklamalarni o'chiring.\n"
            f"5. Faqat tayyor tarjima matnini qaytaring.\n\n"
            f"MATN:\n{protected_text}"
        )

        translated_result = None

        # ChatGPT (Primary)
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": "Siz sport muxbirisiz."}, {"role": "user", "content": prompt}],
                    temperature=0.3
                )
                translated_result = response.choices[0].message.content.strip()
                if translated_result:
                    logger.info("✅ SUCCESS: Translation done by ChatGPT.")
            except Exception as e:
                logger.error(f"❌ OpenAI error: {e}")

        # Gemini (Fallback)
        if not translated_result and self.model_names:
            try:
                model = genai.GenerativeModel(self.model_names[0])
                resp = await asyncio.wait_for(
                    asyncio.to_thread(model.generate_content, prompt),
                    timeout=40.0
                )
                if resp and hasattr(resp, 'text') and resp.text:
                    translated_result = resp.text.strip()
                    logger.info("⚠️ FALLBACK: Translation done by Gemini.")
            except Exception as ge:
                logger.warning(f"❌ Gemini fallback failed: {ge}")

        if not translated_result:
            translated_result = protected_text
            logger.warning("❗ WARNING: All translation engines failed. Using original text.")

        return self.restore_emojis(translated_result, found_emojis, target_alphabet)

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
