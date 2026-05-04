import asyncio
import sys

# Python 3.14 uchun asyncio patch
def get_event_loop_patch():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

asyncio.get_event_loop = get_event_loop_patch

import nest_asyncio
nest_asyncio.apply()

from pyrogram import Client, errors

async def get_session():
    api_id = 33491503
    api_hash = "ebccd4e365c86b8d21ccfad411cd1d19"
    phone = "+998889575710"
    password = "2867171euro"
    
    app = Client(":memory:", api_id=api_id, api_hash=api_hash)
    await app.connect()
    
    try:
        sent_code = await app.send_code(phone)
        phone_code_hash = sent_code.phone_code_hash
        print("\n---KOD_YUBORILDI---")
        
        # Kodni kutamiz
        code = input("KOD:")
        
        try:
            await app.sign_in(phone, phone_code_hash, code)
        except errors.SessionPasswordNeeded:
            await app.check_password(password)
            
        session_string = await app.export_session_string()
        print("\n---SESSION_START---")
        print(session_string)
        print("---SESSION_END---")
        
    except Exception as e:
        print(f"Xatolik: {e}")
    finally:
        await app.disconnect()

if __name__ == "__main__":
    asyncio.run(get_session())
