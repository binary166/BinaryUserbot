"""
Утилиты: html-экранирование, имена, логи, resolve sender.
"""
import asyncio
from telethon.tl.types import User
from telethon.errors import FloodWaitError

import state
from config import MY_ID


def get_username(sender) -> str:
    if sender is None:
        return "Unknown"
    if hasattr(sender, "username") and sender.username:
        return f"@{sender.username}"
    first = getattr(sender, "first_name", "") or ""
    last  = getattr(sender, "last_name",  "") or ""
    return (first + " " + last).strip() or str(getattr(sender, "id", "?"))


def html(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def is_private_chat(event) -> bool:
    return bool(event.is_private)


async def send_me(text: str, file=None):
    """Отправляет лог в установленный чат для логов."""
    from bot_client import client  # ленивый импорт во избежание цикла
    try:
        await client.send_message(
            state.logs_chat_id, text,
            file=file, parse_mode="html", link_preview=False
        )
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 2)
    except Exception as e:
        print(f"[send_me error] {e}")


async def resolve_sender(msg) -> User | None:
    from bot_client import client
    try:
        sender = await msg.get_sender()
        if isinstance(sender, User):
            return sender
        if msg.sender_id:
            entity = await client.get_entity(msg.sender_id)
            if isinstance(entity, User):
                return entity
    except Exception as e:
        print(f"[resolve_sender] {e}")
    return None
