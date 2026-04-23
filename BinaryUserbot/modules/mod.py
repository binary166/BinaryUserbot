# MODULE_NAME = "Счётчик"
# MODULE_CMD  = ".len"
# MODULE_DESC = "Статистика текста ответом на сообщение"

from telethon import events
from bot_client import client
from premium_emoji import pe, by_line

@client.on(events.NewMessage(pattern=r"^\.len$", outgoing=True))
async def cmd_len(event):
    if not event.is_reply:
        return await event.edit("❗ Нужен ответ на сообщение.")

    reply = await event.get_reply_message()
    text = reply.text or ""
    res = (f"{pe('brain')} <b>Статистика:</b>\n"
           f"Символов: <code>{len(text)}</code>\n"
           f"Слов: <code>{len(text.split())}</code>\n\n" + by_line())
    await event.edit(res, parse_mode="html")
