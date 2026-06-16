# MODULE_NAME = "Meow"
# MODULE_CMD  = ".meow"
# MODULE_DESC = "Мяуканье на разных языках (.meow / .stopmeow)"

import asyncio
from telethon import events
from bot_client import client
from premium_emoji import by_line
import state

if not hasattr(state, "meow_active"):
    state.meow_active = False

MEOWS = [
    "Мяу", "Meow", "Miaou", "Miau", "Miao", "야옹", "Miauczeć", "miyav",
    "Мяу", "maullar", "Мјау", "مواء", "myau", "Мияу", "Мөө", "喵喵",
    "Niau", "मयऊ", "မက", "ন", "กน", "მაიო", "मयऊ", "ມອດ",
    "မက", "මය", "מיאו", "մյուռ", "میاو", "मयऊ", "ಮಯವ", "មយវ",
    "മയവ", "мйаоу", "მიაუ", "میاو", "میائو", "เหมยว", "မက",
]


@client.on(events.NewMessage(pattern=r"^\.meow$", outgoing=True))
async def meow(event):
    state.meow_active = True
    msg = await event.edit("😺 <b>Мяу...</b>", parse_mode="html")
    for line in MEOWS:
        if not state.meow_active:
            break
        await asyncio.sleep(2)
        try:
            await msg.edit(line, parse_mode="html")
        except Exception:
            break
    state.meow_active = False


@client.on(events.NewMessage(pattern=r"^\.stopmeow$", outgoing=True))
async def stopmeow(event):
    if state.meow_active:
        state.meow_active = False
        await event.edit("🙀 <b>Ты перестал мяукать.</b>\n\n" + by_line(), parse_mode="html")
    else:
        await event.edit("😾 <b>Ты сейчас не мяукаешь.</b>\n\n" + by_line(), parse_mode="html")
