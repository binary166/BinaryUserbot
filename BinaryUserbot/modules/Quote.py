# MODULE_NAME = "Quote"
# MODULE_CMD  = ".ц"
# MODULE_DESC = "Создает красивые цитаты из сообщений. Алиасы: .q, .фц, .fq"
# requires: aiohttp pillow

import base64
import io
from time import gmtime
from typing import Optional

import aiohttp
import telethon
from telethon import events
from telethon.extensions import html as telethon_html
from telethon.tl import types
from telethon.tl.patched import Message

from bot_client import client
from utils import extract_formatted_body, get_args_raw, html, run_sync

try:
    from premium_emoji import by_line
except Exception:
    def by_line():
        return "<i>Binary Userbot</i>"


QUOTE_TYPE = "quote"
BG_COLOR = "#162330"
WIDTH = 512
HEIGHT = 768
SCALE = 2
EMOJI_BRAND = "apple"
MAX_MESSAGES = 15
ENDPOINT = "https://kok.gay/gayotes/generate"
RF_ENDPOINT = "https://ru.kok.gay/gayotes/generate"


def _status(text: str) -> str:
    return f"<b>Quote</b>\n\n{text}"


def _duration(seconds: int | float) -> str:
    time_value = gmtime(seconds or 0)
    prefix = f"{time_value.tm_hour:02d}:" if time_value.tm_hour > 0 else ""
    return f"{prefix}{time_value.tm_min:02d}:{time_value.tm_sec:02d}"


def _split_name(name: Optional[str]) -> tuple[str, str]:
    if not name:
        return "", ""

    parts = str(name).split()
    return parts[0], " ".join(parts[1:]) if len(parts) > 1 else ""


def _entities_to_quote(entities) -> list[dict]:
    result = []
    if not entities:
        return result

    entity_map = {
        "bold": "bold",
        "italic": "italic",
        "underline": "underline",
        "strikethrough": "strikethrough",
        "code": "code",
        "pre": "pre",
        "texturl": "text_link",
        "url": "url",
        "email": "email",
        "phone": "phone_number",
        "mention": "mention",
        "mentionname": "text_mention",
        "hashtag": "hashtag",
        "cashtag": "cashtag",
        "botcommand": "bot_command",
        "spoiler": "spoiler",
        "customemoji": "custom_emoji",
    }

    for entity in entities:
        try:
            data = entity.to_dict()
            raw_type = data.pop("_", "").replace("MessageEntity", "").lower()
            if not raw_type:
                continue

            entity_type = entity_map.get(raw_type, raw_type)
            item = {
                "type": entity_type,
                "offset": data.get("offset", 0),
                "length": data.get("length", 0),
            }

            if raw_type == "texturl":
                item["url"] = data.get("url", "")
            elif raw_type == "mentionname":
                item["user"] = {"id": data.get("user_id", 0)}
            elif raw_type == "customemoji":
                item["custom_emoji_id"] = str(data.get("document_id", ""))
            elif raw_type == "pre":
                item["language"] = data.get("language", "")

            result.append(item)
        except Exception:
            continue

    return result


def _waveform(data: Optional[bytes]) -> list[int]:
    if not data:
        return []

    count = (len(data) * 8) // 5
    if not count:
        return []

    result = []
    for index in range(count):
        bit_index = index * 5
        byte_index = bit_index // 8
        shift = bit_index % 8
        if byte_index + 1 < len(data):
            value = int.from_bytes(data[byte_index:byte_index + 2], "little")
        else:
            value = data[byte_index]
        result.append((value >> shift) & 0b11111)

    return result


def _media_description(message: Message, reply: bool = False) -> str:
    try:
        file_name = getattr(getattr(message, "file", None), "name", "") or ""
        sticker_emoji = getattr(getattr(message, "file", None), "emoji", "") or ""

        if message.photo and reply:
            return "Фото"
        if message.sticker and reply:
            return f"{sticker_emoji} Стикер".strip()
        if message.video_note and reply:
            return "Видеоcообщение"
        if message.video and reply:
            return "Видео"
        if message.gif:
            return "GIF"
        if message.poll:
            return "Опрос"
        if message.geo:
            return "Местоположение"
        if message.contact:
            return "Контакт"
        if message.voice:
            duration = getattr(message.voice.attributes[0], "duration", 0)
            return f"Голосовое сообщение: {_duration(duration)}"
        if message.audio:
            attr = message.audio.attributes[0]
            duration = getattr(attr, "duration", 0)
            performer = getattr(attr, "performer", "") or ""
            title = getattr(attr, "title", "") or ""
            return f"Музыка: {_duration(duration)} | {performer} - {title}".strip()
        if isinstance(message.media, types.MessageMediaDocument) and not _pick_media(message):
            return f"Файл: {file_name}" if file_name else "Файл"
        if isinstance(message.media, types.MessageMediaDice):
            return f"{message.media.emoticon} Кость: {message.media.value}"
        if isinstance(message, types.MessageService):
            return f"Сервисное сообщение: {message.action.to_dict().get('_')}"
    except Exception:
        return ""

    return ""


def _pick_media(message: Message):
    if message and message.media:
        return message.photo or message.sticker or message.video or message.video_note or message.gif or message.web_preview
    return None


def _image_to_data_url(data: bytes, circle: bool = False) -> Optional[str]:
    try:
        from PIL import Image, ImageDraw

        image = Image.open(io.BytesIO(data))
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        if circle:
            size = min(image.size)
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
            square = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            offset = ((size - image.width) // 2, (size - image.height) // 2)
            square.paste(image, offset)
            image = Image.composite(square, Image.new("RGBA", (size, size), (0, 0, 0, 0)), mask)

        output = io.BytesIO()
        image.save(output, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(output.getvalue()).decode()}"
    except Exception:
        return None


def _sticker_to_data_url(data: bytes) -> Optional[str]:
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        output = io.BytesIO()
        image.save(output, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(output.getvalue()).decode()}"
    except Exception:
        return None


async def _process_media(message: Message) -> Optional[dict]:
    try:
        if message.voice:
            for attr in message.voice.attributes or []:
                if getattr(attr, "voice", False) and hasattr(attr, "waveform"):
                    return {"voice": {"waveform": _waveform(attr.waveform)}}

        picked = _pick_media(message)
        if not picked:
            return None

        data = await client.download_media(picked, bytes, thumb=-1)
        if not data:
            return None

        if message.sticker:
            url = await run_sync(_sticker_to_data_url, data)
        else:
            url = await run_sync(_image_to_data_url, data, bool(message.video_note))

        return {"url": url} if url else None
    except Exception:
        return None


async def _avatar(user_id: int) -> Optional[str]:
    try:
        data = await client.download_profile_photo(user_id, bytes)
        if data:
            return f"data:image/jpeg;base64,{base64.b64encode(data).decode()}"
    except Exception:
        pass
    return None


async def _post_quote(payload: dict, file_format: str) -> tuple[int, bytes, str]:
    timeout = aiohttp.ClientTimeout(total=45)
    errors = []

    for endpoint in (ENDPOINT, RF_ENDPOINT):
        url = f"{endpoint}.{file_format}"
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload) as response:
                    content = await response.read()
                    if response.status == 200:
                        return response.status, content, ""

                    try:
                        parsed = await response.json(content_type=None)
                        error = parsed.get("error") or f"HTTP {response.status}"
                    except Exception:
                        error = content.decode("utf-8", errors="ignore")[:500] or f"HTTP {response.status}"
                    errors.append(f"{endpoint}: {error}")
        except Exception as e:
            errors.append(f"{endpoint}: {e}")

    return 0, b"", "; ".join(errors) or "API не ответил"


async def _message_author(message: Message):
    try:
        if getattr(message, "fwd_from", None):
            forward = message.fwd_from
            if getattr(forward, "from_id", None):
                peer_id = forward.from_id
                user_id = peer_id.channel_id if isinstance(peer_id, types.PeerChannel) else peer_id.user_id
                try:
                    return await client.get_entity(user_id)
                except Exception:
                    return await message.get_sender()

            if getattr(forward, "from_name", None):
                name = forward.from_name
                return types.User(
                    id=abs(hash(name)) % 2147483647,
                    first_name=name,
                    username=None,
                    phone=None,
                    bot=False,
                    verified=False,
                    restricted=False,
                    scam=False,
                    fake=False,
                    premium=False,
                )

        return await message.get_sender()
    except Exception:
        return getattr(message, "sender", None)


async def _reply_block(message: Message) -> Optional[dict]:
    try:
        replied = await message.get_reply_message()
        if not replied:
            return None

        reply_user = await _message_author(replied)
        if not reply_user:
            return None

        reply_name = telethon.utils.get_display_name(reply_user)
        reply_text = _media_description(replied, True)
        if replied.raw_text:
            reply_text = f"{reply_text}. {replied.raw_text}" if reply_text else replied.raw_text

        return {
            "name": reply_name,
            "text": reply_text or "",
            "entities": _entities_to_quote(replied.entities),
            "chatId": getattr(reply_user, "id", message.chat_id),
            "from": {"name": reply_name},
        }
    except Exception:
        return None


async def _message_to_quote(message: Message) -> Optional[dict]:
    try:
        user = await _message_author(message)
        if not user:
            return None

        name = telethon.utils.get_display_name(user)
        first_name, last_name = _split_name(name)
        avatar = await _avatar(getattr(user, "id", 0)) if getattr(user, "id", None) else None

        text = message.raw_text or ""
        description = _media_description(message)
        if description:
            text = f"{text}\n\n{description}" if text else description

        item = {
            "from": {
                "id": getattr(user, "id", 0),
                "first_name": getattr(user, "first_name", "") or first_name,
                "last_name": getattr(user, "last_name", "") or last_name,
                "username": getattr(user, "username", None),
                "name": name,
                "photo": {"url": avatar} if avatar else {},
            },
            "text": text,
            "entities": _entities_to_quote(message.entities),
            "avatar": True,
        }

        media = await _process_media(message)
        if media:
            item["voice" if "voice" in media else "media"] = media.get("voice", media)

        emoji_status = getattr(user, "emoji_status", None)
        if getattr(emoji_status, "document_id", None):
            item["from"]["emoji_status"] = str(emoji_status.document_id)

        reply = await _reply_block(message)
        if reply:
            item["replyMessage"] = reply

        return item
    except Exception:
        return None


async def _collect_messages(command_message: Message, count: int) -> Optional[list[dict]]:
    reply = await command_message.get_reply_message()
    if not reply:
        return None

    messages = [reply]
    if count > 1:
        async for message in client.iter_messages(
            command_message.chat_id,
            min_id=reply.id,
            reverse=True,
            limit=count + 10,
        ):
            if message.id == command_message.id:
                continue
            messages.append(message)
            if len(messages) >= count:
                break

    result = []
    for message in messages[:count]:
        item = await _message_to_quote(message)
        if item:
            result.append(item)

    return result


def _parse_quote_args(raw: str) -> tuple[int, str, bool]:
    parts = (raw or "").split()
    as_file = any(part.lower() == "!file" for part in parts)
    count = 1
    background = BG_COLOR

    for part in parts:
        if part.isdigit() and int(part) > 0:
            count = int(part)
            continue
        if part.lower() != "!file":
            background = part

    return count, background, as_file


async def _fake_token(value: str):
    parts = value.split()
    if not parts:
        return None, ""

    target = parts[0]
    text = value.split(maxsplit=1)[1] if len(parts) > 1 else ""
    try:
        user = await client.get_entity(int(target) if target.isdigit() else target)
        return user, text
    except Exception:
        return None, text


async def _fake_messages(raw_html: str, reply: Optional[Message]) -> list[dict]:
    async def build(user, text: str, entities=None, reply_block=None):
        name = telethon.utils.get_display_name(user)
        first_name, last_name = _split_name(name)
        avatar = await _avatar(user.id) if getattr(user, "id", None) else None

        item = {
            "from": {
                "id": user.id,
                "first_name": getattr(user, "first_name", "") or first_name,
                "last_name": getattr(user, "last_name", "") or last_name,
                "username": getattr(user, "username", None),
                "name": name,
                "photo": {"url": avatar} if avatar else {},
            },
            "text": text or "",
            "entities": _entities_to_quote(entities or []),
            "avatar": True,
        }

        emoji_status = getattr(user, "emoji_status", None)
        if getattr(emoji_status, "document_id", None):
            item["from"]["emoji_status"] = str(emoji_status.document_id)
        if reply_block:
            item["replyMessage"] = reply_block
        return item

    if reply and not raw_html:
        user = await reply.get_sender()
        return [await build(user, "")]

    if reply and raw_html:
        user = await reply.get_sender()
        text, entities = telethon_html.parse(raw_html)
        return [await build(user, text, entities)]

    result = []
    for part in raw_html.split("; "):
        try:
            reply_block = None
            if " -r " in part:
                left, right = part.split(" -r ", 1)
                user, text_html = await _fake_token(left)
                reply_user, reply_text_html = await _fake_token(right)
            else:
                user, text_html = await _fake_token(part)
                reply_user, reply_text_html = None, ""

            if not user:
                continue

            text, entities = telethon_html.parse(text_html) if text_html else ("", [])

            if reply_user:
                reply_text, reply_entities = telethon_html.parse(reply_text_html) if reply_text_html else ("", [])
                reply_name = telethon.utils.get_display_name(reply_user)
                reply_avatar = await _avatar(reply_user.id) if getattr(reply_user, "id", None) else None
                reply_block = {
                    "name": reply_name,
                    "text": reply_text,
                    "entities": _entities_to_quote(reply_entities),
                    "chatId": reply_user.id,
                    "from": {
                        "name": reply_name,
                        "photo": {"url": reply_avatar} if reply_avatar else {},
                    },
                }

            result.append(await build(user, text, entities, reply_block))
        except Exception:
            continue

    return result


async def _send_rendered(event, status_message, payload: dict, as_file: bool = False):
    file_format = "png" if as_file else "webp"
    await status_message.edit(_status("Жду ответ API..."), parse_mode="html")

    status, content, error = await _post_quote(payload, file_format)
    if status != 200 or not content:
        return await status_message.edit(
            _status(f"Ошибка API: <code>{html(error or 'нет ответа')}</code>"),
            parse_mode="html",
            link_preview=False,
        )

    output = io.BytesIO(content)
    output.name = f"quote.{file_format}"

    await client.send_file(
        event.chat_id,
        output,
        force_document=as_file,
        reply_to=getattr(await event.get_reply_message(), "id", None),
        caption=by_line(),
        parse_mode="html",
    )
    await status_message.delete()


@client.on(events.NewMessage(pattern=r"^\.(?:ц|q)(?:\s+([\s\S]+))?$", outgoing=True))
async def quotecmd(event):
    raw = event.pattern_match.group(1) or ""

    if raw.strip().lower() in {"help", "хелп", "?"}:
        return await event.edit(
            _status(
                "Ответь на сообщение командой <code>.ц</code>.\n\n"
                "<code>.ц</code> - цитата одного сообщения\n"
                "<code>.ц 3</code> - цитата 3 сообщений подряд\n"
                "<code>.ц #2d2d2d</code> - свой фон\n"
                "<code>.ц 3 #2d2d2d</code> - несколько сообщений со своим фоном\n"
                "<code>.ц !file</code> - отправить PNG файлом\n\n"
                "Алиас: <code>.q</code>\n\n"
                f"{by_line()}"
            ),
            parse_mode="html",
            link_preview=False,
        )

    reply = await event.get_reply_message()
    if not reply:
        return await event.edit(
            _status("Ответь командой <code>.ц</code> на сообщение, которое нужно процитировать."),
            parse_mode="html",
        )

    count, background, as_file = _parse_quote_args(raw)
    if count > MAX_MESSAGES:
        return await event.edit(
            _status(f"Слишком много сообщений. Максимум: <code>{MAX_MESSAGES}</code>"),
            parse_mode="html",
        )

    status_message = await event.edit(_status("Собираю сообщения..."), parse_mode="html")
    messages = await _collect_messages(event, count)
    if not messages:
        return await status_message.edit(_status("Не удалось собрать сообщения."), parse_mode="html")

    payload = {
        "backgroundColor": background,
        "width": WIDTH,
        "height": HEIGHT,
        "scale": SCALE,
        "emojiBrand": EMOJI_BRAND,
        "messages": messages,
        "format": "png" if as_file else "webp",
        "type": QUOTE_TYPE,
    }

    await _send_rendered(event, status_message, payload, as_file)


@client.on(events.NewMessage(pattern=r"^\.(?:фц|fq)(?:\s+([\s\S]+))?$", outgoing=True))
async def fakequotecmd(event):
    raw = event.pattern_match.group(1) or ""
    reply = await event.get_reply_message()

    if raw.strip().lower() in {"help", "хелп", "?"}:
        return await event.edit(
            _status(
                "<code>.фц @user текст</code> - фейковая цитата от пользователя\n"
                "<code>.фц</code> ответом - пустая цитата от автора реплая\n"
                "<code>.фц текст</code> ответом - цитата от автора реплая с текстом\n"
                "<code>.фц @u1 текст; @u2 текст</code> - несколько сообщений\n"
                "<code>.фц @u1 текст -r @u2 ответ</code> - цитата с ответом\n\n"
                "Алиас: <code>.fq</code>\n\n"
                f"{by_line()}"
            ),
            parse_mode="html",
            link_preview=False,
        )

    if not raw and not reply:
        return await event.edit(
            _status("Нужен текст или реплай. Пример: <code>.фц @user привет</code>"),
            parse_mode="html",
        )

    status_message = await event.edit(_status("Собираю фейковую цитату..."), parse_mode="html")

    raw_html = extract_formatted_body(
        event.raw_text or event.text or "",
        event.entities,
        len((event.raw_text or event.text or "").split(maxsplit=1)[0]),
    ).strip() if raw else get_args_raw(event)

    try:
        messages = await _fake_messages(raw_html, reply)
    except Exception as e:
        return await status_message.edit(
            _status(f"Ошибка разбора аргументов: <code>{html(str(e))}</code>"),
            parse_mode="html",
        )

    if not messages:
        return await status_message.edit(_status("Не удалось собрать фейковую цитату."), parse_mode="html")
    if len(messages) > MAX_MESSAGES:
        return await status_message.edit(
            _status(f"Слишком много сообщений. Максимум: <code>{MAX_MESSAGES}</code>"),
            parse_mode="html",
        )

    payload = {
        "backgroundColor": BG_COLOR,
        "width": WIDTH,
        "height": HEIGHT,
        "scale": SCALE,
        "emojiBrand": EMOJI_BRAND,
        "messages": messages,
        "format": "webp",
        "type": QUOTE_TYPE,
    }

    await _send_rendered(event, status_message, payload, False)
