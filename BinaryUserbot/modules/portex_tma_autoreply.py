# MODULE_NAME = "Portex TMA AutoReply"
# MODULE_CMD  = ".portextma"
# MODULE_DESC = "Automatically sends a fresh Portex TMA token to the configured bot when it asks for one."

import asyncio
import hashlib
import json
import time
import urllib.parse
import urllib.request
import uuid

from telethon import events, functions, types

from bot_client import client
import settings
from utils import html


K_ENABLED = "portex_tma_autoreply_enabled"
K_REQUEST_BOT = "portex_tma_request_bot"
K_PORTEX_BOT = "portex_tma_portex_bot"
K_PLATFORM = "portex_tma_platform"
K_COOLDOWN = "portex_tma_cooldown_seconds"
K_VERIFY_URL = "portex_tma_verify_url"
K_LAST_HASH = "portex_tma_last_hash"
K_LAST_SENT_AT = "portex_tma_last_sent_at"

DEFAULT_REQUEST_BOT = "polymakerAI_bot"
DEFAULT_PORTEX_BOT = "portex"
DEFAULT_PLATFORM = "android"
DEFAULT_COOLDOWN_SECONDS = 45
DEFAULT_VERIFY_URL = "https://api.polystation.tech/api/sports/fifa-world-cup"

REQUEST_PHRASES = (
    "введите новый",
    "отправьте свеж",
    "жду tma",
    "жду tma token",
    "жду токен",
    "обновите token",
    "обновите токен",
    "больше не действует",
    "не действует",
    "истек",
    "expired",
    "unauthorized",
    "missing portex",
    "401",
    "/portex_token",
)

_refresh_lock = asyncio.Lock()


def _enabled() -> bool:
    return bool(settings.get(K_ENABLED, True))


def _request_bot() -> str:
    return str(settings.get(K_REQUEST_BOT, DEFAULT_REQUEST_BOT) or DEFAULT_REQUEST_BOT).strip()


def _portex_bot() -> str:
    return str(settings.get(K_PORTEX_BOT, DEFAULT_PORTEX_BOT) or DEFAULT_PORTEX_BOT).strip()


def _platform() -> str:
    value = str(settings.get(K_PLATFORM, DEFAULT_PLATFORM) or DEFAULT_PLATFORM).strip()
    return value or DEFAULT_PLATFORM


def _cooldown_seconds() -> int:
    try:
        return max(0, int(settings.get(K_COOLDOWN, DEFAULT_COOLDOWN_SECONDS)))
    except Exception:
        return DEFAULT_COOLDOWN_SECONDS


def _verify_url() -> str:
    return str(settings.get(K_VERIFY_URL, DEFAULT_VERIFY_URL) or DEFAULT_VERIFY_URL).strip()


def _normalize_ref(value: str) -> str:
    value = str(value or "").strip()
    if value.startswith("@"):
        value = value[1:]
    return value.lower()


def _sender_matches(sender, configured: str) -> bool:
    ref = _normalize_ref(configured)
    if not ref:
        return False
    sender_id = str(getattr(sender, "id", "") or "")
    if ref.isdigit() and sender_id == ref:
        return True
    username = _normalize_ref(getattr(sender, "username", "") or "")
    return bool(username and username == ref)


def _looks_like_request(text: str) -> bool:
    normalized = (text or "").lower()
    has_token_subject = (
        "tma" in normalized
        or "тма" in normalized
        or ("portex" in normalized and ("token" in normalized or "токен" in normalized))
    )
    if not has_token_subject:
        return False
    return any(marker in normalized for marker in REQUEST_PHRASES)


def _mask_ref(value) -> str:
    value = str(value or "")
    if len(value) <= 4:
        return "***" if value else ""
    return f"{value[:2]}***{value[-2:]}"


def _extract_tg_webapp_data(url: str) -> str:
    parsed = urllib.parse.urlparse(url or "")
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    fragment = urllib.parse.parse_qs(parsed.fragment, keep_blank_values=True)
    raw = (fragment.get("tgWebAppData") or query.get("tgWebAppData") or [""])[0]
    if not raw:
        raise RuntimeError("tgWebAppData was not found in Portex WebView URL")
    return urllib.parse.unquote(raw)


def _parse_token_owner(tma: str) -> tuple[str, str]:
    fields = urllib.parse.parse_qs(tma, keep_blank_values=True)
    auth_date = fields.get("auth_date", [""])[0]
    raw_user = fields.get("user", ["{}"])[0]
    try:
        user_id = str(json.loads(raw_user).get("id", "") or "")
    except Exception:
        user_id = ""
    return user_id, auth_date


def _verify_portex_token_sync(tma: str) -> tuple[int, int]:
    verify_url = _verify_url()
    if not verify_url:
        return 0, 0
    req = urllib.request.Request(
        verify_url,
        headers={
            "Authorization": "tma " + tma,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "x-request-id": str(uuid.uuid4()),
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        count = 0
        try:
            data = json.loads(body) if body else {}
            if isinstance(data, dict):
                events_data = (data.get("data") or {}).get("events") or []
                count = len(events_data)
        except Exception:
            count = 0
        return int(getattr(resp, "status", 200) or 200), count


async def _get_fresh_portex_tma() -> dict:
    bot_ref = _portex_bot()
    portex_entity = await client.get_input_entity(bot_ref)
    result = await client(
        functions.messages.RequestMainWebViewRequest(
            peer=portex_entity,
            bot=portex_entity,
            platform=_platform(),
            fullscreen=True,
            start_param="",
            theme_params=types.DataJSON(data="{}"),
        )
    )
    url = getattr(result, "url", "") or ""
    tma = _extract_tg_webapp_data(url)
    user_id, auth_date = _parse_token_owner(tma)
    status, events_count = await asyncio.to_thread(_verify_portex_token_sync, tma)
    token_hash = hashlib.sha256(tma.encode("utf-8")).hexdigest()
    return {
        "tma": tma,
        "hash": token_hash,
        "user_id": user_id,
        "auth_date": auth_date,
        "status": status,
        "events_count": events_count,
        "host": urllib.parse.urlparse(url).netloc,
    }


async def _refresh_and_send(chat_id, reply_to=None, *, force=False) -> dict:
    async with _refresh_lock:
        now = time.time()
        last_sent = float(settings.get(K_LAST_SENT_AT, 0) or 0)
        cooldown = _cooldown_seconds()
        if not force and cooldown and now - last_sent < cooldown:
            return {"skipped": True, "reason": "cooldown", "wait": int(cooldown - (now - last_sent))}

        data = await _get_fresh_portex_tma()
        await client.send_message(
            chat_id,
            "tma " + data["tma"],
            reply_to=reply_to,
            parse_mode=None,
            link_preview=False,
        )
        settings.set_val(K_LAST_HASH, data["hash"][:12])
        settings.set_val(K_LAST_SENT_AT, int(now))
        return data


async def _status_text() -> str:
    return (
        "<b>Portex TMA AutoReply</b>\n\n"
        f"Enabled: <code>{html(str(_enabled()))}</code>\n"
        f"Request bot: <code>@{html(_normalize_ref(_request_bot()))}</code>\n"
        f"Portex bot: <code>@{html(_normalize_ref(_portex_bot()))}</code>\n"
        f"Platform: <code>{html(_platform())}</code>\n"
        f"Cooldown: <code>{_cooldown_seconds()}s</code>\n"
        f"Last token hash: <code>{html(str(settings.get(K_LAST_HASH, 'none') or 'none'))}</code>\n\n"
        "<code>.portextma on</code> or <code>.portextma off</code>\n"
        "<code>.portextma send</code> sends a fresh token to the request bot\n"
        "<code>.portextma test</code> refreshes and verifies without sending the token\n"
        "<code>.portextma bot @polymakerAI_bot</code>\n"
        "<code>.portextma portex @portex</code>"
    )


@client.on(events.NewMessage(pattern=r"^\.portextma(?:\s+([\s\S]+))?$", outgoing=True))
async def portex_tma_cmd(event):
    arg = (event.pattern_match.group(1) or "").strip()
    low = arg.lower()

    if not arg or low in {"status", "info"}:
        return await event.edit(await _status_text(), parse_mode="html", link_preview=False)

    if low in {"on", "enable", "enabled"}:
        settings.set_val(K_ENABLED, True)
        return await event.edit("<b>Portex TMA AutoReply enabled.</b>", parse_mode="html")

    if low in {"off", "disable", "disabled"}:
        settings.set_val(K_ENABLED, False)
        return await event.edit("<b>Portex TMA AutoReply disabled.</b>", parse_mode="html")

    if low.startswith("bot "):
        value = arg.split(None, 1)[1].strip()
        settings.set_val(K_REQUEST_BOT, value)
        return await event.edit(f"<b>Request bot saved:</b> <code>{html(value)}</code>", parse_mode="html")

    if low.startswith("portex "):
        value = arg.split(None, 1)[1].strip()
        settings.set_val(K_PORTEX_BOT, value)
        return await event.edit(f"<b>Portex bot saved:</b> <code>{html(value)}</code>", parse_mode="html")

    if low.startswith("platform "):
        value = arg.split(None, 1)[1].strip()
        settings.set_val(K_PLATFORM, value)
        return await event.edit(f"<b>Platform saved:</b> <code>{html(value)}</code>", parse_mode="html")

    if low.startswith("cooldown "):
        value = max(0, int(arg.split(None, 1)[1].strip()))
        settings.set_val(K_COOLDOWN, value)
        return await event.edit(f"<b>Cooldown saved:</b> <code>{value}s</code>", parse_mode="html")

    if low in {"test", "check"}:
        await event.edit("<b>Refreshing Portex TMA and checking API...</b>", parse_mode="html")
        try:
            data = await _get_fresh_portex_tma()
            return await event.edit(
                "<b>Portex TMA check OK.</b>\n\n"
                f"Host: <code>{html(data['host'])}</code>\n"
                f"Owner: <code>{html(_mask_ref(data['user_id']))}</code>\n"
                f"Auth date: <code>{html(str(data['auth_date']))}</code>\n"
                f"API status: <code>{data['status']}</code>\n"
                f"Events: <code>{data['events_count']}</code>\n"
                f"Hash: <code>{html(data['hash'][:12])}</code>",
                parse_mode="html",
                link_preview=False,
            )
        except Exception as e:
            return await event.edit(f"<b>Portex TMA check failed:</b> <code>{html(str(e)[:500])}</code>", parse_mode="html")

    if low in {"send", "now", "refresh"}:
        target = _request_bot()
        await event.edit(f"<b>Sending fresh Portex TMA to</b> <code>@{html(_normalize_ref(target))}</code>...", parse_mode="html")
        try:
            entity = await client.get_input_entity(target)
            data = await _refresh_and_send(entity, force=True)
            return await event.edit(
                "<b>Fresh Portex TMA sent.</b>\n\n"
                f"Owner: <code>{html(_mask_ref(data.get('user_id')))}</code>\n"
                f"API status: <code>{data.get('status')}</code>\n"
                f"Hash: <code>{html(str(data.get('hash', ''))[:12])}</code>",
                parse_mode="html",
                link_preview=False,
            )
        except Exception as e:
            return await event.edit(f"<b>Send failed:</b> <code>{html(str(e)[:500])}</code>", parse_mode="html")

    await event.edit(await _status_text(), parse_mode="html", link_preview=False)


@client.on(events.NewMessage(incoming=True))
async def portex_tma_request_watcher(event):
    if not _enabled() or not event.is_private:
        return

    text = event.raw_text or ""
    if not _looks_like_request(text):
        return

    try:
        sender = await event.get_sender()
        if not _sender_matches(sender, _request_bot()):
            return
        result = await _refresh_and_send(event.chat_id, reply_to=getattr(event.message, "id", None))
        if result.get("skipped"):
            print(f"[PortexTMA] skipped request by cooldown: wait={result.get('wait')}s")
        else:
            print(
                "[PortexTMA] sent fresh token "
                f"owner={_mask_ref(result.get('user_id'))} "
                f"hash={str(result.get('hash', ''))[:12]} "
                f"api={result.get('status')}"
            )
    except Exception as e:
        print(f"[PortexTMA] auto reply failed: {e}")


print("[MOD] Portex TMA AutoReply loaded")
