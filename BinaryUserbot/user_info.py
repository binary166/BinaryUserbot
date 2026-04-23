import io
import aiohttp
from telethon.tl.types import User, Channel, Chat
from telethon.tl.functions.channels import GetParticipantRequest

from utils import html, get_username, resolve_sender
from premium_emoji import pe, by_line
from config import BOT_NAME, BOT_VERSION, CREATOR_ID
import settings


def estimate_reg_date(uid: int) -> str:
    ranges = [
        (100_000_000, "до 2014"), (500_000_000, "2014–2015"),
        (1_000_000_000, "2015–2016"), (1_500_000_000, "2016–2017"),
        (2_000_000_000, "2017–2018"), (3_000_000_000, "2018–2019"),
        (4_000_000_000, "2019–2020"), (5_000_000_000, "2020–2021"),
        (6_000_000_000, "2021"), (7_000_000_000, "2022"),
        (8_000_000_000, "2022–2023"), (9_000_000_000, "2023"),
        (10_000_000_000, "2024"),
    ]
    for max_id, period in ranges:
        if uid < max_id:
            return period
    return "2024+"


async def get_user_info(event) -> str:
    from bot_client import client

    reply = await event.message.get_reply_message()
    if not reply:
        return "❗ Используй <code>.info</code> <b>ответом</b> на сообщение."

    target = await resolve_sender(reply)
    if not target:
        return "❌ Не удалось получить данные."

    uid      = target.id
    fname    = getattr(target, "first_name", "") or ""
    lname    = getattr(target, "last_name",  "") or ""
    fullname = (fname + " " + lname).strip() or "—"
    uname_str = get_username(target)

    flags = []
    if getattr(target, "bot",     False): flags.append("🤖 Бот")
    if getattr(target, "scam",    False): flags.append("🚨 Скам")
    if getattr(target, "fake",    False): flags.append("⚠️ Фейк")
    if getattr(target, "premium", False): flags.append("⭐ Premium")

    import asyncio as _asyncio

    async def _msg_count():
        try:
            res = await client.get_messages(event.chat_id, from_user=uid, limit=0)
            return getattr(res, "total", 0)
        except Exception:
            return -1

    async def _join_date():
        try:
            chat = await event.get_chat()
            part = await client(GetParticipantRequest(chat, target))
            p = part.participant
            if hasattr(p, "date") and p.date:
                return p.date.strftime("%d.%m.%Y")
        except Exception:
            pass
        return "—"

    msg_count, join_date_str = await _asyncio.gather(_msg_count(), _join_date())

    flags_str   = "  ".join(flags) if flags else "—"
    msg_cnt_str = "недоступно" if msg_count < 0 else str(msg_count)

    return (
        f'<tg-emoji emoji-id="5870994129244131212">👤</tg-emoji> <b>{html(fullname)}</b>  ·  <code>{html(uname_str)}</code>\n'
        f'<tg-emoji emoji-id="5226513232549664618">🔢</tg-emoji> <code>{uid}</code>  ·  {estimate_reg_date(uid)}\n'
        f'---\n'
        f'<tg-emoji emoji-id="5258132936401624790">⬅️</tg-emoji> Сообщений:  <code>{msg_cnt_str}</code>\n'
        f'<tg-emoji emoji-id="5258419835922030550">🕔</tg-emoji> В чате с  {join_date_str}\n'
        f'<tg-emoji emoji-id="5296348778012361146">🏷</tg-emoji> Флаги  {flags_str}\n'
        f'---\n'
        f'<i>{BOT_NAME} {BOT_VERSION}</i>  ·  {by_line()}'
    )


async def cmd_me(event) -> tuple[str, bytes | None]:
    from bot_client import client

    me       = await client.get_me()
    uid      = me.id
    fname    = getattr(me, "first_name", "") or ""
    lname    = getattr(me, "last_name",  "") or ""
    fullname = (fname + " " + lname).strip() or "—"
    uname_str = get_username(me)

    try:
        res = await client.get_messages(event.chat_id, from_user=uid, limit=0)
        msg_count = getattr(res, "total", 0)
    except Exception:
        msg_count = -1
    msg_cnt_str = "недоступно" if msg_count < 0 else str(msg_count)

    custom_text = settings.get("custom_me_text")

    if custom_text:
        text = custom_text
        text = text.replace("(ник)", f"<b>{html(fullname)}</b>")
        text = text.replace("(юзернейм)", f"<b>{html(uname_str)}</b>")
        text = text.replace("(айди)", f"<b>{uid}</b>")
        text = text.replace("(год)", f"<b>{estimate_reg_date(uid)}</b>")
        text = text.replace("(чат)", f"<b>{msg_cnt_str}</b>")
    else:
        flags = []
        if getattr(me, "premium", False): flags.append("⭐ Premium")
        if getattr(me, "bot",     False): flags.append("🤖 Бот")
        flags_str = "  ".join(flags) if flags else "—"

        creator_line = ""
        if uid == CREATOR_ID:
            creator_line = f'\n{pe("cloak")} <b>Создатель</b> {BOT_NAME}\n'

        text = (
            f'<tg-emoji emoji-id="5870994129244131212">👤</tg-emoji> <b>{html(fullname)}</b>  ·  <code>{html(uname_str)}</code>\n'
            f'<tg-emoji emoji-id="5226513232549664618">🔢</tg-emoji> <code>{uid}</code>  ·  {estimate_reg_date(uid)}\n'
            f'<tg-emoji emoji-id="5296348778012361146">🏷</tg-emoji> Флаги  {flags_str}'
            + creator_line +
            f'\n---\n'
            f'<tg-emoji emoji-id="5258132936401624790">⬅️</tg-emoji> Сообщений:  <code>{msg_cnt_str}</code>\n'
            f'---\n'
            f'<i>{BOT_NAME} {BOT_VERSION}</i>  ·  {by_line()}'
        )

    custom_pic_url = settings.get("custom_me_pic")
    photo = None

    if custom_pic_url:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(custom_pic_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        photo = await resp.read()
        except Exception:
            pass

    if photo is None and not custom_pic_url:
        try:
            photo = await client.download_profile_photo(me, bytes)
        except Exception:
            pass

    return text, photo


async def cmd_stat() -> str:
    from bot_client import client

    channels = 0
    public_groups = 0
    private_chats = 0
    bots = 0
    total = 0
    try:
        async for dialog in client.iter_dialogs():
            total += 1
            entity = dialog.entity
            if isinstance(entity, Channel):
                if entity.broadcast: channels += 1
                else: public_groups += 1
            elif isinstance(entity, Chat):
                public_groups += 1
            elif isinstance(entity, User):
                if entity.bot: bots += 1
                else: private_chats += 1
    except Exception as e:
        return f"❌ <b>Ошибка:</b> <code>{html(str(e))}</code>"

    arrow = '<tg-emoji emoji-id="5258215850745275216">➡️</tg-emoji>'
    return (
        '<blockquote><tg-emoji emoji-id="5258391025281408576">📈</tg-emoji> Статистика диалогов</blockquote>\n\n'
        f'Каналы: <code>{channels}</code>\n'
        f'Группы/супергруппы: <code>{public_groups}</code>\n'
        f'Личные переписки: <code>{private_chats}</code>\n'
        f'Боты: <code>{bots}</code>\n'
        f' \n'
        f'{arrow} Итого диалогов: <code>{total}</code>\n\n'
        + by_line()
    )
