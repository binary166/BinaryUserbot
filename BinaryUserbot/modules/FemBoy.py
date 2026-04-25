# MODULE_NAME = "FemBoy"
# MODULE_CMD  = ".femboy"
# MODULE_DESC = "Femboy-режим: добавляет премиум-эмодзи и ASCII-лица в твои сообщения"

import random
import asyncio
from telethon import events
from bot_client import client
from premium_emoji import by_line
import state

if not hasattr(state, "femboy_active"):
    state.femboy_active = False

FEMBOY_EMOJIES = [
    '<tg-emoji emoji-id="5424970378374035950">🕺</tg-emoji>',
    '<tg-emoji emoji-id="5429635773714412028">😆</tg-emoji>',
    '<tg-emoji emoji-id="5321451749460946626">😘</tg-emoji>',
    '<tg-emoji emoji-id="5215496967852936076">🥵</tg-emoji>',
    '<tg-emoji emoji-id="5326027259725749455">🤭</tg-emoji>',
    '<tg-emoji emoji-id="5402630084509066049">😏</tg-emoji>',
    '<tg-emoji emoji-id="5327760081461190613">😋</tg-emoji>',
    '<tg-emoji emoji-id="5235787973907205473">👅</tg-emoji>',
]

ASCII_FACES = [
    "(o´ω`o)", "(˘▾˘)", "(✿◠‿◠)", "(≧◡≦)", "(⺣◡⺣)♡*",
    "(๑•́ ₃ •̀๑)", "(✧ω✧)", "(´｡• ᵕ •｡`)", "(〃＾▽＾〃)",
    "(*/ω＼*)", "(＞﹏＜)", "(｡♥‿♥｡)", "(≧◡≦) ♡",
]


def _femboyify(text: str) -> str:
    if not text:
        return text
    words = text.split()
    out = []
    for w in words:
        out.append(w)
        if random.random() > 0.5:
            out.append(random.choice(FEMBOY_EMOJIES))
    tail = f" {random.choice(ASCII_FACES)}" if random.random() > 0.6 else ""
    return " ".join(out) + tail


@client.on(events.NewMessage(pattern=r"^\.femboy$", outgoing=True))
async def femboy_toggle(event):
    state.femboy_active = not state.femboy_active
    if state.femboy_active:
        text = (
            '<tg-emoji emoji-id="5341813983252851777">🌟</tg-emoji> '
            '<b>Режим Femboy включён!</b>\n\n' + by_line()
        )
    else:
        text = (
            '<tg-emoji emoji-id="5318833180915027058">😭</tg-emoji> '
            '<b>Режим Femboy выключен!</b>\n\n' + by_line()
        )
    await event.edit(text, parse_mode="html")


@client.on(events.NewMessage(outgoing=True))
async def femboy_watcher(event):
    if not state.femboy_active:
        return
    raw = event.raw_text or ""
    if not raw or raw.startswith("."):
        return
    if event.message.media:
        return
    new_text = _femboyify(raw)
    if new_text == raw:
        return
    try:
        await asyncio.sleep(0.1)
        await event.edit(new_text, parse_mode="html")
    except Exception:
        pass
