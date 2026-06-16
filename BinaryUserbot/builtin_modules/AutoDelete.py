# MODULE_NAME = "AutoDelete"
# MODULE_CMD  = ".autodel"
# MODULE_DESC = "Автоудаление своих сообщений в указанных чатах через N минут"

import asyncio
import logging
from telethon import events
from bot_client import client
from premium_emoji import by_line
import settings

logger = logging.getLogger("AutoDelete")

# ───────── ключи в settings ─────────
K_ENABLED  = "autodel_enabled"
K_CHATS    = "autodel_chats"     # list[int]
K_INTERVAL = "autodel_interval"  # минуты

_task: asyncio.Task | None = None


# ───────── helpers ─────────

def _enabled() -> bool:
    return bool(settings.get(K_ENABLED, False))

def _chats() -> list[int]:
    raw = settings.get(K_CHATS) or []
    out = []
    for x in raw:
        try:
            out.append(int(x))
        except Exception:
            pass
    return out

def _interval() -> int:
    try:
        return max(1, int(settings.get(K_INTERVAL, 15)))
    except Exception:
        return 15


def _parse_chat(arg: str) -> int | None:
    arg = arg.strip().lstrip("@")
    if not arg:
        return None
    try:
        return int(arg)
    except ValueError:
        return None


# ───────── фоновый воркер ─────────

async def _worker():
    logger.info("AutoDelete worker started")
    while _enabled():
        chats = _chats()
        interval_min = _interval()
        for chat_id in chats:
            try:
                async for msg in client.iter_messages(chat_id, from_user="me"):
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                    await asyncio.sleep(0.05)
            except Exception as e:
                logger.warning("AutoDelete: chat %s error: %s", chat_id, e)
        await asyncio.sleep(interval_min * 60)
    logger.info("AutoDelete worker stopped")


def _ensure_worker():
    global _task
    if _enabled() and (_task is None or _task.done()):
        _task = asyncio.create_task(_worker())


# запустить, если уже было включено до перезапуска
try:
    _ensure_worker()
except RuntimeError:
    pass


# ───────── команды ─────────

HELP = (
    "🗑 <b>AutoDelete</b> — автоудаление твоих сообщений в указанных чатах.\n\n"
    "<code>.autodel on</code> / <code>.autodel off</code> — вкл/выкл\n"
    "<code>.autodel status</code> — статус\n"
    "<code>.autodel add &lt;id|@user&gt;</code> — добавить чат (или ответом)\n"
    "<code>.autodel del &lt;id&gt;</code> — убрать чат\n"
    "<code>.autodel here</code> — добавить текущий чат\n"
    "<code>.autodel list</code> — список чатов\n"
    "<code>.autodel time &lt;минут&gt;</code> — интервал (по умолчанию 15)\n"
)


@client.on(events.NewMessage(pattern=r"^\.autodel(?:\s+(.+))?$", outgoing=True))
async def autodel_cmd(event):
    raw = (event.pattern_match.group(1) or "").strip()
    parts = raw.split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    arg = parts[1] if len(parts) > 1 else ""

    if not sub:
        s = "✅" if _enabled() else "⛔️"
        chats = _chats()
        await event.edit(
            HELP +
            f"\n<b>Статус:</b> {s} • <b>Интервал:</b> {_interval()} мин • "
            f"<b>Чатов:</b> {len(chats)}\n\n" + by_line(),
            parse_mode="html",
        )
        return

    if sub == "on":
        settings.set_val(K_ENABLED, True)
        _ensure_worker()
        await event.edit(
            f"✅ <b>AutoDelete включён.</b> Интервал {_interval()} мин, чатов: {len(_chats())}.\n\n" + by_line(),
            parse_mode="html",
        )
        return

    if sub == "off":
        settings.set_val(K_ENABLED, False)
        await event.edit("⛔️ <b>AutoDelete выключен.</b>\n\n" + by_line(), parse_mode="html")
        return

    if sub == "status":
        s = "Активен" if _enabled() else "Выключен"
        await event.edit(
            f"ℹ️ <b>AutoDelete:</b> {s}\n"
            f"⏱ Интервал: <b>{_interval()}</b> мин\n"
            f"💬 Чатов: <b>{len(_chats())}</b>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    if sub == "here":
        chats = _chats()
        if event.chat_id in chats:
            await event.edit("ℹ️ <b>Этот чат уже в списке.</b>\n\n" + by_line(), parse_mode="html")
            return
        chats.append(event.chat_id)
        settings.set_val(K_CHATS, chats)
        await event.edit(f"➕ <b>Добавлен текущий чат</b> <code>{event.chat_id}</code>.\n\n" + by_line(), parse_mode="html")
        return

    if sub == "add":
        target = None
        if event.is_reply and not arg:
            r = await event.get_reply_message()
            target = r.chat_id
        else:
            target = _parse_chat(arg)
            if target is None and arg:
                # попытка резолвить @username
                try:
                    ent = await client.get_entity(arg)
                    target = ent.id
                except Exception as e:
                    await event.edit(f"⚠️ <b>Не удалось найти:</b> {e}\n\n" + by_line(), parse_mode="html")
                    return
        if target is None:
            await event.edit("⚠️ <b>Укажи id чата или @username.</b>\n\n" + by_line(), parse_mode="html")
            return
        chats = _chats()
        if target in chats:
            await event.edit(f"ℹ️ <b>{target}</b> уже в списке.\n\n" + by_line(), parse_mode="html")
            return
        chats.append(target)
        settings.set_val(K_CHATS, chats)
        await event.edit(f"➕ <b>Добавлен:</b> <code>{target}</code>.\n\n" + by_line(), parse_mode="html")
        return

    if sub == "del":
        target = _parse_chat(arg)
        if target is None:
            await event.edit("⚠️ <b>Укажи id.</b>\n\n" + by_line(), parse_mode="html")
            return
        chats = _chats()
        if target not in chats:
            await event.edit(f"ℹ️ <b>{target}</b> не в списке.\n\n" + by_line(), parse_mode="html")
            return
        chats.remove(target)
        settings.set_val(K_CHATS, chats)
        await event.edit(f"➖ <b>Удалён:</b> <code>{target}</code>.\n\n" + by_line(), parse_mode="html")
        return

    if sub == "list":
        chats = _chats()
        if not chats:
            await event.edit("📭 <b>Список чатов пуст.</b>\n\n" + by_line(), parse_mode="html")
            return
        body = "\n".join(f"• <code>{c}</code>" for c in chats)
        await event.edit(f"💬 <b>Чаты ({len(chats)}):</b>\n{body}\n\n" + by_line(), parse_mode="html")
        return

    if sub == "time":
        try:
            n = int(arg)
            if n < 1:
                raise ValueError
        except Exception:
            await event.edit("⚠️ <b>Нужно целое число ≥ 1.</b>\n\n" + by_line(), parse_mode="html")
            return
        settings.set_val(K_INTERVAL, n)
        await event.edit(f"⏱ <b>Интервал:</b> {n} мин.\n\n" + by_line(), parse_mode="html")
        return

    await event.edit(HELP + "\n" + by_line(), parse_mode="html")
