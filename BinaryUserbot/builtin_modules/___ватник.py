# MODULE_NAME = "Ватник"
# MODULE_CMD  = ".tvatnik"
# MODULE_DESC = "Ватник-режим: автоматически меняет з/о/в на Z/O/V в исходящих + .vat по реплаю"

from telethon import events
from bot_client import client
from premium_emoji import by_line
import settings

if settings.get("vatnik_enabled") is None:
    settings.set_val("vatnik_enabled", False)

TRANSLATE_MAP = {
    ord("з"): "Z", ord("З"): "Z", ord("z"): "Z", ord("Z"): "Z",
    ord("о"): "O", ord("О"): "O", ord("o"): "O", ord("O"): "O",
    ord("в"): "V", ord("В"): "V", ord("v"): "V", ord("V"): "V",
}


@client.on(events.NewMessage(pattern=r"^\.tvatnik$", outgoing=True))
async def cmd_tvatnik(event):
    enabled = not settings.get("vatnik_enabled", False)
    settings.set_val("vatnik_enabled", enabled)
    if enabled:
        text = "🇷🇺 <b>Ватник включён.</b> Страна может спать спокойно.\n\n" + by_line()
    else:
        text = "❌ <b>Ватник выключен.</b>\n\n" + by_line()
    await event.edit(text, parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.vat(?:\s|$)", outgoing=True))
async def cmd_vat(event):
    reply = await event.get_reply_message()
    if not reply or not reply.raw_text:
        await event.edit("⚠️ <b>Ответь на сообщение.</b>", parse_mode="html")
        return
    translated = reply.raw_text.translate(TRANSLATE_MAP)
    await event.edit(
        f"🇷🇺 <b>Заватненное сообщение:</b>\n\n{translated}\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(outgoing=True))
async def vatnik_watcher(event):
    if not settings.get("vatnik_enabled", False):
        return
    raw = event.raw_text or ""
    if not raw or raw.startswith("."):
        return
    translated = raw.translate(TRANSLATE_MAP)
    if translated == raw:
        return
    try:
        await event.edit(translated)
    except Exception:
        pass
