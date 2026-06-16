import re

from telethon import events

from bot_client import client


SPACED_COMMAND_RE = re.compile(r"^\.\s+([^\s.][\s\S]*)$")


def normalize_command_text(text: str | None) -> str | None:
    if not text:
        return text
    match = SPACED_COMMAND_RE.match(text)
    if not match:
        return text
    return "." + match.group(1).lstrip()


@client.on(events.NewMessage(outgoing=True))
async def normalize_spaced_dot_commands(event):
    normalized = normalize_command_text(getattr(event.message, "message", None))
    if normalized and normalized != event.message.message:
        event.message.message = normalized
        event.message._text = None
