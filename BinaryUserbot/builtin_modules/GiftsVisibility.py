# MODULE_NAME = "GiftsVisibility"
# MODULE_CMD  = ".hgifts"
# MODULE_DESC = "Скрыть/показать подарки звёздами в профиле. Флаги: -l лимит, -g обычные, -n NFT"

import asyncio
from telethon import events
from telethon.tl.functions.payments import GetSavedStarGiftsRequest, SaveStarGiftRequest
from telethon.tl.types import SavedStarGift, StarGiftUnique, StarGift, InputSavedStarGiftUser

from bot_client import client
from premium_emoji import by_line


LOADING = "<blockquote>💫 <b>Получаю подарки...</b></blockquote>"
NO_GIFTS = "<blockquote>☹️ <b>У вас нет подарков.</b></blockquote>"
NO_SELECTION = "<blockquote>☹️ <b>Нет подарков под выбранные флаги.</b></blockquote>"
PROCESSING = "<blockquote>💫 <b>Обрабатываю</b> <code>{}</code> <b>подарков...</b></blockquote>"
DONE_HIDDEN = "<blockquote>✅ <b>Скрыто</b> <code>{}</code> <b>подарков.</b></blockquote>"
DONE_SHOWN = "<blockquote>✅ <b>Показано</b> <code>{}</code> <b>подарков.</b></blockquote>"
ERRORS = "<blockquote>❗️ <b>Ошибок при обработке:</b> {}</blockquote>"


async def _fetch_all_saved():
    first = await client(GetSavedStarGiftsRequest(peer="me", offset="", limit=100))
    gifts = list(first.gifts) if getattr(first, "gifts", None) else []
    total = getattr(first, "count", len(gifts))
    if total > len(gifts):
        pages = (total + 99) // 100
        for i in range(1, pages):
            nxt = await client(
                GetSavedStarGiftsRequest(peer="me", offset=str(100 * i).encode(), limit=100)
            )
            gifts.extend(nxt.gifts)
    return gifts


def _parse_flags(rest: str):
    args = (rest or "").lower()
    nft = gifts = limited = False
    if "-nft" in args or "-n" in args:
        nft = True
    if "-gifts" in args or "-g" in args:
        gifts = True
    if "-limited" in args or "-l" in args:
        limited = True
    return nft, gifts, limited


async def _process(event, unsave: bool):
    rest = event.raw_text.split(None, 1)
    rest = rest[1] if len(rest) > 1 else ""
    nft, gifts_flag, limited = _parse_flags(rest)

    await event.edit(LOADING, parse_mode="html")

    gifts_list = await _fetch_all_saved()
    if not gifts_list:
        await event.edit(NO_GIFTS + "\n\n" + by_line(), parse_mode="html")
        return

    candidates = []
    for gift in gifts_list:
        if not isinstance(gift, SavedStarGift) or not gift.msg_id:
            continue
        is_unique = isinstance(gift.gift, StarGiftUnique)
        is_star = isinstance(gift.gift, StarGift)
        is_limited = getattr(gift.gift, "limited", False) if is_star else False
        if not (nft or gifts_flag or limited):
            candidates.append(gift)
        elif (is_unique and nft) or (is_star and is_limited and limited) or (
            is_star and not is_limited and gifts_flag
        ):
            candidates.append(gift)

    if not candidates:
        await event.edit(NO_SELECTION + "\n\n" + by_line(), parse_mode="html")
        return

    await event.edit(PROCESSING.format(len(candidates)), parse_mode="html")

    processed = errors = 0
    for g in candidates:
        try:
            await client(
                SaveStarGiftRequest(
                    stargift=InputSavedStarGiftUser(msg_id=g.msg_id),
                    unsave=unsave,
                )
            )
            processed += 1
            await asyncio.sleep(0.15)
        except Exception:
            errors += 1
            await asyncio.sleep(0.2)

    result = (DONE_HIDDEN if unsave else DONE_SHOWN).format(processed)
    if errors:
        result += "\n" + ERRORS.format(errors)
    await event.edit(result + "\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.hgifts(?:\s|$)", outgoing=True))
async def cmd_hgifts(event):
    await _process(event, True)


@client.on(events.NewMessage(pattern=r"^\.sgifts(?:\s|$)", outgoing=True))
async def cmd_sgifts(event):
    await _process(event, False)
