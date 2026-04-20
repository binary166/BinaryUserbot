"""
Логирование изменённых и удалённых сообщений в личных чатах.
"""
from telethon import events
from telethon.tl.types import User

import state
from utils import html, get_username, resolve_sender, send_me
from bot_client import client


@client.on(events.MessageEdited)
async def on_edit(event):
    if not event.is_private:
        return
    msg = event.message
    if msg.out or msg.id in state.animating_msgs:
        return

    sender = await resolve_sender(msg)
    if sender and sender.id in state.muted_users.get(msg.chat_id, set()):
        return

    old      = state.message_store.get(msg.id, {})
    old_text = old.get("text", "(текст недоступен)")
    new_text = msg.text or ""
    uname    = get_username(sender)

    await send_me(
        f"✏️ <b>{html(uname)}</b> изменил сообщение\n\n"
        f"<b>Было:</b>\n<blockquote>{html(old_text)}</blockquote>\n\n"
        f"<b>Стало:</b>\n<blockquote>{html(new_text)}</blockquote>"
    )
    state.message_store[msg.id] = {**old, "text": new_text}


@client.on(events.MessageDeleted)
async def on_delete(event):
    for msg_id in event.deleted_ids:
        stored = state.message_store.pop(msg_id, None)
        if not stored or msg_id in state.animating_msgs:
            continue
        sender = stored.get("sender")
        if sender:
            sid = getattr(sender, "id", None)
            if sid and sid in state.muted_users.get(stored.get("chat_id", 0), set()):
                continue
        try:
            chat = await client.get_entity(stored["chat_id"])
            if not isinstance(chat, User):
                continue
        except Exception:
            continue
        await send_me(
            f"🗑 <b>{html(get_username(sender))}</b> удалил сообщение\n\n"
            f"<b>Текст:</b>\n<blockquote>{html(stored.get('text', '(медиафайл)'))}</blockquote>"
        )
