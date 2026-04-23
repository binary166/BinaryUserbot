import copy
import struct
import asyncio
from telethon.tl.types import (
    User,
    MessageEntityBold, MessageEntityItalic, MessageEntityCode,
    MessageEntityPre, MessageEntityUnderline, MessageEntityStrike,
    MessageEntityCustomEmoji, MessageEntitySpoiler, MessageEntityTextUrl,
    MessageEntityBlockquote,
)
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
    from bot_client import client
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


def _add_surrogate(text):
    return ''.join(
        ''.join(chr(y) for y in struct.unpack('<2H', x.encode('utf-16le')))
        if (0x10000 <= ord(x) <= 0x10FFFF) else x for x in text
    )


def _del_surrogate(text):
    return text.encode('utf-16', 'surrogatepass').decode('utf-16')


def entities_to_html(text, entities):
    if not text:
        return ""
    if not entities:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    text = _add_surrogate(text)

    opens = {}
    closes = {}

    for ent in sorted(entities, key=lambda e: (e.offset, -e.length)):
        start = ent.offset
        end = start + ent.length

        if isinstance(ent, MessageEntityBold):
            o, c = "<b>", "</b>"
        elif isinstance(ent, MessageEntityItalic):
            o, c = "<i>", "</i>"
        elif isinstance(ent, MessageEntityCode):
            o, c = "<code>", "</code>"
        elif isinstance(ent, MessageEntityPre):
            o, c = "<pre>", "</pre>"
        elif isinstance(ent, MessageEntityUnderline):
            o, c = "<u>", "</u>"
        elif isinstance(ent, MessageEntityStrike):
            o, c = "<s>", "</s>"
        elif isinstance(ent, MessageEntityCustomEmoji):
            o = f'<tg-emoji emoji-id="{ent.document_id}">'
            c = '</tg-emoji>'
        elif isinstance(ent, MessageEntitySpoiler):
            o, c = '<tg-spoiler>', '</tg-spoiler>'
        elif isinstance(ent, MessageEntityTextUrl):
            url = (ent.url or "").replace('"', '&quot;')
            o = f'<a href="{url}">'
            c = '</a>'
        elif isinstance(ent, MessageEntityBlockquote):
            o, c = '<blockquote>', '</blockquote>'
        else:
            continue

        opens.setdefault(start, []).append(o)
        closes.setdefault(end, []).insert(0, c)

    result = []
    for i in range(len(text) + 1):
        if i in closes:
            result.extend(closes[i])
        if i in opens:
            result.extend(opens[i])
        if i < len(text):
            ch = text[i]
            if ch == '&':
                result.append('&amp;')
            elif ch == '<':
                result.append('&lt;')
            elif ch == '>':
                result.append('&gt;')
            else:
                result.append(ch)

    return _del_surrogate("".join(result))


def extract_formatted_body(text, entities, prefix_len):
    body = text[prefix_len:]
    prefix_utf16_len = len(_add_surrogate(text[:prefix_len]))
    total_utf16_len = len(_add_surrogate(text))

    adjusted = []
    for e in (entities or []):
        e_start = e.offset
        e_end = e_start + e.length

        if e_end <= prefix_utf16_len:
            continue

        new_start = max(e_start - prefix_utf16_len, 0)
        new_end = min(e_end, total_utf16_len) - prefix_utf16_len
        new_len = new_end - new_start

        if new_len <= 0:
            continue

        new_e = copy.copy(e)
        new_e.offset = new_start
        new_e.length = new_len
        adjusted.append(new_e)

    return entities_to_html(body, adjusted)
