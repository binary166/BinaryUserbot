# MODULE_NAME = "Snoser"
# MODULE_CMD  = ".glban"
# MODULE_DESC = "Глобальный бан/мут/разбан/размут пользователя во всех чатах, где ты админ"

import re
import time
import asyncio
from telethon import events
from telethon.tl.types import (
    Channel, Chat, User, ChannelForbidden, ChatForbidden,
    ChatBannedRights, PeerUser, PeerChat, PeerChannel,
)
from telethon.tl.functions.channels import EditBannedRequest
from telethon.errors import FloodWaitError, ChatAdminRequiredError, UserAdminInvalidError

from bot_client import client
from premium_emoji import by_line
from utils import html
from config import LOADING
import settings

_BAN_RIGHTS = ChatBannedRights(
    until_date=None,
    view_messages=True, send_messages=True, send_media=True,
    send_stickers=True, send_gifs=True, send_games=True,
    send_inline=True, send_polls=True,
    change_info=True, invite_users=True, pin_messages=True,
)

_MUTE_RIGHTS = ChatBannedRights(
    until_date=None,
    send_messages=True, send_media=True,
    send_stickers=True, send_gifs=True, send_games=True,
    send_inline=True, send_polls=True,
)

_UNBAN_RIGHTS = ChatBannedRights(
    until_date=None,
    view_messages=False, send_messages=False, send_media=False,
    send_stickers=False, send_gifs=False, send_games=False,
    send_inline=False, send_polls=False,
    change_info=False, invite_users=False, pin_messages=False,
)

_cache = {"exp": 0, "chats": []}
_CACHE_TTL = 600


def _convert_time(t: str) -> int:
    if not t or not t[:-1].isdigit():
        return 0
    try:
        n = int(re.sub(r"[^0-9]", "", t))
    except ValueError:
        return 0
    mult = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    for k, v in mult.items():
        if k in t.lower():
            return n * v
    return 0


async def _parse_target(event, rest: str):
    reply = await event.get_reply_message()
    args = (rest or "").split()
    period = 0; reason_parts = []
    silent = False
    target = None

    filtered = []
    for a in args:
        if a == "-s":
            silent = True; continue
        t = _convert_time(a)
        if t and not period:
            period = t; continue
        filtered.append(a)

    if reply and not filtered:
        try:
            target = await client.get_entity(reply.sender_id)
        except Exception:
            target = None
    elif filtered:
        head = filtered[0]
        try:
            if head.lstrip("-").isdigit():
                target = await client.get_entity(int(head))
            else:
                target = await client.get_entity(head)
            reason_parts = filtered[1:]
        except Exception:
            if reply:
                try:
                    target = await client.get_entity(reply.sender_id)
                    reason_parts = filtered
                except Exception:
                    target = None
            else:
                target = None
    elif reply:
        try:
            target = await client.get_entity(reply.sender_id)
        except Exception:
            target = None

    reason = " ".join(reason_parts).strip() or "Не указана"
    return target, period, reason, silent


async def _admin_chats():
    now = time.time()
    if _cache["exp"] > now and _cache["chats"]:
        return _cache["chats"]
    chats = []
    async for dlg in client.iter_dialogs():
        ent = dlg.entity
        if isinstance(ent, (ChannelForbidden, ChatForbidden)):
            continue
        if isinstance(ent, Chat):
            if getattr(ent, "admin_rights", None) and getattr(ent.admin_rights, "ban_users", False):
                chats.append(ent)
            continue
        if isinstance(ent, Channel):
            if not (getattr(ent, "megagroup", False) or getattr(ent, "gigagroup", False)):
                continue
            ar = getattr(ent, "admin_rights", None)
            if ar and getattr(ar, "ban_users", False):
                chats.append(ent)
    _cache["exp"] = now + _CACHE_TTL
    _cache["chats"] = chats
    return chats


def _full_name(u) -> str:
    if isinstance(u, Channel):
        return u.title or "Channel"
    fn = getattr(u, "first_name", "") or ""
    ln = getattr(u, "last_name", "") or ""
    return (fn + " " + ln).strip() or str(getattr(u, "id", "?"))


def _entity_url(u) -> str:
    un = getattr(u, "username", None)
    if un:
        return f"https://t.me/{un}"
    uid = getattr(u, "id", 0)
    return f"tg://user?id={uid}"


async def _apply(action: str, chat, user, period: int = 0) -> bool:
    until = (int(time.time() + period)) if period else None
    if action == "ban":
        perms = dict(
            view_messages=False, send_messages=False, send_media=False,
            send_stickers=False, send_gifs=False, send_games=False,
            send_inline=False, send_polls=False,
            change_info=False, invite_users=False, pin_messages=False,
        )
    elif action == "mute":
        perms = dict(
            send_messages=False, send_media=False,
            send_stickers=False, send_gifs=False, send_games=False,
            send_inline=False, send_polls=False,
        )
    elif action in ("unban", "unmute"):
        perms = dict(
            view_messages=True, send_messages=True, send_media=True,
            send_stickers=True, send_gifs=True, send_games=True,
            send_inline=True, send_polls=True,
            change_info=True, invite_users=True, pin_messages=True,
        )
        until = None
    else:
        return False

    try:
        await client.edit_permissions(chat, user, until_date=until, **perms)
        return True
    except FloodWaitError as e:
        await asyncio.sleep(min(e.seconds + 1, 15))
        return False
    except (ChatAdminRequiredError, UserAdminInvalidError):
        return False
    except Exception:
        return False


async def _run_global(event, action: str, emoji_head: str, action_ru: str):
    rest = event.raw_text.split(None, 1)
    rest = rest[1] if len(rest) > 1 else ""
    parsed = await _parse_target(event, rest)
    if not parsed or not parsed[0]:
        await event.edit(
            f"🚫 <b>Неверные аргументы.</b> Используй ответом или укажи юзернейм/ID.\n\n"
            + by_line(),
            parse_mode="html",
        )
        return
    user, period, reason, silent = parsed

    url = _entity_url(user)
    name = html(_full_name(user))
    await event.edit(
        f"{emoji_head} <b>{action_ru} <a href=\"{url}\">{name}</a>...</b>",
        parse_mode="html",
    )

    chats = await _admin_chats()
    ok_chats = []
    for chat in chats:
        if await _apply(action, chat, user, period):
            ok_chats.append(chat)

    if silent or len(ok_chats) > 40:
        tail = f"<blockquote>✅ Успешно в <b>{len(ok_chats)}</b> чат(-ах) из <b>{len(chats)}</b></blockquote>"
    else:
        lines = []
        for c in ok_chats:
            cn = html(getattr(c, "title", "") or str(c.id))
            cu = getattr(c, "username", None)
            link = f"https://t.me/{cu}" if cu else f"tg://openmessage?chat_id={c.id}"
            lines.append(f"▫️ <a href=\"{link}\">{cn}</a>")
        listing = "\n".join(lines) or "<i>ничего</i>"
        tail = f"<blockquote expandable>{listing}</blockquote>\n<i>Всего: {len(ok_chats)}/{len(chats)}</i>"

    period_str = f"\n⏳ На: <code>{period}s</code>" if period else ""
    reason_str = f"\n<b>Причина:</b> <i>{html(reason)}</i>" if reason != "Не указана" else ""

    await event.edit(
        f"{emoji_head} <b><a href=\"{url}\">{name}</a></b>  —  <b>{action_ru}</b>"
        f"{period_str}{reason_str}\n\n{tail}\n\n" + by_line(),
        parse_mode="html", link_preview=False,
    )


@client.on(events.NewMessage(pattern=r"^\.glban(?:\s|$)", outgoing=True))
async def cmd_glban(event):
    await _run_global(event, "ban", "🔨", "Глобальный бан")


@client.on(events.NewMessage(pattern=r"^\.glunban(?:\s|$)", outgoing=True))
async def cmd_glunban(event):
    await _run_global(event, "unban", "🤗", "Глобальный разбан")


@client.on(events.NewMessage(pattern=r"^\.glmute(?:\s|$)", outgoing=True))
async def cmd_glmute(event):
    await _run_global(event, "mute", "🔇", "Глобальный мут")


@client.on(events.NewMessage(pattern=r"^\.glunmute(?:\s|$)", outgoing=True))
async def cmd_glunmute(event):
    await _run_global(event, "unmute", "🔊", "Глобальный размут")


@client.on(events.NewMessage(pattern=r"^\.snoser$", outgoing=True))
async def cmd_snoser_help(event):
    txt = (
        "☠️ <b>Snoser</b> — глобальный снос\n\n"
        "<blockquote>"
        "🔨 <code>.glban</code> [юзер/реплай] [причина] [время] [-s]\n"
        "🤗 <code>.glunban</code> [юзер/реплай]\n"
        "🔇 <code>.glmute</code> [юзер/реплай] [время]\n"
        "🔊 <code>.glunmute</code> [юзер/реплай]\n"
        "</blockquote>\n"
        "<i>Время: 30s, 5m, 2h, 1d. Флаг <code>-s</code> — тихо.</i>\n\n"
        + by_line()
    )
    await event.edit(txt, parse_mode="html")
