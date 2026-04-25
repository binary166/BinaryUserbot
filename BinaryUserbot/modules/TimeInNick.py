# MODULE_NAME = "TimeInNick"
# MODULE_CMD  = ".timenick"
# MODULE_DESC = "Показывает текущее время в имени и/или био. Стили шрифта, часовой пояс."

import asyncio
import datetime
import logging

from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.users import GetFullUserRequest

from bot_client import client
from premium_emoji import by_line
import settings

logger = logging.getLogger(__name__)


TIMEZONE_OFFSETS = {
    "MSK": 3, "UTC": 0, "GMT": 0, "CET": 1, "EET": 2,
    "AZT": 4, "AMT": 4, "GET": 4, "TJT": 5, "TMT": 5, "UZT": 5,
    "KGT": 6, "BDT": 6, "IST": 5.5, "THA": 7, "ICT": 7,
    "CST": 8, "HKT": 8, "JST": 9, "KST": 9,
    "EST": -5, "EDT": -4, "CDT": -5, "MDT": -6, "PDT": -7, "PST": -8, "AKST": -9,
    "AEST": 10, "NZST": 12,
}

FONT_STYLES = {
    1: lambda x: x,
    2: lambda x: f"『{x}』",
    3: lambda x: x.translate(str.maketrans("0123456789", "⓿➊➋➌➍➎➏➐➑➒")),
    4: lambda x: x.translate(str.maketrans("0123456789", "⓪⓵⓶⓷⓸⓹⓺⓻⓼⓽")),
    5: lambda x: x.translate(str.maketrans("0123456789", "⓪①②③④⑤⑥⑦⑧⑨")),
    6: lambda x: x.translate(str.maketrans("0123456789", "𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡")),
    7: lambda x: x.translate(str.maketrans("0123456789:", "⁰¹²³⁴⁵⁶⁷⁸⁹'")),
    8: lambda x: x.translate(str.maketrans("0123456789:", "₀₁₂₃₄₅₆₇₈₉‚")),
    9: lambda x: "".join(i + "️⃣" if i.isdigit() else i for i in x),
}

FONT_DESC = (
    "1. 12:34 → 12:34\n"
    "2. 12:34 → 『12:34』\n"
    "3. 12:34 → ➊➋:➌➍\n"
    "4. 12:34 → ⓵⓶:⓷⓸\n"
    "5. 12:34 → ①②:③④\n"
    "6. 12:34 → 𝟙𝟚:𝟛𝟜\n"
    "7. 12:34 → ¹²'³⁴\n"
    "8. 12:34 → ₁₂‚₃₄\n"
    "9. 12:34 → 1️⃣2️⃣:3️⃣4️⃣"
)

DEFAULTS = {
    "tin_timezone":    "MSK",
    "tin_update_min":  0,        # 0 = каждую минуту
    "tin_nick_format": "{nickname} | {time}",
    "tin_bio_format":  "{bio} | {time}",
    "tin_font":        1,
    "tin_nick_active": False,
    "tin_bio_active":  False,
    "tin_orig_nick":   None,
    "tin_orig_bio":    None,
}
for k, v in DEFAULTS.items():
    if settings.get(k) is None:
        settings.set_val(k, v)


_state = {"nick_task": None, "bio_task": None, "last_nick_time": None, "last_bio_time": None}


def _format_time() -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    tz = settings.get("tin_timezone", "MSK").upper()
    offset = TIMEZONE_OFFSETS.get(tz, 0)
    h = int(offset)
    m = int(round((offset - h) * 60))
    adjusted = now + datetime.timedelta(hours=h, minutes=m)
    s = adjusted.strftime("%H:%M")
    font = settings.get("tin_font", 1)
    if font not in FONT_STYLES:
        font = 1
    return FONT_STYLES[font](s)


def _delay_seconds() -> int:
    d = settings.get("tin_update_min", 0)
    try:
        d = int(d)
    except Exception:
        d = 0
    return d * 60 if d > 0 else 60


async def _update_nick_loop():
    retries = 0
    while settings.get("tin_nick_active", False) and retries < 10:
        try:
            t = _format_time()
            if t != _state["last_nick_time"]:
                orig = settings.get("tin_orig_nick") or ""
                fmt = settings.get("tin_nick_format", "{nickname} | {time}")
                new_nick = fmt.format(nickname=orig, time=t)
                await client(UpdateProfileRequest(first_name=new_nick[:70]))
                _state["last_nick_time"] = t
                retries = 0
        except asyncio.CancelledError:
            raise
        except Exception as e:
            retries += 1
            logger.exception(f"[TimeInNick] nick error #{retries}: {e}")
            await asyncio.sleep(min(5 * retries, 30))
            continue
        await asyncio.sleep(_delay_seconds())


async def _update_bio_loop():
    retries = 0
    while settings.get("tin_bio_active", False) and retries < 10:
        try:
            t = _format_time()
            if t != _state["last_bio_time"]:
                orig = settings.get("tin_orig_bio") or ""
                fmt = settings.get("tin_bio_format", "{bio} | {time}")
                new_bio = fmt.format(bio=orig, time=t)
                await client(UpdateProfileRequest(about=new_bio[:70]))
                _state["last_bio_time"] = t
                retries = 0
        except asyncio.CancelledError:
            raise
        except Exception as e:
            retries += 1
            logger.exception(f"[TimeInNick] bio error #{retries}: {e}")
            await asyncio.sleep(min(5 * retries, 30))
            continue
        await asyncio.sleep(_delay_seconds())


def _start_nick_task():
    if _state["nick_task"] and not _state["nick_task"].done():
        return
    _state["nick_task"] = asyncio.create_task(_update_nick_loop())


def _start_bio_task():
    if _state["bio_task"] and not _state["bio_task"].done():
        return
    _state["bio_task"] = asyncio.create_task(_update_bio_loop())


def _stop_nick_task():
    t = _state.get("nick_task")
    if t and not t.done():
        t.cancel()
    _state["nick_task"] = None


def _stop_bio_task():
    t = _state.get("bio_task")
    if t and not t.done():
        t.cancel()
    _state["bio_task"] = None


async def _restore_nick():
    orig = settings.get("tin_orig_nick")
    if orig is not None:
        try:
            await client(UpdateProfileRequest(first_name=orig[:70]))
        except Exception:
            pass


async def _restore_bio():
    orig = settings.get("tin_orig_bio")
    if orig is not None:
        try:
            await client(UpdateProfileRequest(about=orig[:70]))
        except Exception:
            pass


@client.on(events.NewMessage(pattern=r"^\.timenick$", outgoing=True))
async def cmd_timenick(event):
    if settings.get("tin_nick_active", False):
        settings.set_val("tin_nick_active", False)
        _stop_nick_task()
        await _restore_nick()
        await event.edit(
            "⏰ <b>Время в имени выключено.</b>\n\n" + by_line(),
            parse_mode="html",
        )
        return
    try:
        me = await client.get_me()
        cur = me.first_name or ""
        orig = cur.split("|")[0].strip() if "|" in cur else cur
        if not orig:
            orig = "User"
        settings.set_val("tin_orig_nick", orig)
        settings.set_val("tin_nick_active", True)
        _state["last_nick_time"] = None
        _start_nick_task()
        await event.edit(
            "⏰ <b>Время в имени включено.</b>\n\n" + by_line(),
            parse_mode="html",
        )
    except Exception as e:
        settings.set_val("tin_nick_active", False)
        await event.edit(f"⚠️ <b>Ошибка:</b> <code>{e}</code>", parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.timebio$", outgoing=True))
async def cmd_timebio(event):
    if settings.get("tin_bio_active", False):
        settings.set_val("tin_bio_active", False)
        _stop_bio_task()
        await _restore_bio()
        await event.edit(
            "⏰ <b>Время в био выключено.</b>\n\n" + by_line(),
            parse_mode="html",
        )
        return
    try:
        full = await client(GetFullUserRequest("me"))
        cur = full.full_user.about or ""
        orig = cur.split("|")[0].strip() if "|" in cur else cur
        settings.set_val("tin_orig_bio", orig)
        settings.set_val("tin_bio_active", True)
        _state["last_bio_time"] = None
        _start_bio_task()
        await event.edit(
            "⏰ <b>Время в био включено.</b>\n\n" + by_line(),
            parse_mode="html",
        )
    except Exception as e:
        settings.set_val("tin_bio_active", False)
        await event.edit(f"⚠️ <b>Ошибка:</b> <code>{e}</code>", parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.timenickset(?:\s|$)", outgoing=True))
async def cmd_timenickset(event):
    parts = event.raw_text.split(None, 2)
    if len(parts) < 3:
        tz = settings.get("tin_timezone", "MSK")
        upd = settings.get("tin_update_min", 0)
        font = settings.get("tin_font", 1)
        nf = settings.get("tin_nick_format", "")
        bf = settings.get("tin_bio_format", "")
        tz_list = ", ".join(TIMEZONE_OFFSETS.keys())
        await event.edit(
            "⚙️ <b>Настройки TimeInNick</b>\n\n"
            f"<blockquote>"
            f"🌍 <b>tz</b>: <code>{tz}</code>\n"
            f"⏱ <b>update</b>: <code>{upd}</code> мин (0 = каждую минуту)\n"
            f"🔤 <b>font</b>: <code>{font}</code>\n"
            f"📝 <b>nick</b>: <code>{nf}</code>\n"
            f"📝 <b>bio</b>: <code>{bf}</code>"
            f"</blockquote>\n\n"
            f"<b>Использование:</b>\n"
            f"<code>.timenickset tz MSK</code>\n"
            f"<code>.timenickset update 5</code>\n"
            f"<code>.timenickset font 1..9</code>\n"
            f"<code>.timenickset nick {{nickname}} | {{time}}</code>\n"
            f"<code>.timenickset bio {{bio}} | {{time}}</code>\n\n"
            f"<b>Шрифты:</b>\n<blockquote expandable>{FONT_DESC}</blockquote>\n"
            f"<b>Часовые пояса:</b>\n<blockquote expandable>{tz_list}</blockquote>\n\n"
            + by_line(),
            parse_mode="html",
            link_preview=False,
        )
        return

    key, value = parts[1].lower(), parts[2]
    if key == "tz":
        v = value.upper()
        if v not in TIMEZONE_OFFSETS:
            await event.edit(
                f"⚠️ <b>Неизвестный пояс.</b> Доступные: <code>{', '.join(TIMEZONE_OFFSETS.keys())}</code>",
                parse_mode="html",
            )
            return
        settings.set_val("tin_timezone", v)
        await event.edit(f"✅ <b>tz</b> = <code>{v}</code>", parse_mode="html")
    elif key == "update":
        try:
            n = int(value)
            assert 0 <= n <= 60
        except Exception:
            await event.edit("⚠️ <b>update</b> должно быть числом 0..60", parse_mode="html")
            return
        settings.set_val("tin_update_min", n)
        await event.edit(f"✅ <b>update</b> = <code>{n}</code> мин", parse_mode="html")
    elif key == "font":
        try:
            n = int(value)
            assert n in FONT_STYLES
        except Exception:
            await event.edit("⚠️ <b>font</b> должен быть 1..9", parse_mode="html")
            return
        settings.set_val("tin_font", n)
        await event.edit(f"✅ <b>font</b> = <code>{n}</code>", parse_mode="html")
    elif key == "nick":
        if "{time}" not in value:
            await event.edit("⚠️ Формат должен содержать <code>{time}</code>", parse_mode="html")
            return
        settings.set_val("tin_nick_format", value)
        await event.edit(f"✅ <b>nick</b> = <code>{value}</code>", parse_mode="html")
    elif key == "bio":
        if "{time}" not in value:
            await event.edit("⚠️ Формат должен содержать <code>{time}</code>", parse_mode="html")
            return
        settings.set_val("tin_bio_format", value)
        await event.edit(f"✅ <b>bio</b> = <code>{value}</code>", parse_mode="html")
    else:
        await event.edit(
            "⚠️ Неизвестный ключ. Используй: <code>tz | update | font | nick | bio</code>",
            parse_mode="html",
        )


# Авто-восстановление задач при загрузке модуля
if settings.get("tin_nick_active", False):
    _start_nick_task()
if settings.get("tin_bio_active", False):
    _start_bio_task()
