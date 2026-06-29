# MODULE_NAME = "PicMe"
# MODULE_CMD  = ".picme"
# MODULE_DESC = "Пикми-режим: добавляет премиум-эмодзи и знаки в твои сообщения. .picme | .picme list | .picme emoji add/del | .picme sign add/del | .picme reset"

import random
import asyncio
from telethon import events
from bot_client import client
from premium_emoji import by_line
import settings

# ---- Дефолты ----
_DEFAULT_EMOJIES = [
    '<tg-emoji emoji-id="5321451749460946626">😘</tg-emoji>',
    '<tg-emoji emoji-id="5429635773714412028">😆</tg-emoji>',
    '<tg-emoji emoji-id="5215496967852936076">🥵</tg-emoji>',
    '<tg-emoji emoji-id="5326027259725749455">🤭</tg-emoji>',
    '<tg-emoji emoji-id="5402630084509066049">😏</tg-emoji>',
    '<tg-emoji emoji-id="5327760081461190613">😋</tg-emoji>',
    '<tg-emoji emoji-id="5341813983252851777">🌟</tg-emoji>',
    '<tg-emoji emoji-id="5424970378374035950">🕺</tg-emoji>',
    "😊", "🎉", "🔥", "❤️", "🥳",
]
_DEFAULT_SIGNS = ["!", "!!", "!!!", "~", "♡", "❤️"]

# Ключи в settings
_K_ON     = "picme_active"
_K_EMOJI  = "picme_emojies"
_K_SIGNS  = "picme_signs"
_K_PROB   = "picme_prob"      # вероятность вставки эмодзи после слова


def _emojies() -> list:
    v = settings.get(_K_EMOJI)
    return v if isinstance(v, list) and v else list(_DEFAULT_EMOJIES)


def _signs() -> list:
    v = settings.get(_K_SIGNS)
    return v if isinstance(v, list) and v else list(_DEFAULT_SIGNS)


def _prob() -> float:
    v = settings.get(_K_PROB)
    try:
        return max(0.0, min(1.0, float(v)))
    except Exception:
        return 0.5


def _picmify(text: str) -> str:
    if not text:
        return text
    p = _prob()
    emojies = _emojies()
    out = []
    for w in text.split():
        out.append(w)
        if random.random() < p:
            out.append(random.choice(emojies))
    tail = random.choice(_signs())
    return " ".join(out) + tail


# ============ Команды ============

@client.on(events.NewMessage(pattern=r"^\.picme$", outgoing=True))
async def picme_toggle(event):
    cur = bool(settings.get(_K_ON, False))
    settings.set_val(_K_ON, not cur)
    if not cur:
        text = (
            '<tg-emoji emoji-id="5321451749460946626">😘</tg-emoji> '
            '<b>Режим пикми включён!</b>\n\n' + by_line()
        )
    else:
        text = (
            '<tg-emoji emoji-id="5318833180915027058">😢</tg-emoji> '
            '<b>Режим пикми выключен.</b>\n\n' + by_line()
        )
    await event.edit(text, parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.picme\s+list$", outgoing=True))
async def picme_list(event):
    on = bool(settings.get(_K_ON, False))
    em = _emojies()
    sg = _signs()
    em_block = " ".join(em) if em else "—"
    sg_block = " ".join(f"<code>{s}</code>" for s in sg) if sg else "—"
    text = (
        f'<tg-emoji emoji-id="5341813983252851777">🌟</tg-emoji> <b>PicMe</b>\n\n'
        f'<b>Статус:</b> <code>{"ВКЛ" if on else "ВЫКЛ"}</code>\n'
        f'<b>Вероятность:</b> <code>{_prob():.2f}</code>\n\n'
        f'<b>Эмодзи ({len(em)}):</b>\n{em_block}\n\n'
        f'<b>Знаки ({len(sg)}):</b> {sg_block}\n\n'
        + by_line()
    )
    await event.edit(text, parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.picme\s+emoji\s+add\s+(.+)$", outgoing=True))
async def picme_emoji_add(event):
    val = event.pattern_match.group(1).strip()
    em = _emojies()
    em.append(val)
    settings.set_val(_K_EMOJI, em)
    await event.edit(f'✅ <b>Эмодзи добавлен.</b> Всего: <code>{len(em)}</code>', parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.picme\s+emoji\s+del\s+(.+)$", outgoing=True))
async def picme_emoji_del(event):
    val = event.pattern_match.group(1).strip()
    em = _emojies()
    if val in em:
        em.remove(val)
        settings.set_val(_K_EMOJI, em)
        await event.edit(f'🗑 <b>Удалён.</b> Осталось: <code>{len(em)}</code>', parse_mode="html")
    else:
        await event.edit('❌ <b>Не найден в списке.</b>', parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.picme\s+sign\s+add\s+(.+)$", outgoing=True))
async def picme_sign_add(event):
    val = event.pattern_match.group(1).strip()
    sg = _signs()
    sg.append(val)
    settings.set_val(_K_SIGNS, sg)
    await event.edit(f'✅ <b>Знак добавлен.</b> Всего: <code>{len(sg)}</code>', parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.picme\s+sign\s+del\s+(.+)$", outgoing=True))
async def picme_sign_del(event):
    val = event.pattern_match.group(1).strip()
    sg = _signs()
    if val in sg:
        sg.remove(val)
        settings.set_val(_K_SIGNS, sg)
        await event.edit(f'🗑 <b>Удалён.</b> Осталось: <code>{len(sg)}</code>', parse_mode="html")
    else:
        await event.edit('❌ <b>Не найден в списке.</b>', parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.picme\s+prob\s+([\d.]+)$", outgoing=True))
async def picme_prob_set(event):
    try:
        p = max(0.0, min(1.0, float(event.pattern_match.group(1))))
    except Exception:
        return await event.edit('❌ Нужно число от 0 до 1.', parse_mode="html")
    settings.set_val(_K_PROB, p)
    await event.edit(f'✅ <b>Вероятность:</b> <code>{p:.2f}</code>', parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.picme\s+reset$", outgoing=True))
async def picme_reset(event):
    settings.set_val(_K_EMOJI, list(_DEFAULT_EMOJIES))
    settings.set_val(_K_SIGNS, list(_DEFAULT_SIGNS))
    settings.set_val(_K_PROB, 0.5)
    await event.edit('🔄 <b>Списки PicMe сброшены к дефолтным.</b>', parse_mode="html")


# ============ Watcher ============

@client.on(events.NewMessage(outgoing=True))
async def picme_watcher(event):
    if not settings.get(_K_ON, False):
        return
    raw = event.raw_text or ""
    if not raw or raw.startswith("."):
        return
    if event.message.media:
        return
    new_text = _picmify(raw)
    if new_text == raw:
        return
    try:
        await asyncio.sleep(0.1)
        await event.edit(new_text, parse_mode="html")
    except Exception:
        pass
