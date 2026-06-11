# MODULE_NAME = "Warpigs"
# MODULE_CMD  = ".autogrow"
# MODULE_DESC = "Автоматизация @warpigs_bot: автогроу, автобои, смена имени"

import asyncio
import logging
from telethon import events
from bot_client import client
from premium_emoji import by_line
import settings

logger = logging.getLogger("Warpigs")

K_GROW  = "warpigs_grow"
K_FIGHT = "warpigs_fight"
K_GROW_CHAT  = "warpigs_grow_chat"
K_FIGHT_CHAT = "warpigs_fight_chat"

DAY = 86400

_grow_task: asyncio.Task | None = None
_fight_task: asyncio.Task | None = None


async def _loop(kind: str, key_enabled: str, key_chat: str, command: str):
    while settings.get(key_enabled):
        chat_id = settings.get(key_chat)
        if chat_id:
            try:
                await client.send_message(int(chat_id), command)
            except Exception as e:
                logger.warning("Warpigs %s send failed: %s", kind, e)
        await asyncio.sleep(DAY)


def _ensure(kind: str):
    global _grow_task, _fight_task
    if kind == "grow":
        if settings.get(K_GROW) and (_grow_task is None or _grow_task.done()):
            _grow_task = asyncio.create_task(_loop("grow", K_GROW, K_GROW_CHAT, "/grow"))
    elif kind == "fight":
        if settings.get(K_FIGHT) and (_fight_task is None or _fight_task.done()):
            _fight_task = asyncio.create_task(_loop("fight", K_FIGHT, K_FIGHT_CHAT, "/fight"))


try:
    _ensure("grow")
    _ensure("fight")
except RuntimeError:
    pass


@client.on(events.NewMessage(pattern=r"^\.autogrow$", outgoing=True))
async def autogrow(event):
    settings.set_val(K_GROW, True)
    settings.set_val(K_GROW_CHAT, event.chat_id)
    _ensure("grow")
    try:
        await client.send_message(event.chat_id, "/grow")
    except Exception:
        pass
    await event.edit(
        "🐷 <b>Автоматический рост свиней:</b> <i>Включён.</i>\n"
        f"💬 Чат: <code>{event.chat_id}</code> • интервал 24ч.\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.ungrow$", outgoing=True))
async def ungrow(event):
    settings.set_val(K_GROW, False)
    await event.edit(
        "🐷 <b>Автоматический рост свиней:</b> <i>Выключен.</i>\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.autofight$", outgoing=True))
async def autofight(event):
    settings.set_val(K_FIGHT, True)
    settings.set_val(K_FIGHT_CHAT, event.chat_id)
    _ensure("fight")
    try:
        await client.send_message(event.chat_id, "/fight")
    except Exception:
        pass
    await event.edit(
        "⚔️ <b>Автоматические свиные бои:</b> <i>Включены.</i>\n"
        f"💬 Чат: <code>{event.chat_id}</code> • интервал 24ч.\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.unfight$", outgoing=True))
async def unfight(event):
    settings.set_val(K_FIGHT, False)
    await event.edit(
        "⚔️ <b>Автоматические свиные бои:</b> <i>Выключены.</i>\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.nameset(?:\s+(.+))?$", outgoing=True))
async def nameset(event):
    name = (event.pattern_match.group(1) or "").strip()
    if not name:
        await event.edit("⚠️ <b>Укажите имя для свиньи.</b>\n\n" + by_line(), parse_mode="html")
        return
    await client.send_message(event.chat_id, f"/name {name}")
    await event.edit(
        "✅ <b>Имя вашей свиньи отправлено!</b>\n"
        f"🆕 <b>Новое имя:</b> <code>{name}</code>\n\n" + by_line(),
        parse_mode="html",
    )
