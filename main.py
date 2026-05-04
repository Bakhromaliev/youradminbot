import asyncio
import os
from pyrogram import Client
from dotenv import load_dotenv

load_dotenv()

async def get_session():
    api_id = int(os.getenv("API_ID"))
    api_hash = os.getenv("API_HASH")
    bot_token = os.getenv("BOT_TOKEN")
    
    print("LOG: Renderda sessiya olish boshlandi...")
    
    # Renderda bu albatta ishlaydi, chunki u yerda Python 3.10/3.11
    app = Client("temp_session", api_id=api_id, api_hash=api_hash)
    
    await app.start()
    session_string = await app.export_session_string()
    
    print("\n--- TAYYOR ---")
    print(f"SESSION_STRING_OLINDI: {session_string}")
    print("--- TAYYOR ---\n")
    
    await app.stop()

if __name__ == "__main__":
    asyncio.run(get_session())
