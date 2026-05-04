from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os

api_id = 33491503
api_hash = "ebccd4e365c86b8d21ccfad411cd1d19"

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\n--- TAYYOR ---")
    print("Sizning SESSION_STRING kodingiz:")
    print(client.session.save())
    print("--- TAYYOR ---\n")
