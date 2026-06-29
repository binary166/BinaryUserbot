# MODULE_NAME = "RandomAvatars"
# MODULE_CMD  = ".rpavatars"
# MODULE_DESC = "Случайные парные аватарки от @anime_4bot"

import os
import asyncio
import logging
import tempfile
from telethon import events
from telethon.tl.functions.channels import JoinChannelRequest
from bot_client import client
from premium_emoji import by_line

logger = logging.getLogger("RandomAvatars")

BOT      = "anime_4bot"
CHANNELS = ("anime4_avatarki", "anime4_arts")
TRIGGER  = "👫 Парные аватарки"


async def _ensure_subscribed():
    for ch in CHANNELS:
        try:
            await client(JoinChannelRequest(ch))
        except Exception as e:
            logger.debug("subscribe %s: %s", ch, e)


async def _grab_two_photos(timeout: float = 25.0) -> list[str]:
    """Шлём триггер боту, ловим следующие 2 фото-сообщения, скачиваем."""
    bot_entity = await client.get_entity(BOT)

    # маркер времени, чтобы не ловить старые сообщения
    last_id = 0
    async for m in client.iter_messages(bot_entity, limit=1):
        last_id = m.id

    received: list = []
    done = asyncio.Event()

    @client.on(events.NewMessage(from_users=bot_entity.id, incoming=True))
    async def _h(ev):
        if ev.message.id <= last_id:
            return
        if not ev.message.photo:
            return
        received.append(ev.message)
        if len(received) >= 2:
            done.set()

    try:
        await client.send_message(bot_entity, TRIGGER)
        try:
            await asyncio.wait_for(done.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            if len(received) < 2:
                raise
    finally:
        client.remove_event_handler(_h)

    tmp = tempfile.gettempdir()
    paths = []
    for i, msg in enumerate(received[:2]):
        path = os.path.join(tmp, f"rpavatar_{msg.id}_{i}.jpg")
        await client.download_media(msg, path)
        paths.append(path)
    return paths


@client.on(events.NewMessage(pattern=r"^\.rpavatars$", outgoing=True))
async def rpavatars(event):
    await event.edit("🖼 <b>Загружаю аватарки...</b>\n\n" + by_line(), parse_mode="html")

    try:
        await _ensure_subscribed()
        paths = await _grab_two_photos()
    except asyncio.TimeoutError:
        await event.edit(
            "❌ <b>Бот @anime_4bot не ответил вовремя.</b> Проверь ЛС с ним.\n\n" + by_line(),
            parse_mode="html",
        )
        return
    except Exception as e:
        logger.exception("rpavatars failed")
        await event.edit(
            f"❌ <b>Не удалось получить аватарки:</b> <code>{e}</code>\n"
            "Проверь ЛС с ботом @anime_4bot.\n\n" + by_line(),
            parse_mode="html",
        )
        return

    try:
        for p in paths:
            await client.send_file(event.chat_id, p)
        await event.delete()
    finally:
        for p in paths:
            try:
                os.remove(p)
            except Exception:
                pass
