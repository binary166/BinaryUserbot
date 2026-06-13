# MODULE_NAME = "RemoveBG"
# MODULE_CMD  = ".removebg"
# MODULE_DESC = "Удаление фона с фото через remove.bg API (.removebg, .rmbgkey <token>)"

import os
import tempfile
import aiohttp
from aiohttp import FormData

from telethon import events
from bot_client import client
from premium_emoji import by_line
from utils import html as esc
import settings

_TOKEN_KEY = "ugN4atzEsXNcdPYdafdgZq9k"


@client.on(events.NewMessage(pattern=r"^\.rmbgkey(?:\s+(\S+))?$", outgoing=True))
async def cmd_rmbg_key(event):
    arg = event.pattern_match.group(1)
    if arg:
        settings.set_val(_TOKEN_KEY, arg)
        await event.edit(
            "🔑 <b>Токен remove.bg сохранён.</b>\n\n" + by_line(),
            parse_mode="html",
        )
        try:
            await event.delete()
        except Exception:
            pass
        return
    cur = settings.get(_TOKEN_KEY)
    state = "<code>задан</code>" if cur else "<code>не задан</code>"
    await event.edit(
        f"🔑 <b>Токен remove.bg:</b> {state}\n"
        "<i>Получить:</i> https://www.remove.bg/dashboard#api-key\n"
        "<i>Установить:</i> <code>.rmbgkey &lt;token&gt;</code>\n\n" + by_line(),
        parse_mode="html", link_preview=False,
    )


@client.on(events.NewMessage(pattern=r"^\.removebg$", outgoing=True))
async def cmd_removebg(event):
    reply = await event.get_reply_message()
    if not reply or not reply.media:
        await event.edit(
            "🚫 <b>Ответь на фото!</b>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    fname = getattr(reply.file, "name", None) or ""
    ext = os.path.splitext(fname)[1].lower()
    if not ext:
        # документ без имени или сжатое фото
        if not getattr(reply, "photo", None):
            await event.edit(
                "😕 <b>Удалять фон можно только с фото (.png, .jpg, .jpeg).</b>\n\n" + by_line(),
                parse_mode="html",
            )
            return
        ext = ".jpg"
        fname = "photo.jpg"
    elif ext not in (".png", ".jpg", ".jpeg"):
        await event.edit(
            "😕 <b>Удалять фон можно только с фото (.png, .jpg, .jpeg).</b>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    token = settings.get(_TOKEN_KEY)
    if not token:
        await event.edit(
            "🚫 <b>Нет токена.</b> Установи через <code>.rmbgkey &lt;token&gt;</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    await event.edit("🔄 <b>Удаление фона...</b>", parse_mode="html")

    with tempfile.TemporaryDirectory() as tmp:
        in_path = os.path.join(tmp, "input" + ext)
        try:
            await reply.download_media(in_path)
        except Exception as e:
            await event.edit(
                f"🚫 <b>Не удалось скачать файл:</b> <code>{esc(str(e))}</code>\n\n" + by_line(),
                parse_mode="html",
            )
            return

        try:
            async with aiohttp.ClientSession() as s:
                form = FormData()
                form.add_field("image_file", open(in_path, "rb"),
                               filename=os.path.basename(in_path))
                form.add_field("size", "auto")
                async with s.post(
                    "https://api.remove.bg/v1.0/removebg",
                    headers={"X-Api-Key": token},
                    data=form,
                ) as res:
                    ctype = res.headers.get("Content-Type", "")
                    if "json" in ctype:
                        j = await res.json()
                        errs = (j or {}).get("errors") or []
                        title = errs[0].get("title", "Ошибка") if errs else "Ошибка"
                        if "API Key invalid" in title:
                            await event.edit(
                                "😕 <b>Неверный токен remove.bg.</b>\n\n" + by_line(),
                                parse_mode="html",
                            )
                            return
                        await event.edit(
                            f"🚫 <b>API ошибка:</b> <code>{esc(title)}</code>\n\n" + by_line(),
                            parse_mode="html",
                        )
                        return
                    data = await res.read()
        except Exception as e:
            await event.edit(
                f"🚫 <b>Ошибка запроса:</b> <code>{esc(str(e))}</code>\n\n" + by_line(),
                parse_mode="html",
            )
            return

        out_name = f"nobg-{os.path.splitext(os.path.basename(fname))[0] or 'photo'}.png"
        out_path = os.path.join(tmp, out_name)
        with open(out_path, "wb") as f:
            f.write(data)

        await client.send_file(
            event.chat_id, out_path, force_document=True,
            caption="🪄 <b>Фон удалён.</b>\n\n" + by_line(),
            parse_mode="html",
            reply_to=reply.id,
        )
        try:
            await event.delete()
        except Exception:
            pass
