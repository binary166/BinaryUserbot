# MODULE_NAME = "TagWatcher"
# MODULE_CMD  = ".tagwatcher"
# MODULE_DESC = "Уведомляет о reply/упоминаниях и умеет автоматически читать личные сообщения."

import logging

from telethon import events
from telethon.tl.functions.messages import MarkDialogUnreadRequest

import state
from bot_client import client
from premium_emoji import by_line, pe
from utils import html


logger = logging.getLogger("TagWatcher")


def _ensure_defaults():
    if not hasattr(state, "tagger_enabled"):
        state.tagger_enabled = True
    if not hasattr(state, "pm_autoread"):
        state.pm_autoread = False
    if not hasattr(state, "ignore_bots"):
        state.ignore_bots = True
    if not hasattr(state, "ignore_chats"):
        state.ignore_chats = []
    if not hasattr(state, "blacklist_chats"):
        state.blacklist_chats = []
    if not hasattr(state, "ignore_users"):
        state.ignore_users = []
    if not hasattr(state, "blacklist_users"):
        state.blacklist_users = []
    if not hasattr(state, "pm_mark_unread"):
        state.pm_mark_unread = False
    if not hasattr(state, "custom_notif_text"):
        state.custom_notif_text = None


_ensure_defaults()


def _onoff(value: bool) -> str:
    return "включено" if value else "выключено"


async def _make_link(event, chat) -> str:
    username = getattr(chat, "username", None)
    if username:
        return f"https://t.me/{username}/{event.id}"
    chat_id = str(event.chat_id)
    if chat_id.startswith("-100"):
        return f"https://t.me/c/{chat_id[4:]}/{event.id}"
    return ""


async def _status_text() -> str:
    return (
        f'{pe("bell")} <b>TagWatcher</b>\n\n'
        f"Уведомления: <b>{_onoff(bool(state.tagger_enabled))}</b>\n"
        f"Авточтение ЛС: <b>{_onoff(bool(state.pm_autoread))}</b>\n"
        f"Оставлять ЛС непрочитанными: <b>{_onoff(bool(state.pm_mark_unread))}</b>\n"
        f"Игнорировать ботов: <b>{_onoff(bool(state.ignore_bots))}</b>\n\n"
        f"<code>.tagwatcher</code> — уведомления on/off\n"
        f"<code>.tagwatcher pm</code> — авточтение ЛС\n"
        f"<code>.tagwatcher unread</code> — помечать ЛС непрочитанными\n"
        f"<code>.tagwatcher status</code> — статус\n\n"
        f"{by_line()}"
    )


@client.on(events.NewMessage(pattern=r"^\.tagwatcher(?:\s+(.+))?$", outgoing=True))
async def tagwatcher_cmd(event):
    _ensure_defaults()
    arg = (event.pattern_match.group(1) or "").strip().lower()

    if arg in {"status", "статус", "info"}:
        return await event.edit(await _status_text(), parse_mode="html")

    if arg in {"pm", "лс", "autoread"}:
        state.pm_autoread = not bool(state.pm_autoread)
        return await event.edit(
            f'{pe("bell")} <b>Авточтение ЛС {_onoff(state.pm_autoread)}</b>\n\n{by_line()}',
            parse_mode="html",
        )

    if arg in {"unread", "непрочит", "mark"}:
        state.pm_mark_unread = not bool(state.pm_mark_unread)
        return await event.edit(
            f'{pe("bell")} <b>Пометка ЛС непрочитанными {_onoff(state.pm_mark_unread)}</b>\n\n{by_line()}',
            parse_mode="html",
        )

    state.tagger_enabled = not bool(state.tagger_enabled)
    await event.edit(
        f'{pe("bell")} <b>TagWatcher {_onoff(state.tagger_enabled)}</b>\n\n{by_line()}',
        parse_mode="html",
    )


@client.on(events.NewMessage(incoming=True))
async def pm_reader(event):
    _ensure_defaults()
    if not state.pm_autoread or not event.is_private:
        return

    try:
        chat = await event.get_chat()
        chat_id = getattr(chat, "id", None)
        if chat_id in state.ignore_users:
            return
        if state.ignore_bots and getattr(chat, "bot", False):
            return

        await client.send_read_acknowledge(chat_id, event, clear_mentions=True)
        if state.pm_mark_unread:
            peer = await client.get_input_entity(chat_id)
            await client(MarkDialogUnreadRequest(peer, True))
    except Exception as e:
        logger.error("pm_reader: %s", e)


@client.on(events.NewMessage(incoming=True))
async def inform(event):
    _ensure_defaults()
    if not state.tagger_enabled or event.is_private:
        return

    try:
        me = await client.get_me()
        sender = await event.get_sender()
        if not sender:
            return
        if event.chat_id in state.ignore_chats or sender.id in state.ignore_users:
            return
        if event.chat_id in state.blacklist_chats or sender.id in state.blacklist_users:
            return
        if state.ignore_bots and getattr(sender, "bot", False):
            return

        reply = await event.get_reply_message() if event.is_reply else None
        reply_to_me = bool(reply and reply.sender_id == me.id)
        mentioned = bool(getattr(event, "mentioned", False))

        if not reply_to_me and not mentioned:
            return

        await client.send_read_acknowledge(event.chat_id, event, clear_mentions=True)

        chat = await event.get_chat()
        chat_title = getattr(chat, "title", None) or getattr(chat, "first_name", None) or str(event.chat_id)
        sender_name = (
            (getattr(sender, "first_name", "") or "") + " " + (getattr(sender, "last_name", "") or "")
        ).strip() or getattr(sender, "username", None) or str(sender.id)
        msg_content = event.raw_text or "Пустое сообщение"
        link = await _make_link(event, chat)

        template = state.custom_notif_text or (
            "<b>Вас отметили в <code>{title}</code></b>\n\n"
            "<b>От:</b> <a href='tg://user?id={user_id}'>{name}</a>\n"
            "<b>Текст:</b> <blockquote>{msg_content}</blockquote>\n"
            "{link_line}"
        )
        link_line = f"<a href='{html(link)}'>Перейти к сообщению</a>" if link else ""
        text = template.format(
            title=html(chat_title),
            name=html(sender_name),
            user_id=sender.id,
            msg_content=html(msg_content[:1200]),
            link=html(link),
            link_line=link_line,
        )
        await client.send_message(state.logs_chat_id, text + "\n\n" + by_line(), parse_mode="html", link_preview=False)
    except Exception as e:
        logger.error("inform: %s", e)


print("[MOD] TagWatcher загружен")
