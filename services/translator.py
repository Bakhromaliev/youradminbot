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
            except Exception: pass
        
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

        system_instruction = (
            "Siz O'zbekistondagi eng mashhur futbol blogerisiz. Vazifangiz xorijiy xabarlarni O'zbekiston muxlislari uchun ONA TILIDAGI kabi tabiiy yetkazish.\n"
            "MUHIM QOIDALAR:\n"
            "- So'zma-so'z tarjima qilmang! Gaplarni o'zbek tili qoidalariga (Ega, to'ldiruvchi, kesim tartibiga) moslab, mazmunan qayta yozing.\n"
            "- Xuddi o'zbek tilida yozilgan postdek tuyulsin. Chet ellikning talaffuzi sezilmasin.\n"
            "- 'Carvajal' -> 'Karvaxal', 'Real Madrid' -> 'Real Madrid'.\n"
            "- Sport terminologiyasidan professional foydalaning.\n"
            "- MAJBURIY: Faqat LOTIN (LATIN) alifbosida, eng sifatli o'zbek tilida javob bering."
        )

        prompt = (
            f"Quyidagi futbol xabarini o'zbek tiliga ona tilida so'zlashuvchi bloger uslubida, gap tartibini to'g'rilab tarjima qiling:\n\n"
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
                            "temperature": 0.5
                        }
                    )
                    if response.status_code == 200:
                        translated_result = response.json()['choices'][0]['message']['content'].strip()
            except Exception: pass

        # 2. Gemini Fallback
        if not translated_result and self.model_names:
            try:
                model = genai.GenerativeModel(self.model_names[0], system_instruction=system_instruction)
                resp = model.generate_content(prompt)
                if resp and resp.text:
                    translated_result = resp.text.strip()
            except Exception: pass

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
        repl_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'j', 'з': 'z',
            'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
            'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'x', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'ъ': "'",
            'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya', 'ў': "o'", 'ғ': "g'", 'қ': 'q', 'ҳ': 'h',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'J', 'З': 'Z',
            'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R',
            'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'X', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Ъ': "'",
            'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya', 'Ў': "O'", 'Ғ': "G'", 'Қ': 'Q', 'Ҳ': 'H'
        }
        res = text
        for k, v in repl_map.items():
            res = res.replace(k, v)
        return res

    def to_cyrillic(self, text: str) -> str:
        for a in ["’", "‘", "`", "´", "ʻ"]: text = text.replace(a, "'")
        text = re.sub(r'(^|[^a-zA-Z])E', r'\1Э', text)
        text = re.sub(r'(^|[^a-zA-Z])e', r'\1э', text)
        complex_repl = [
            ("O'", 'Ў'), ("o'", 'ў'), ("G'", 'Ғ'), ("g'", 'ғ'),
            ("A'", 'АЪ'), ("a'", 'аъ'),
            ('Sh', 'Ш'), ('sh', 'ш'), ('Ch', 'Ч'), ('ch', 'ч'),
            ('Yo', 'Ё'), ('yo', 'ё'), ('Yu', 'Ю'), ('yu', 'ю'),
            ('Ya', 'Я'), ('ya', 'я'), ('Ye', 'Е'), ('ye', 'е'), ('Ts', 'Ц'), ('ts', 'ц')
        ]
        for s, d in complex_repl: text = text.replace(s, d)
        single_repl = {
            'A': 'А', 'B': 'Б', 'D': 'Д', 'F': 'Ф', 'G': 'Г', 'H': 'Ҳ', 'I': 'И', 'J': 'Ж', 'K': 'К',
            'L': 'Л', 'M': 'М', 'N': 'Н', 'O': 'О', 'P': 'П', 'Q': 'Қ', 'R': 'Р', 'S': 'С', 'T': 'Т',
            'U': 'У', 'V': 'В', 'X': 'Х', 'Y': 'Й', 'Z': 'З', 'E': 'Е',
            'a': 'а', 'b': 'б', 'd': 'д', 'f': 'ф', 'g': 'г', 'h': 'ҳ', 'i': 'и', 'j': 'ж', 'k': 'к',
            'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'q': 'қ', 'r': 'р', 's': 'с', 't': 'т',
            'u': 'у', 'v': 'в', 'x': 'х', 'y': 'й', 'z': 'з', 'e': 'е', "'": 'ъ'
        }
        for s, d in single_repl.items(): text = text.replace(s, d)
        return text
