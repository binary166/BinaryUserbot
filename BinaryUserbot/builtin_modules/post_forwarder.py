# MODULE_NAME = "Post Forwarder"
# MODULE_CMD  = ".pf"
# MODULE_DESC = "Периодическая пересылка выбранного поста в список чатов"

import asyncio
import re
import time

from telethon import events
from telethon.errors.rpcerrorlist import ChatForwardsRestrictedError
from telethon.errors import FloodWaitError
from telethon.utils import get_peer_id

import settings
from bot_client import client
from config import MY_ID
from premium_emoji import by_line, pe
from utils import html, send_me


K_ENABLED = "postfw_enabled"
K_INTERVAL = "postfw_interval"
K_SOURCE = "postfw_source"
K_TARGETS = "postfw_targets"
K_LAST_RUN = "postfw_last_run"
K_LAST_REPORT = "postfw_last_report"

_task = None
_lock = asyncio.Lock()


def _enabled():
    return bool(settings.get(K_ENABLED, False))


def _interval():
    try:
        return max(1, int(settings.get(K_INTERVAL, 60)))
    except Exception:
        return 60


def _source():
    return settings.get(K_SOURCE) or {}


def _targets():
    raw = settings.get(K_TARGETS) or []
    if not isinstance(raw, list):
        return []
    return [x for x in raw if isinstance(x, dict) and x.get("input")]


def _save_targets(targets):
    settings.set_val(K_TARGETS, targets)


def _fmt_ts(ts):
    if not ts:
        return "никогда"
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(int(ts)))


def _menu():
    source = _source()
    targets = _targets()
    status = "запущена" if _enabled() else "остановлена"
    post = source.get("link") or "не задан"
    return (
        f"{pe('gear')} <b>Рассылка поста</b>\n\n"
        f"<blockquote>"
        f"Статус: <b>{status}</b>\n"
        f"Таймер: <b>{_interval()}</b> мин\n"
        f"Пост: <code>{html(str(post))}</code>\n"
        f"Чатов: <b>{len(targets)}</b>\n"
        f"Последний запуск: <b>{_fmt_ts(settings.get(K_LAST_RUN, 0))}</b>"
        f"</blockquote>\n\n"
        f"<b>Управление:</b>\n"
        f"<code>.pf start</code> — запустить\n"
        f"<code>.pf stop</code> — остановить\n"
        f"<code>.pf timer 15</code> — изменить таймер\n"
        f"<code>.pf post ссылка</code> — установить пост\n"
        f"<code>.pf add @chat</code> — добавить чат\n"
        f"<code>.pf del 1</code> — удалить чат по номеру\n"
        f"<code>.pf list</code> — список чатов\n"
        f"<code>.pf send</code> — отправить один раз\n\n"
        + by_line()
    )


def _parse_post_link(link):
    text = (link or "").strip()
    text = text.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    m = re.match(r"^(?:https?://)?t\.me/(.+)$", text, re.I)
    if not m:
        return None
    parts = [p for p in m.group(1).split("/") if p]
    if len(parts) < 2:
        return None
    try:
        message_id = int(parts[-1])
    except ValueError:
        return None
    if parts[0] == "c" and len(parts) >= 3:
        return {"chat": int(f"-100{parts[1]}"), "message_id": message_id, "link": link}
    if parts[0] == "s" and len(parts) >= 3:
        return {"chat": parts[1], "message_id": message_id, "link": link}
    if parts[0].startswith("+"):
        return None
    return {"chat": parts[0].lstrip("@"), "message_id": message_id, "link": link}


async def _entity_info(raw):
    value = str(raw).strip()
    lookup = int(value) if value.lstrip("-").isdigit() else value
    ent = await client.get_entity(lookup)
    username = getattr(ent, "username", None)
    title = getattr(ent, "title", None) or " ".join(x for x in [getattr(ent, "first_name", ""), getattr(ent, "last_name", "")] if x) or username or str(raw)
    peer_id = get_peer_id(ent)
    return {
        "input": value,
        "peer_id": peer_id,
        "title": title,
        "username": f"@{username}" if username else "",
    }


async def _resolve_target(target):
    value = str(target.get("input") or target.get("peer_id") or "").strip()
    if value.lstrip("-").isdigit():
        value = int(value)
    return await client.get_entity(value)


async def _source_message(source):
    msg = await client.get_messages(source["chat"], ids=int(source["message_id"]))
    if not msg:
        raise ValueError("post not found")
    return msg


async def _forward_post(source, target_entity):
    msg = await _source_message(source)
    try:
        await msg.forward_to(target_entity)
    except ChatForwardsRestrictedError:
        raise
    except Exception:
        await client.forward_messages(target_entity, msg)


async def _send_once():
    async with _lock:
        source = _source()
        targets = _targets()
        if not source.get("chat") or not source.get("message_id"):
            return 0, [("source", "пост не установлен")]
        if not targets:
            return 0, [("targets", "список чатов пуст")]
        sent = 0
        errors = []
        for target in targets:
            label = target.get("username") or target.get("title") or target.get("input")
            try:
                entity = await _resolve_target(target)
                await _forward_post(source, entity)
                sent += 1
                await asyncio.sleep(1.2)
            except FloodWaitError as e:
                await asyncio.sleep(e.seconds + 2)
                try:
                    entity = await _resolve_target(target)
                    await _forward_post(source, entity)
                    sent += 1
                except ChatForwardsRestrictedError:
                    errors.append((label, "в источнике запрещена пересылка постов"))
                except Exception as inner:
                    errors.append((label, str(inner)[:180]))
            except ChatForwardsRestrictedError:
                errors.append((label, "в источнике запрещена пересылка постов"))
            except Exception as e:
                errors.append((label, str(e)[:180]))
        report = {"sent": sent, "errors": errors, "ts": int(time.time())}
        settings.set_val(K_LAST_RUN, report["ts"])
        settings.set_val(K_LAST_REPORT, report)
        return sent, errors


async def _worker():
    while _enabled():
        sent, errors = await _send_once()
        try:
            err_line = ""
            if errors:
                err_line = "\n" + "\n".join(f"• <code>{html(str(x[0]))}</code>: {html(str(x[1]))}" for x in errors[:5])
            await send_me(
                f"{pe('chain')} <b>Рассылка выполнена</b>\n\n"
                f"Отправлено: <b>{sent}</b>\n"
                f"Ошибок: <b>{len(errors)}</b>{err_line}"
            )
        except Exception:
            pass
        await asyncio.sleep(_interval() * 60)


def _ensure_worker():
    global _task
    if _enabled() and (_task is None or _task.done()):
        _task = asyncio.create_task(_worker())


async def _show_list(event):
    targets = _targets()
    if not targets:
        await event.edit(
            f"{pe('doc')} <b>Список чатов пуст.</b>\n\n"
            f"<code>.pf add @chat</code> или <code>.pf add -1001234567890</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return
    lines = []
    refreshed = []
    for i, target in enumerate(targets, 1):
        current = dict(target)
        try:
            current.update(await _entity_info(target.get("input")))
        except Exception:
            pass
        refreshed.append(current)
        username = current.get("username") or "—"
        title = html(current.get("title") or current.get("input"))
        peer_id = html(str(current.get("peer_id") or current.get("input")))
        lines.append(f"<b>{i}.</b> {title}\n   {html(username)} · <code>{peer_id}</code>")
    _save_targets(refreshed)
    await event.edit(
        f"{pe('users')} <b>Чаты рассылки ({len(refreshed)})</b>\n\n"
        + "\n".join(lines)
        + "\n\n<code>.pf del номер</code> — удалить чат\n"
        + "<code>.pf add @chat</code> — добавить чат\n\n"
        + by_line(),
        parse_mode="html",
    )


async def postfw_cmd(event):
    if not event.out:
        return
    if event.sender_id and event.sender_id != MY_ID:
        return
    raw = (event.pattern_match.group(1) or "").strip()
    parts = raw.split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    arg = parts[1].strip() if len(parts) > 1 else ""

    if not sub:
        await event.edit(_menu(), parse_mode="html", link_preview=False)
        return

    if sub in {"start", "on", "run"}:
        if not _source().get("chat"):
            await event.edit(f"{pe('lock')} <b>Сначала установи пост:</b>\n<code>.pf post ссылка</code>", parse_mode="html")
            return
        if not _targets():
            await event.edit(f"{pe('lock')} <b>Сначала добавь хотя бы один чат:</b>\n<code>.pf add @chat</code>", parse_mode="html")
            return
        settings.set_val(K_ENABLED, True)
        _ensure_worker()
        await event.edit(f"{pe('bolt')} <b>Рассылка запущена.</b>\n\n{_menu()}", parse_mode="html", link_preview=False)
        return

    if sub in {"stop", "off"}:
        settings.set_val(K_ENABLED, False)
        await event.edit(f"{pe('lock')} <b>Рассылка остановлена.</b>\n\n{_menu()}", parse_mode="html", link_preview=False)
        return

    if sub in {"timer", "time"}:
        if not arg:
            await event.edit(f"{pe('gear')} <b>Текущий таймер:</b> {_interval()} мин\n\n<code>.pf timer 15</code>", parse_mode="html")
            return
        try:
            minutes = int(arg)
            if minutes < 1:
                raise ValueError
        except Exception:
            await event.edit(f"{pe('lock')} <b>Нужно целое число минут от 1.</b>", parse_mode="html")
            return
        settings.set_val(K_INTERVAL, minutes)
        await event.edit(f"{pe('gear')} <b>Таймер изменён:</b> {minutes} мин.\n\n{_menu()}", parse_mode="html", link_preview=False)
        return

    if sub == "post":
        if not arg and event.is_reply:
            reply = await event.get_reply_message()
            data = {"chat": reply.chat_id, "message_id": reply.id, "link": f"reply:{reply.chat_id}/{reply.id}"}
        else:
            data = _parse_post_link(arg)
        if not data:
            await event.edit(
                f"{pe('lock')} <b>Нужна ссылка на пост.</b>\n\n"
                f"Пример: <code>.pf post https://t.me/channel/123</code>",
                parse_mode="html",
            )
            return
        try:
            msg = await client.get_messages(data["chat"], ids=int(data["message_id"]))
            if not msg:
                raise ValueError("post not found")
        except Exception as e:
            await event.edit(f"{pe('lock')} <b>Не смог открыть пост:</b>\n<code>{html(str(e)[:200])}</code>", parse_mode="html")
            return
        settings.set_val(K_SOURCE, data)
        await event.edit(
            f"{pe('check')} <b>Пост установлен.</b>\n\n"
            f"Источник: <code>{html(str(data['chat']))}</code>\n"
            f"Message ID: <code>{data['message_id']}</code>\n\n{_menu()}",
            parse_mode="html",
            link_preview=False,
        )
        return

    if sub == "add":
        if not arg:
            await event.edit(f"{pe('lock')} <b>Укажи ID или @username чата.</b>\n\n<code>.pf add @chat</code>", parse_mode="html")
            return
        try:
            info = await _entity_info(arg)
        except Exception as e:
            await event.edit(f"{pe('lock')} <b>Не смог найти чат:</b>\n<code>{html(str(e)[:200])}</code>", parse_mode="html")
            return
        targets = _targets()
        if any(str(x.get("peer_id")) == str(info["peer_id"]) or str(x.get("input")) == str(info["input"]) for x in targets):
            await event.edit(f"{pe('doc')} <b>Этот чат уже в списке.</b>\n\n<code>{html(str(info['peer_id']))}</code>", parse_mode="html")
            return
        targets.append(info)
        _save_targets(targets)
        await event.edit(
            f"{pe('check')} <b>Чат добавлен.</b>\n\n"
            f"{html(info['title'])}\n{html(info.get('username') or '—')} · <code>{info['peer_id']}</code>\n\n"
            f"Всего чатов: <b>{len(targets)}</b>",
            parse_mode="html",
        )
        return

    if sub in {"del", "delete", "remove"}:
        targets = _targets()
        if not targets:
            await event.edit(f"{pe('doc')} <b>Список чатов пуст.</b>", parse_mode="html")
            return
        if not arg:
            await _show_list(event)
            return
        idx = None
        if arg.isdigit():
            idx = int(arg) - 1
        else:
            for i, target in enumerate(targets):
                if arg.lower() in {str(target.get("input", "")).lower(), str(target.get("peer_id", "")).lower(), str(target.get("username", "")).lower()}:
                    idx = i
                    break
        if idx is None or idx < 0 or idx >= len(targets):
            await event.edit(f"{pe('lock')} <b>Не нашёл чат в списке.</b>\n\n<code>.pf list</code>", parse_mode="html")
            return
        removed = targets.pop(idx)
        _save_targets(targets)
        await event.edit(
            f"{pe('check')} <b>Чат удалён.</b>\n\n"
            f"{html(removed.get('title') or removed.get('input'))}\n"
            f"<code>{html(str(removed.get('peer_id') or removed.get('input')))}</code>\n\n"
            f"Осталось: <b>{len(targets)}</b>",
            parse_mode="html",
        )
        return

    if sub == "list":
        await _show_list(event)
        return

    if sub in {"send", "test"}:
        await event.edit(f"{pe('bolt')} <b>Отправляю один раз...</b>", parse_mode="html")
        sent, errors = await _send_once()
        err_line = ""
        if errors:
            err_line = "\n\n<b>Ошибки:</b>\n" + "\n".join(f"• <code>{html(str(x[0]))}</code>: {html(str(x[1]))}" for x in errors[:10])
        await event.edit(
            f"{pe('chain')} <b>Готово.</b>\n\n"
            f"Отправлено: <b>{sent}</b>\n"
            f"Ошибок: <b>{len(errors)}</b>{err_line}\n\n" + by_line(),
            parse_mode="html",
        )
        return

    if sub == "status":
        report = settings.get(K_LAST_REPORT, {}) or {}
        errors = report.get("errors") or []
        err_line = ""
        if errors:
            err_line = "\n" + "\n".join(f"• <code>{html(str(x[0]))}</code>: {html(str(x[1]))}" for x in errors[:5])
        await event.edit(
            _menu()
            + f"\n<b>Последний отчёт:</b>\n"
            f"Отправлено: <b>{report.get('sent', 0)}</b>\n"
            f"Ошибок: <b>{len(errors)}</b>{err_line}",
            parse_mode="html",
            link_preview=False,
        )
        return

    await event.edit(_menu(), parse_mode="html", link_preview=False)


_handler = postfw_cmd
client.add_event_handler(_handler, events.NewMessage(pattern=r"^(?:\.pf|\.рассылка)(?:\s+(.+))?$", outgoing=True))
_binary_handlers = [_handler]

try:
    _ensure_worker()
except RuntimeError:
    pass
