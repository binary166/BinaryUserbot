# MODULE_NAME = "HistoryFacts"
# MODULE_CMD  = ".rfact"
# MODULE_DESC = "Случайные исторические факты (.rfact / .hfact / .mfact / .sfact)"

import json
import random
import logging
import aiohttp
from telethon import events
from bot_client import client
from premium_emoji import by_line

logger = logging.getLogger("HistoryFacts")

URL = "https://raw.githubusercontent.com/KorenbZla/HikkaModules/main/HistoryFacts.json"

_cache: dict | None = None


async def _fetch() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    async with aiohttp.ClientSession() as s:
        async with s.get(URL, timeout=aiohttp.ClientTimeout(total=15)) as r:
            r.raise_for_status()
            text = await r.text()
    _cache = json.loads(text)
    return _cache


async def _send_fact(event, key: str, header: str):
    try:
        data = await _fetch()
    except Exception as e:
        logger.warning("fetch failed: %s", e)
        await event.edit(
            f"❌ <b>Ошибка при загрузке данных:</b> <code>{e}</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    items = data.get(key)
    if not isinstance(items, list) or not items:
        await event.edit("⚠️ <b>Ключ не найден или пуст.</b>\n\n" + by_line(), parse_mode="html")
        return

    fact = random.choice(items)
    await event.edit(f"{header}\n\n{fact}\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.rfact$", outgoing=True))
async def rfact(event):
    await _send_fact(event, "RandomFact", "📜 <b>Случайный факт о Великой Отечественной войне:</b>")


@client.on(events.NewMessage(pattern=r"^\.hfact$", outgoing=True))
async def hfact(event):
    await _send_fact(event, "AdolfFact", "📜 <b>Случайный факт об Адольфе Гитлере:</b>")


@client.on(events.NewMessage(pattern=r"^\.mfact$", outgoing=True))
async def mfact(event):
    await _send_fact(event, "MussoliniFact", "📜 <b>Случайный факт о Бенито Муссолини:</b>")


@client.on(events.NewMessage(pattern=r"^\.sfact$", outgoing=True))
async def sfact(event):
    await _send_fact(event, "StalinFact", "📜 <b>Случайный факт об Иосифе Сталине:</b>")
