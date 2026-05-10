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
    def __init__(self, gemini_key: str = None, openai_key: str = None):
        api_key = gemini_key or os.getenv("GEMINI_API_KEY")
        if api_key: api_key = api_key.strip()
        self.model_names = []
        if api_key and api_key != "dummy":
            try:
                genai.configure(api_key=api_key)
                models = genai.list_models()
                self.model_names = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
            except Exception: pass
        
        raw_key = openai_key or os.getenv("OPENAI_API_KEY")
        self.openai_key = raw_key.strip() if raw_key and raw_key != "dummy" else None

    async def translate(self, text: str, target_lang: str = 'uz', target_alphabet: str = 'latin', is_twitter: bool = False) -> str:
        if not re.search(r'[a-zA-Zа-яА-ЯёЁўЎғҒқҚҳҲ\u0600-\u06FF]', text):
            return text

        emoji_pattern = r'\[\[emoji_id:[^\]]+\]\]'
        found_emojis = re.findall(emoji_pattern, text)
        protected_text = text
        for i, emoji_code in enumerate(found_emojis):
            protected_text = protected_text.replace(emoji_code, f'____{i}____', 1)

        # QAT'IY JURNALISTIK YO'RIQNOMA
        system_instruction = (
            "SIZ PROFESSIONAL SPORT JURNALISTISIZ. VAZIFANGIZ — INGLIZCHA YOKI RUSCHA SPORT XABARLARINI "
            "O'ZBEK TILIGA SO'ZMA-SO'Z EMAS, BALKI PROFESSIONAL SPORT NASHRLARI (CHAMPIONAT.ASIA, TRIBUNA.UZ) "
            "USLUBIDA QAYTA YOZIB BERISH.\n\n"
            "ASOSIY TALABLAR:\n"
            "1. GAP TUZILISHI: Inglizcha/ruscha gap tuzilishini butunlay buzing. O'zbek tilida gap har doim FE'L BILAN TUGASHINI ta'minlang.\n"
            "2. ISMLAR (RUSCHA USLUB): Barcha Yevropa va xorijiy ismlarni rus sport nashrlari (Sports.ru, Championat.com) qanday yozsa, "
            "o'zbek tiliga shunday transkripsiya qiling. Masalan: Huijsen -> Xyuysen, Courtois -> Kurtua, Mbappe -> Mbappe.\n"
            "3. SPORT TERMINLARI: 'Warm-up' so'zini 'Isinish' emas, 'O'yinoldi chigalyozdi mashg'ulotlari' deb tarjima qiling. "
            "'Felt weak/sick' so'zini 'O'zini noqulay his qildi' yoki 'Sog'lig'ida muammo sezdi' deb bering.\n"
            "4. MA'NO VA MANTIQ: Xabarni o'qib chiqib, uni jurnalistik tilda hikoya qilib bering. Robotga o'xshab qolmasin.\n"
            "5. ALIFBO: Faqat LOTIN alifbosida, hech qanday HTML teglarsiz (faqat xabarning o'zini) javob bering."
        )

        if is_twitter:
            system_instruction += (
                "\n6. TWITTER USLUBI: Xabar qisqa va tezkor bo'lsin. 'JUST IN', 'BREAKING' kabi so'zlarni tarjima qilmasdan qalin (bold) qoldiring."
            )

        prompt = (
            f"Quyidagi futbol xabarini o'zbek tilida, professional sport tahriri bilan qayta yozing:\n\n"
            f"MATN:\n{protected_text}"
        )

        translated_result = None

        # 1. OpenAI GPT-4o (Eng kuchli model)
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
                            "model": "gpt-4o",
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": 0.2 # Aniqroq tarjima uchun
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

        if not translated_result:
            return self.restore_emojis(protected_text, found_emojis, target_alphabet)

        translated_result = translated_result.replace('<', '&lt;').replace('>', '&gt;')

        if is_twitter:
            for kw in ["JUST IN", "CONFIRMED", "BREAKING"]:
                translated_result = translated_result.replace(f"{kw}:", f"<b>{kw}:</b>")
                translated_result = translated_result.replace(kw, f"<b>{kw}:</b>")
            translated_result = translated_result.replace("<b>JUST IN:</b>", "🚨 <b>JUST IN:</b>")
            translated_result = translated_result.replace("<b>CONFIRMED:</b>", "✅ <b>CONFIRMED:</b>")
            translated_result = translated_result.replace("<b>BREAKING:</b>", "📰 <b>BREAKING:</b>")

        return self.restore_emojis(translated_result, found_emojis, target_alphabet)

    def restore_emojis(self, text: str, original_emojis: list, target_alphabet: str) -> str:
        protected_sources = re.findall(r'\[\[\[(.*?)\]\]\]', text)
        for i, source in enumerate(protected_sources):
            text = text.replace(f'[[[{source}]]]', f'____SRC_{i}____')

        if target_alphabet == 'cyrillic':
            text = self.to_cyrillic(text)
        elif target_alphabet == 'latin':
            text = self.to_latin(text)
        
        for i, source in enumerate(protected_sources):
            text = text.replace(f'____SRC_{i}____', f"<b>{source}</b>")

        for i, emoji_code in enumerate(original_emojis):
            text = text.replace(f'____{i}____', emoji_code)
        
        text = text.replace("<b><b>", "<b>").replace("</b></b>", "</b>")
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
        for k, v in repl_map.items(): res = res.replace(k, v)
        return res

    def to_cyrillic(self, text: str) -> str:
        for a in ["’", "‘", "`", "´", "ʻ"]: text = text.replace(a, "'")
        text = re.sub(r'(^|[^a-zA-Z])E', r'\1Э', text)
        text = re.sub(r'(^|[^a-zA-Z])e', r'\1э', text)
        complex_repl = [
            ("O'", 'Ў'), ("o'", 'ў'), ("G'", 'Ғ'), ("g'", 'ғ'),
            ("A'", 'АЪ'), ("a'", 'аъ'),
            ('SH', 'Ш'), ('Sh', 'Ш'), ('sh', 'ш'),
            ('CH', 'Ч'), ('Ch', 'Ч'), ('ch', 'ч'),
            ('YO', 'Ё'), ('Yo', 'Ё'), ('yo', 'ё'),
            ('YU', 'Ю'), ('Yu', 'YU'), ('yu', 'yu'),
            ('YA', 'Я'), ('Ya', 'Ya'), ('ya', 'ya'),
            ('YE', 'Е'), ('Ye', 'Ye'), ('ye', 'ye'),
            ('TS', 'Ц'), ('Ts', 'Ts'), ('ts', 'ts')
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
