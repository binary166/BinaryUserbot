from telethon import events
from telethon.errors import ChatAdminRequiredError, UserAdminInvalidError
from telethon.tl.functions.channels import EditBannedRequest
from telethon.tl.types import ChatBannedRights

import state
from bot_client import client
from premium_emoji import by_line
from utils import get_username, html, resolve_sender, send_me


def _same_chat(event_chat_id: int | None, configured_chat_id: int | None) -> bool:
    if not event_chat_id or not configured_chat_id:
        return False
    if event_chat_id == configured_chat_id:
        return True

    event_str = str(event_chat_id)
    configured_str = str(configured_chat_id)

    if event_str.startswith("-100") and configured_chat_id > 0:
        return event_str[4:] == configured_str
    if configured_str.startswith("-100") and event_chat_id > 0:
        return configured_str[4:] == event_str
    return False


def _matched_bad_word(text: str) -> str | None:
    text_lower = (text or "").lower()
    for word in list(state.bw_words):
        clean_word = str(word or "").strip().lower()
        if clean_word and clean_word in text_lower:
            return clean_word
    return None


async def _ban_sender(event, sender) -> None:
    input_chat = await event.get_input_chat()
    try:
        input_sender = await event.get_input_sender()
    except Exception:
        input_sender = sender

    await client(
        EditBannedRequest(
            channel=input_chat,
            participant=input_sender,
            banned_rights=ChatBannedRights(until_date=None, view_messages=True),
        )
    )


@client.on(events.NewMessage(incoming=True))
async def on_bw_chat_message(event):
    if not state.bw_words or not _same_chat(event.chat_id, state.bw_chat_id):
        return

    msg = event.message
    text = getattr(msg, "raw_text", None) or msg.text or msg.message or ""
    bad_word = _matched_bad_word(text)
    if not bad_word:
        return

    sender = await resolve_sender(msg)
    if not sender:
        print("[BW] sender not found")
        return

    try:
        me = await client.get_me()
        if sender.id == me.id:
            return
    except Exception:
        pass

    uname = get_username(sender)

    delete_ok = False
    ban_ok = False
    error_text = ""

    try:
        await msg.delete()
        delete_ok = True
    except Exception as e:
        error_text += f"delete: {e}; "
        print(f"[BW] delete error: {e}")

    try:
        await _ban_sender(event, sender)
        ban_ok = True
        print(f"[BW] banned {getattr(sender, 'id', '?')}: {bad_word!r}")
    except (ChatAdminRequiredError, UserAdminInvalidError) as e:
        error_text += f"ban permissions: {e}; "
        print(f"[BW] ban permissions error: {e}")
    except Exception as e:
        error_text += f"ban: {e}; "
        print(f"[BW] ban error: {e}")

    status = "забанен" if ban_ok else "не забанен"
    deleted = "удалено" if delete_ok else "не удалено"
    await send_me(
        f"🚫 <b>Bad Word Filter</b>\n\n"
        f"👤 {html(uname)} {status}\n"
        f"🗑 Сообщение: <b>{deleted}</b>\n"
        f"🔤 Слово: <code>{html(bad_word)}</code>\n"
        f"💬 Чат: <code>{html(str(event.chat_id))}</code>"
        + (f"\n⚠️ <code>{html(error_text[:500])}</code>" if error_text else "")
        + "\n\n"
        + by_line()
    )
