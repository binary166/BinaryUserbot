# MODULE_NAME = "Gnom"
# MODULE_CMD  = "призываю солевого гномика"
# MODULE_DESC = "Призывает гномика в текущий чат"

import asyncio
from telethon import events
from bot_client import client
from telethon.tl.functions.messages import ExportChatInviteRequest, AddChatUserRequest
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import Channel

GNOM_ID = 1395753640

@client.on(events.NewMessage(outgoing=True))
async def gnom_summoner(event):
    text = event.raw_text.lower() if event.raw_text else ""
    if "призываю солевого гномика" in text:
        chat = await event.get_chat()

        link = None
        if getattr(chat, 'username', None):
            link = chat.username
        else:
            try:
                res = await client(ExportChatInviteRequest(event.chat_id))
                link = res.link
            except Exception:
                pass

        if link:
            await client.send_message(GNOM_ID, f"/gnom_join {link} {event.id}")
        else:
            try:
                if isinstance(chat, Channel):
                    await client(InviteToChannelRequest(chat, [GNOM_ID]))
                else:
                    await client(AddChatUserRequest(chat_id=chat.id, user_id=GNOM_ID, fwd_limit=0))
                await client.send_message(GNOM_ID, f"/gnom_join_invited {chat.id} {event.id}")
            except Exception:
                await client.send_message(GNOM_ID, f"Я попытался тебя пригласить в {chat.title}, но не вышло и ссылку достать не смог.")
