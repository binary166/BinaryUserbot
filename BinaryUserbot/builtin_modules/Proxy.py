# MODULE_NAME = "Proxy"
# MODULE_CMD  = ".gproxy"
# MODULE_DESC = "Получение и проверка прокси (.gproxy / .wproxy / .proxylink)"

import random
import asyncio
import aiohttp

from telethon import events
from bot_client import client
from premium_emoji import by_line
from utils import html as esc
import settings

_LINK_KEY  = "proxy_link"
_CHECK_KEY = "proxy_check"

_DEFAULT_LINK = None  # пользователь задаёт через .proxylink <url>


async def _check(proto: str, ip: str, port: str, timeout: int = 5) -> bool:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "http://example.com",
                proxy=f"{proto}://{ip}:{port}",
                timeout=timeout,
            ) as res:
                return res.status == 200
    except Exception:
        return False


@client.on(events.NewMessage(pattern=r"^\.proxylink(?:\s+(\S+))?$", outgoing=True))
async def cmd_proxy_link(event):
    arg = event.pattern_match.group(1)
    if arg:
        settings.set_val(_LINK_KEY, arg)
        await event.edit(
            f"🔗 <b>Ссылка на прокси сохранена:</b>\n<code>{esc(arg)}</code>\n\n" + by_line(),
            parse_mode="html", link_preview=False,
        )
        return
    cur = settings.get(_LINK_KEY) or "<i>не задана</i>"
    await event.edit(
        "🔗 <b>Ссылка для прокси</b>\n"
        f"<b>Текущая:</b> <code>{esc(str(cur))}</code>\n\n"
        "<i>Получить можно на</i> https://advanced.name/ru/freeproxy\n"
        "<i>Использование:</i> <code>.proxylink &lt;url&gt;</code>\n\n" + by_line(),
        parse_mode="html", link_preview=False,
    )


@client.on(events.NewMessage(pattern=r"^\.proxycheck(?:\s+(on|off))?$", outgoing=True))
async def cmd_proxy_check_toggle(event):
    arg = (event.pattern_match.group(1) or "").lower()
    if arg in ("on", "off"):
        settings.set_val(_CHECK_KEY, arg == "on")
    cur = "вкл" if settings.get(_CHECK_KEY, True) else "выкл"
    await event.edit(
        f"🛡 <b>Проверка прокси на работоспособность:</b> <code>{cur}</code>\n"
        f"<i>Использование:</i> <code>.proxycheck on|off</code>\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.gproxy(?:\s+(\S+))?$", outgoing=True))
async def cmd_gproxy(event):
    proto = (event.pattern_match.group(1) or "").strip().lower()
    if not proto:
        await event.edit(
            "🚫 <b>Использование:</b> <code>.gproxy [протокол]</code>\n"
            "<i>напр.</i> <code>.gproxy http</code>, <code>socks4</code>, <code>socks5</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    link = settings.get(_LINK_KEY)
    if not link:
        await event.edit(
            "🚫 <b>Нет ссылки на прокси.</b>\n"
            "<i>Установить:</i> <code>.proxylink &lt;url&gt;</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    await event.edit("🔄 <b>Ищу прокси...</b>", parse_mode="html")

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(link, timeout=15) as r:
                base = await r.text()
            async with s.get(link, params={"type": proto}, timeout=15) as r:
                filtered = await r.text()
    except Exception as e:
        await event.edit(
            f"🚫 <b>Ошибка запроса:</b> <code>{esc(str(e))}</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    if not filtered.strip():
        await event.edit(
            "😕 <b>Истёк срок работы ссылки.</b> Обнови через <code>.proxylink</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return
    if base == filtered:
        await event.edit(
            "😕 <b>Неверный протокол или его нет в базе.</b>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    proxies = [p.strip() for p in filtered.splitlines() if ":" in p]
    if not proxies:
        await event.edit("😕 <b>Список прокси пуст.</b>\n\n" + by_line(), parse_mode="html")
        return

    do_check = settings.get(_CHECK_KEY, True)
    chosen = None
    tries = 0
    pool = proxies[:]
    random.shuffle(pool)
    for cand in pool:
        tries += 1
        ip, _, port = cand.partition(":")
        port = port.split()[0] if port else ""
        if not ip or not port:
            continue
        if not do_check:
            chosen = (ip, port)
            break
        if await _check(proto, ip, port):
            chosen = (ip, port)
            break
        if tries >= 25:
            break

    if not chosen:
        await event.edit(
            "🚫 <b>Не удалось найти рабочий прокси.</b>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    ip, port = chosen
    extra = "💎 <i>Проверено на работоспособность.</i>" if do_check else "<i>Без проверки.</i>"
    await event.edit(
        "🌐 <b>Рандомное прокси</b>\n\n"
        f"💾 <b>Протокол:</b> <code>{esc(proto)}</code>\n"
        f"🖥 <b>IP:</b> <code>{esc(ip)}</code>\n"
        f"📟 <b>Порт:</b> <code>{esc(port)}</code>\n\n"
        f"{extra}\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.wproxy(?:\s+(\S+)\s+(\S+))?$", outgoing=True))
async def cmd_wproxy(event):
    proto = event.pattern_match.group(1)
    addr  = event.pattern_match.group(2)
    if not proto or not addr or ":" not in addr:
        await event.edit(
            "🚫 <b>Использование:</b> <code>.wproxy [протокол] [ip:port]</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return
    ip, _, port = addr.partition(":")
    await event.edit("🔄 <b>Проверяю прокси...</b>", parse_mode="html")
    ok = await _check(proto.lower(), ip, port)
    await event.edit(
        ("✅ <b>Прокси работает!</b>" if ok else "❌ <b>Прокси не работает.</b>")
        + "\n\n" + by_line(),
        parse_mode="html",
    )
