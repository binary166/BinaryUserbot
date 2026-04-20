"""
Проверка по скам-базе @GID_ScamBase и команда .lol.
"""
from utils import html, get_username, resolve_sender
from premium_emoji import by_line
from ai import or_request
from config import SCAM_CHANNEL, LOADING


async def check_scam_base(username: str) -> bool:
    from bot_client import client

    if not username:
        return False
    try:
        clean = username.lstrip("@").lower()
        async for msg in client.iter_messages(SCAM_CHANNEL, search=clean, limit=30):
            if msg.text and clean in msg.text.lower():
                return True
    except Exception:
        pass
    return False


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
    uname = getattr(target, "username", None)
    if not uname:
        for u in (getattr(target, "usernames", None) or []):
            un = getattr(u, "username", None)
            if un:
                uname = un
                break
    if not uname:
        await event.message.edit(
            f"❓ <b>{html(name)}</b> — нет юзернейма.\n🆔 ID: <code>{target.id}</code>",
            parse_mode="html"
        )
        return

    await event.message.edit(LOADING, parse_mode="html")
    found = await check_scam_base(uname)

    if found:
        await event.message.edit(
            ' \n'
            '<tg-emoji emoji-id="5267123797600783095">❌</tg-emoji> <b>СКАМЕР ОБНАРУЖЕН</b> \n'
            ' \n'
            f'Скамер - @{html(uname)}\n'
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
            f'@{html(uname)} не найден в базе\n'
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
