from telethon import events
import asyncio

import state
from bot_client import client


@client.on(events.NewMessage(func=lambda e: e.chat_id in state.auto_comment_channels))
async def on_channel_post(event):
    if not state.auto_comment_text:
        return
    msg = event.message
    if not msg.post:
        return

    channel_id         = event.chat_id
    discussion_chat_id = state.auto_comment_channels.get(channel_id)
    if not discussion_chat_id:
        return

    chan_name = getattr(await event.get_chat(), "title", str(channel_id))
    await asyncio.sleep(1.2)

    try:
        await client.send_message(channel_id, state.auto_comment_text, comment_to=msg.id)
        print(f"[КОМ] {chan_name}")
        return
    except Exception as e1:
        print(f"[КОМ] direct: {e1}")

    try:
        from telethon.tl.functions.messages import GetDiscussionMessageRequest
        disc = await client(GetDiscussionMessageRequest(peer=channel_id, msg_id=msg.id))
        await client.send_message(
            discussion_chat_id, state.auto_comment_text,
            reply_to=disc.messages[0].id
        )
        print(f"[КОМ] disc {chan_name}")
        return
    except Exception as e2:
        print(f"[КОМ] disc: {e2}")

    try:
        await client.send_message(discussion_chat_id, state.auto_comment_text)
        print(f"[КОМ] fallback {chan_name}")
    except Exception as e3:
        print(f"[КОМ] {e3}")
