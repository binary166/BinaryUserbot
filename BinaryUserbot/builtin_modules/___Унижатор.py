# MODULE_NAME = "Унижатор"
# MODULE_CMD  = ".addbull"
# MODULE_DESC = "Автоматически отвечает матом на каждое сообщение указанного пользователя"

import random
import asyncio
from telethon import events
from telethon.tl.types import PeerUser

from bot_client import client
from premium_emoji import by_line
from utils import html
import settings
import state

BULLR = [
    "пошел нахуй",
    "всоси хуяку",
    "хуяру зажуй",
    "мать те ебал",
    "твою мамашу поебем",
    "закрой рыло своё сын шлюхи",
    "хуяру зажуй тебе сказали ты чё тупого из себя строишь",
    "я твою маму ебал сынка шлюхи кривоёблого",
    "ты здесь мою залупу отсосёшь",
    "че замолк идиот ебаный мать те ебём",
    "тебе рот отьёб",
    "сынка шлюхи тебя выебут",
    "ебало в залупу втопи",
    "отсосешь",
    "слитый сын шлюхи соси",
    "в соло всей конфе хуи до блеска соси блядина слабая",
    "ку сосёшь слабак криворукий",
    "грязный хуй соси",
    "член выжуй огромный",
    "пососешь мне шалава черномазая",
    "блядина черная соси тут",
    "сынок шлюхи черный соси",
    "дырявый сын шлюхи соси давай",
    "в очко прими долбоёб ебучий",
    "отсоси мне тут улитка ебучая",
    "твою мамашу поебём слоупок ты ебаный",
    "бери хуище в рот",
    "истеричка ебаная отсоси чё",
    "блядина истеричная соси",
    "доброе утро хуй на",
    "здарова чё сосёшь мне",
    "чё молчишь мать ебём те",
    "поебут мамашу те",
    "на член вафлер ебучий",
    "ну че соси",
    "чё сосёшь тут молча шлюха ебучая",
    "ку твою мать ебал спящий ты сынок проститутки",
    "хуяру высоси сынок блядины",
    "сынка шлюхи порванного тебя ебём",
    "грызи хуище",
    "твой рот отъеб",
    "пососи блядина жирноеблая",
    "пожуй член",
    "ебальник закрой и соси тут сын шлюхи",
    "пососи шалава криворукая",
    "пососи блядье",
    "твою рожу еб",
    "твою маму ёб",
    "маму те ёб",
    "рыло те ебём",
    "всем хуй пососи",
    "те рот выебли шлюхе",
    "ты пидорас",
    "пересоси",
    "чососи",
    "взял хуй в рот, он сказал:",
    "Сосни моего хуйца блядоеб сука",
    "Сосеш ты мне блядина ебаная",
    "сру тебе на рожу чмо ебаное",
    "лох ебаный ты че потух опять",
    "обоссали тебя лошара ссаная",
    "привет сосала ты мне",
    "нассали тебе на патлы хуйло",
    "ку насоси блядовитая",
    "слыш меня клоун ебал я тебя в нос твой красный",
    "не бойся моего говна и сожри его уже блять",
    "время тебе жрать мое дерьмо сука просыпайся",
    "потей давай рабыня хуя эу",
]


def _load() -> dict:
    data = settings.get("bully", None)
    if not isinstance(data, dict):
        data = {"users": [], "phrases": [], "realistic": False}
        settings.set_val("bully", data)
    data.setdefault("users", [])
    data.setdefault("phrases", [])
    data.setdefault("realistic", False)
    return data


def _save(data: dict):
    settings.set_val("bully", data)


def _add_user(uid: int):
    data = _load()
    if uid not in data["users"]:
        data["users"].append(uid)
        _save(data)


def _remove_user(uid: int) -> bool:
    data = _load()
    if uid in data["users"]:
        data["users"].remove(uid)
        _save(data)
        return True
    return False


def _clear_users():
    data = _load()
    data["users"] = []
    _save(data)


def _add_phrase(phrase: str):
    data = _load()
    data["phrases"].append(phrase)
    _save(data)


def _toggle_realistic() -> bool:
    data = _load()
    data["realistic"] = not data["realistic"]
    _save(data)
    return data["realistic"]


def _all_phrases() -> list:
    data = _load()
    return BULLR + data["phrases"]


@client.on(events.NewMessage(pattern=r"^\.addbull$", outgoing=True))
async def cmd_addbull(event):
    reply = await event.get_reply_message()
    if not reply:
        await event.edit("🚫 <b>Нужен реплай на сообщение пользователя.</b>\n\n" + by_line(), parse_mode="html")
        return
    uid = None
    if reply.from_id and isinstance(reply.from_id, PeerUser):
        uid = reply.from_id.user_id
    elif reply.sender_id:
        uid = reply.sender_id
    if not uid:
        await event.edit("🚫 <b>Не могу определить пользователя.</b>\n\n" + by_line(), parse_mode="html")
        return
    _add_user(uid)
    try:
        ent = await client.get_entity(uid)
        name = html((getattr(ent, "first_name", "") or "") + " " + (getattr(ent, "last_name", "") or "")).strip() or str(uid)
    except Exception:
        name = str(uid)
    await event.edit(
        f"☠️ <b>Теперь буллю</b> <a href=\"tg://user?id={uid}\">{name}</a>\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.rmbull$", outgoing=True))
async def cmd_rmbull(event):
    reply = await event.get_reply_message()
    uid = None
    if reply:
        if reply.from_id and isinstance(reply.from_id, PeerUser):
            uid = reply.from_id.user_id
        elif reply.sender_id:
            uid = reply.sender_id
    if not uid:
        args = event.raw_text.split(None, 1)
        if len(args) > 1 and args[1].strip().lstrip("-").isdigit():
            uid = int(args[1].strip())
    if not uid:
        await event.edit("🚫 <b>Нужен реплай или ID.</b>\n\n" + by_line(), parse_mode="html")
        return
    ok = _remove_user(uid)
    if ok:
        await event.edit(f"💀 <b>Больше не буллю</b> <code>{uid}</code>\n\n" + by_line(), parse_mode="html")
    else:
        await event.edit(f"💀 <b>Я и так не буллил</b> <code>{uid}</code>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.clearbull$", outgoing=True))
async def cmd_clearbull(event):
    _clear_users()
    await event.edit("☠️ <b>Очищен список жертв — никого больше не буллю.</b>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.bulla(?:\s+(.+))?$", outgoing=True))
async def cmd_bulla(event):
    m = event.pattern_match.group(1)
    if not m:
        await event.edit("🚫 <b>Не указана фраза.</b>\n<code>.bulla твоя фраза</code>\n\n" + by_line(), parse_mode="html")
        return
    phrase = m.strip()
    _add_phrase(phrase)
    await event.edit(f"☠️ <b>Фраза добавлена:</b> <i>{html(phrase)}</i>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.bullr$", outgoing=True))
async def cmd_bullr(event):
    await event.edit(random.choice(_all_phrases()))


@client.on(events.NewMessage(pattern=r"^\.trealistic$", outgoing=True))
async def cmd_trealistic(event):
    on = _toggle_realistic()
    if on:
        await event.edit("🫠 <b>Реалистичный режим включён.</b> Буду имитировать печатание.\n\n" + by_line(), parse_mode="html")
    else:
        await event.edit("🥸 <b>Реалистичный режим выключен.</b>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.bulllist$", outgoing=True))
async def cmd_bulllist(event):
    data = _load()
    users = data.get("users", [])
    phrases = data.get("phrases", [])
    if not users:
        users_str = "<i>пусто</i>"
    else:
        users_str = "\n".join(f"▫️ <code>{u}</code>" for u in users[:30])
        if len(users) > 30:
            users_str += f"\n<i>... ещё {len(users) - 30}</i>"
    custom_str = f"<b>Своих фраз:</b> <code>{len(phrases)}</code>"
    await event.edit(
        f"☠️ <b>Унижатор</b>\n\n"
        f"<b>Режим:</b> {'🫠 реалистичный' if data.get('realistic') else '🥸 мгновенный'}\n"
        f"<b>Всего фраз:</b> <code>{len(BULLR) + len(phrases)}</code>  "
        f"({len(BULLR)} встроенных + {len(phrases)} своих)\n\n"
        f"<b>Буллим:</b>\n<blockquote>{users_str}</blockquote>\n\n"
        + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(incoming=True))
async def bully_watcher(event):
    try:
        data = _load()
        users = data.get("users", [])
        if not users:
            return
        sender = event.sender_id
        if not sender or sender not in users:
            return

        phrase = random.choice(_all_phrases())

        if data.get("realistic"):
            try:
                await client.send_read_acknowledge(event.chat_id, event.message)
            except Exception:
                pass
            speed = random.uniform(0.06, 0.18)
            delay = min(max(len(phrase) * speed, 1.0), 8.0)
            try:
                async with client.action(event.chat_id, "typing"):
                    await asyncio.sleep(delay)
                    await event.reply(phrase)
            except Exception:
                await event.reply(phrase)
        else:
            await event.reply(phrase)
    except Exception as e:
        print(f"[bully] {e}")
