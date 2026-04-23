from telethon import events

import state
from utils import html, get_username, resolve_sender, send_me
from premium_emoji import by_line
from bot_client import client
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights


@client.on(events.NewMessage(func=lambda e: bool(state.bw_chat_id) and e.chat_id == state.bw_chat_id))
async def on_bw_chat_message(event):
    if not state.bw_words:
        return
    msg = event.message
    if not msg.text or msg.out:
        return
    text_lower = msg.text.lower()
    for word in state.bw_words:
        if word.lower() in text_lower:
            sender = await resolve_sender(msg)
            try:
                await msg.delete()
                print(f"[BW] Удалено сообщение от {getattr(sender, 'id', '?')}: {word!r}")
            except Exception as e:
                print(f"[BW] delete error: {e}")
            try:
                await client(EditBannedRequest(
                    channel=state.bw_chat_id,
                    participant=sender,
                    banned_rights=ChatBannedRights(until_date=None, view_messages=True)
                ))
                uname = get_username(sender)
                print(f"[BW] Забанен: {uname}")
                await send_me(
                    f"🚫 <b>Bad Word Filter</b>\n\n"
                    f"👤 {html(uname)} забанен\n"
                    f"🔤 Слово: <code>{html(word)}</code>\n\n" + by_line()
                )
            except Exception as e:
                print(f"[BW] ban error: {e}")
            return
