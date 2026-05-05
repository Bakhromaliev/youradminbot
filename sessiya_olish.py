import os
try:
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("Telethon kutubxonasi topilmadi. O'rnatilmoqda...")
    os.system("pip3 install telethon")
    from telethon.sync import TelegramClient
    from telethon.sessions import StringSession

# Sizning API ma'lumotlaringiz
api_id = 33491503
api_hash = 'ebccd4e365c86b8d21ccfad411cd1d19'

print("\n" + "="*50)
print("TELEGRAM SESSYIA OLISH DASTURI")
print("="*50)
print("\nHozir sizdan telefon raqamingiz va Telegramga kelgan kod so'raladi.\n")

try:
    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session_str = client.session.save()
        print("\n" + "SUCCESS!".center(50, "="))
        print("\nSizning yangi TELEGRAM_SESSION kodingiz (NUSXALANG):\n")
        print(session_str)
        print("\n" + "="*50)
        print("\nUshbu kodni nusxalab Render'dagi TELEGRAM_SESSION qiymatiga qo'ying va Save bosing.\n")
except Exception as e:
    print(f"\nXato yuz berdi: {e}")
    print("\nAgar API_ID yoki API_HASH xato bo'lsa, my.telegram.org saytidan qaytadan oling.")
