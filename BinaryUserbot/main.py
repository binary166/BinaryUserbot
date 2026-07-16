import asyncio
import sys
try:
    sys.stdout.reconfigure(line_buffering=True)
except Exception:
    pass

import state
from config import (
    PHONE, PASSWORD_2FA, OR_MODEL, BOT_NAME, BOT_VERSION, MY_ID,
    CONFIG_PATH, missing_required_values,
)
from bot_client import client, ensure_runtime_permissions
from premium_emoji import pe, by_line
from utils import send_me
import settings

import handlers.command_normalizer
import handlers.bw_handler
import handlers.channel_handler
import handlers.edit_delete_handler
import handlers.commands
import handlers.new_commands

from module_loader import load_all_saved, run_deferred_startups
import manager_bot


async def main():
    missing = missing_required_values()
    if missing:
        print("[CONFIG] Не заполнены обязательные поля: " + ", ".join(missing))
        print(f"[CONFIG] Запустите: python setup_config.py")
        print(f"[CONFIG] Файл настроек: {CONFIG_PATH}")
        return

    state.ai_semaphore = asyncio.Semaphore(2)
    ensure_runtime_permissions()

    settings.load(default_logs_id=MY_ID)

    state.eng_mode_active       = settings.get("eng_mode_active", False)
    state.premium_emoji_active  = settings.get("premium_emoji_active", True)
    state.logs_chat_id          = settings.get("logs_chat_id", MY_ID)
    state.bw_words              = list(settings.get("bw_words", []))
    state.bw_chat_id            = settings.get("bw_chat_id", 0)
    state.auto_comment_channels = settings.get_auto_comment_channels()

    load_all_saved()

    await client.start(phone=PHONE, password=PASSWORD_2FA)
    await manager_bot.start_manager_bot()
    await manager_bot.flush_pending_post_restart_notice()
    await manager_bot.start_update_monitor()
    await run_deferred_startups()
    me = await client.get_me()
    print(f"[OK] {me.first_name} (@{me.username})")

    ch_count = len(state.auto_comment_channels)
    bw_info  = f"<code>{state.bw_chat_id}</code>" if state.bw_chat_id else "<i>не задан</i>"
    active_or_model = settings.get("or_model") or OR_MODEL
    manager_hint = ""
    if not settings.get("manager_bot_token"):
        manager_hint = (
            "\n\n<blockquote><b>Привяжите бота к юзерботу командой .sb, "
            "это откроет вам новый большой функционал.</b></blockquote>"
        )
    await send_me(
        f'<tg-emoji emoji-id="5370869711888194012">🤖</tg-emoji> <b>{BOT_NAME} {BOT_VERSION}</b>\n\n'
        f'<tg-emoji emoji-id="5951665890079544884">✅</tg-emoji> Запущен\n'
        f'<tg-emoji emoji-id="5913787972200698358">🧠</tg-emoji> AI: <code>{active_or_model}</code>\n'
        f'<tg-emoji emoji-id="6008258140108231117">📡</tg-emoji> Каналов: <code>{ch_count}</code>\n'
        f'<tg-emoji emoji-id="5778423822940114949">🔒</tg-emoji> BW чат: {bw_info}\n\n'
        f"Напиши <code>.help</code> для команд.{manager_hint}\n\n" + by_line()
    )
    print("[OK] Работаю... (Ctrl+C для выхода)")
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass
    asyncio.run(main())
