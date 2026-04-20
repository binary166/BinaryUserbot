"""
Единственный экземпляр TelegramClient.
Все модули импортируют client отсюда.
"""
from telethon import TelegramClient
from config import SESSION_NAME, API_ID, API_HASH

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
