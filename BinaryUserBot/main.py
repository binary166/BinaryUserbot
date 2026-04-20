"""
Binary Userbot v1.5 — точка входа.

Запуск:
    python main.py

Зависимости:
    pip install telethon aiohttp yt-dlp
"""
import asyncio
import state
from config import PHONE, PASSWORD_2FA, OR_MODEL, BOT_NAME, BOT_VERSION, MY_ID, BW_CHAT_ID_DEFAULT
from bot_client import client
from premium_emoji import pe, by_line
from utils import send_me
import settings

import handlers.bw_handler
import handlers.channel_handler
import handlers.edit_delete_handler
import handlers.commands
import handlers.new_commands

from module_loader import load_all_saved


async def main():
    state.ai_semaphore = asyncio.Semaphore(2)

    settings.load(
        default_logs_id=MY_ID,
        default_bw_chat_id=BW_CHAT_ID_DEFAULT,
    )

    state.eng_mode_active       = settings.get("eng_mode_active", False)
    state.premium_emoji_active  = settings.get("premium_emoji_active", True)
    state.logs_chat_id          = settings.get("logs_chat_id", MY_ID)
    state.bw_words              = list(settings.get("bw_words", []))
    state.bw_chat_id            = settings.get("bw_chat_id", 0)
    state.auto_comment_channels = settings.get_auto_comment_channels()

    load_all_saved()

    await client.start(phone=PHONE, password=PASSWORD_2FA)
    me = await client.get_me()
    print(f"[OK] {me.first_name} (@{me.username})")

    ch_count = len(state.auto_comment_channels)
    bw_info  = f"<code>{state.bw_chat_id}</code>" if state.bw_chat_id else "<i>не задан</i>"
    await send_me(
        f"{pe('alien')} <b>{BOT_NAME} {BOT_VERSION}</b>\n\n"
        f"✅ Запущен\n"
        f"{pe('brain')} AI: <code>{OR_MODEL}</code>\n"
        f"📡 Каналов: <code>{ch_count}</code>\n"
        f"🔒 BW чат: {bw_info}\n\n"
        f"Напиши <code>.help</code> для команд.\n\n" + by_line()
    )
    print("[OK] Работаю... (Ctrl+C для выхода)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
