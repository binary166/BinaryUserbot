import re
import time

from utils import html, get_username, resolve_sender
from premium_emoji import by_line
from ai import or_request
from config import SCAM_CHANNEL, LOADING


SCAM_CACHE_TTL = 600
_scam_cache: dict = {"loaded_at": 0.0, "items": {}}


def get_scam_identifiers(user) -> list[str]:
    identifiers: list[str] = []
    if not user:
        return identifiers

    username = getattr(user, "username", None)
    if username:
        identifiers.append(username.lstrip("@").lower())

    for item in (getattr(user, "usernames", None) or []):
        alt = getattr(item, "username", None)
        if alt:
            identifiers.append(alt.lstrip("@").lower())

    user_id = getattr(user, "id", None)
    if user_id:
        identifiers.append(str(user_id))

    result: list[str] = []
    seen = set()
    for value in identifiers:
        value = str(value).strip().lstrip("@").lower()
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _message_contains_identifier(text: str, identifier: str) -> bool:
    text_l = (text or "").lower()
    ident = str(identifier).strip().lstrip("@").lower()
    if not ident:
        return False
    if ident.isdigit():
        return re.search(rf"(?<!\d){re.escape(ident)}(?!\d)", text_l) is not None

    strict_patterns = [
        rf"(?<![a-z0-9_])@{re.escape(ident)}(?![a-z0-9_])",
        rf"(?:https?://)?(?:t\.me|telegram\.me)/{re.escape(ident)}(?![a-z0-9_])",
    ]
    if any(re.search(pattern, text_l) for pattern in strict_patterns):
        return True

    # Bare usernames are accepted only when the message explicitly marks a Telegram username field.
    label = (
        r"(?:юз|юзер|юзернейм|username|user|ник|telegram|телеграм|тг|аккаунт|scammer|скамер)"
        r"\s*[:=\-–—]?\s*@?"
    )
    return re.search(rf"(?<![a-z0-9_]){label}{re.escape(ident)}(?![a-z0-9_])", text_l) is not None


def _extract_scam_identifiers(text: str) -> set[str]:
    text_l = (text or "").lower()
    found: set[str] = set()
    found.update(re.findall(r"(?<![a-z0-9_])@([a-z0-9_]{5,32})(?![a-z0-9_])", text_l))
    found.update(re.findall(r"(?:https?://)?(?:t\.me|telegram\.me)/([a-z0-9_]{5,32})(?![a-z0-9_])", text_l))

    label = (
        r"(?:юз|юзер|юзернейм|username|user|ник|telegram|телеграм|тг|аккаунт|scammer|скамер)"
        r"\s*[:=\-–—]?\s*@?"
    )
    found.update(re.findall(rf"(?<![a-z0-9_]){label}([a-z0-9_][a-z0-9_]{{4,31}})(?![a-z0-9_])", text_l))

    # Telegram IDs are long numeric values. Short numbers in scam posts are often prices/dates.
    found.update(re.findall(r"(?<!\d)(\d{6,20})(?!\d)", text_l))
    return {item.strip().lstrip("@").lower() for item in found if item.strip()}


async def _load_scam_index(force: bool = False) -> dict[str, object]:
    from bot_client import client

    now = time.monotonic()
    if not force and _scam_cache["items"] and now - float(_scam_cache["loaded_at"]) < SCAM_CACHE_TTL:
        return _scam_cache["items"]

    try:
        entity = await client.get_entity(SCAM_CHANNEL)
    except Exception:
        entity = SCAM_CHANNEL

    items: dict[str, object] = {}
    async for msg in client.iter_messages(entity, limit=None):
        text = getattr(msg, "raw_text", None) or getattr(msg, "text", None) or ""
        if not text:
            continue
        for ident in _extract_scam_identifiers(text):
            items.setdefault(ident, msg)

    _scam_cache["loaded_at"] = now
    _scam_cache["items"] = items
    print(f"[scam] indexed {len(items)} identifiers")
    return items


async def check_scam_base(*identifiers: str) -> bool:
    found, _term, _message = await check_scam_base_details(*identifiers)
    return found


async def check_scam_base_details(*identifiers: str) -> tuple[bool, str | None, object | None]:
    terms = []
    seen = set()
    for identifier in identifiers:
        clean = str(identifier or "").strip().lstrip("@").lower()
        if clean and clean not in seen:
            seen.add(clean)
            terms.append(clean)

    try:
        items = await _load_scam_index()
        for term in terms:
            if term in items:
                return True, term, items[term]
    except Exception:
        pass
    return False, None, None


async def cmd_scam(event):
    reply = await event.message.get_reply_message()
    if not reply:
        await event.message.edit("❗ Используй <code>.scam</code> <b>ответом</b>.", parse_mode="html")
        return

    target = await resolve_sender(reply)
    if not target:
        await event.message.edit("❌ Не удалось определить отправителя.", parse_mode="html")
        return

    name  = get_username(target)
    identifiers = get_scam_identifiers(target)
    uname = next((item for item in identifiers if not item.isdigit()), None)
    visible_target = f"@{uname}" if uname else f"ID {target.id}"

    await event.message.edit(LOADING, parse_mode="html")
    found, found_term, _msg = await check_scam_base_details(*identifiers)

    if found:
        await event.message.edit(
            ' \n'
            '<tg-emoji emoji-id="5267123797600783095">❌</tg-emoji> <b>СКАМЕР ОБНАРУЖЕН</b> \n'
            ' \n'
            f'Скамер - <code>{html(visible_target)}</code>\n'
            f'Совпадение - <code>{html(found_term or "")}</code>\n'
            f'<a href="https://t.me/{SCAM_CHANNEL}">@{SCAM_CHANNEL}</a>\n'
            '<tg-emoji emoji-id="5260341314095947411">👀</tg-emoji> Будьте крайне осторожны!\n'
            + by_line(),
            parse_mode="html", link_preview=False
        )
    else:
        await event.message.edit(
            ' \n'
            '<tg-emoji emoji-id="5357069174512303778">✅</tg-emoji> <b>Проверка пройдена</b> \n'
            ' \n'
            f'<code>{html(visible_target)}</code> не найден в базе\n'
            f'<a href="https://t.me/{SCAM_CHANNEL}">@{SCAM_CHANNEL}</a>\n'
            + by_line(),
            parse_mode="html", link_preview=False
        )


async def cmd_lol(event):
    reply = await event.message.get_reply_message()
    if not reply:
        await event.message.edit("❗ Используй <code>.lol</code> <b>ответом</b>.", parse_mode="html")
        return

    target    = await resolve_sender(reply)
    name      = get_username(target) if target else "Unknown"
    last_text = (reply.text or "...")[:80]
    await event.message.edit(LOADING, parse_mode="html")

    try:
        joke = await or_request(
            "Ты саркастичный стендап-комик. Одна короткая едкая шутка про юзера. "
            "Только шутка, до 150 символов. Будь остроумным!",
            f"Ник: {name}. Сообщение: «{last_text}»",
            max_chars=150, max_tokens=200
        )
        await event.message.edit(
            f"😂 <b>Шутка про {html(name)}:</b>\n\n🤣 {html(joke)}\n\n" + by_line(),
            parse_mode="html"
        )
    except Exception as e:
        await event.message.edit(
            f"❌ <b>Ошибка:</b> <code>{html(str(e)[:150])}</code>", parse_mode="html"
        )
