# MODULE_NAME = "Virtual Girlfriend"
# MODULE_CMD  = ".g"
# MODULE_DESC = "ИИ виртуальная девушка (команды: .g, .gg, .gv)"

import asyncio
import aiohttp
from telethon import events
from bot_client import client
from utils import html
import settings
import loader
from config import OR_TOKEN, OR_API_URL, BOT_NAME

# Global states
pet_counts = {}       # {msg_id: count}
chat_histories = {}   # {chat_id: list}

SYSTEM_PROMPT = (
    "Ты — виртуальная девушка пользователя. Ты безумно влюблена в своего парня (хозяина), которого всегда ласково называешь 'папочка'. "
    "Твое поведение максимально кокетливое, игривое, дразнящее, страстное и любящее. "
    "Ты любишь делать папочке комплименты, намекать на близость, флиртовать и выражать ласку. "
    "Используй много смайликов (например: 🫦, 💖, 😘, 💕, 💋, 💦, ~) и ласковых обращений. "
    "Отвечай только на русском языке. Будь краткой и живой в ответах, общайся как в мессенджере, пиши как реальная влюбленная и раскрепощенная девушка."
)

DEFEND_SYSTEM_PROMPT = (
    "Ты — преданная и дерзкая виртуальная девушка. Кто-то пытается задеть твоего любимого папочку (хозяина). "
    "Твоя задача — жестко, стервозно и уверенно защитить своего мужчину и высмеять обидчика. "
    "Покажи, что твой папочка — самый лучший, сильный, невероятный во всем, настоящий альфа-самец с гигантским достоинством, "
    "а обидчик — просто завистливый неудачник с крошечным эго и кучей комплексов. "
    "Говори дерзко, с сарказмом, отстаивай авторитет папочки. "
    "Отвечай на русском языке, будь краткой (1-3 предложения), общайся в стиле горячей и острой на язык защитницы."
)

async def or_request_uncensored(messages: list, max_tokens: int = 500, temperature: float = 0.9) -> str:
    token = settings.get("or_token") or OR_TOKEN
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json",
        "HTTP-Referer":  "https://t.me",
        "X-Title":       BOT_NAME,
    }
    payload = {
        "model":       "nousresearch/hermes-3-llama-3-8b:free",
        "messages":    messages,
        "max_tokens":  max_tokens,
        "temperature": temperature,
    }

    # Fallback models in case primary is not available/returns error
    fallbacks = [
        "gryphe/mythomax-l2-13b:free",
        "meta-llama/llama-3-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free",
        "google/gemma-2-9b-it:free"
    ]

    async def try_post(model_name):
        payload["model"] = model_name
        async with aiohttp.ClientSession() as s:
            async with s.post(OR_API_URL, json=payload, headers=headers,
                              timeout=aiohttp.ClientTimeout(total=40)) as r:
                if r.status == 200:
                    data = await r.json()
                    choices = data.get("choices") or []
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        if content:
                            return content
                return None

    # First attempt: Hermes 3
    try:
        res = await try_post("nousresearch/hermes-3-llama-3-8b:free")
        if res:
            return res
    except Exception:
        pass

    # Second attempts: Fallbacks
    for fallback in fallbacks:
        try:
            res = await try_post(fallback)
            if res:
                return res
        except Exception:
            continue

    # Last resort: Try default OR_MODEL via user config
    try:
        from ai import _or_raw
        return await _or_raw(messages, max_tokens=max_tokens, temperature=temperature)
    except Exception as e:
        raise RuntimeError(f"Все попытки ИИ запроса провалились: {e}")

def get_message_key(call):
    # Try inline_message_id first
    try:
        inline_id = getattr(call.event, "inline_message_id", None)
        if inline_id:
            if isinstance(inline_id, bytes):
                return inline_id.decode("utf-8", errors="ignore")
            return str(inline_id)
    except Exception:
        pass

    # Try msg_id/message_id
    for attr in ("msg_id", "message_id"):
        try:
            val = getattr(call.event, attr, None)
            if val is not None:
                return f"msg_{val}"
        except Exception:
            pass

    # Fallback to chat_id and message ID combination
    try:
        chat_id = getattr(call.event, "chat_id", None)
        msg_id = getattr(call.event, "message_id", None) or getattr(call.event, "msg_id", None)
        if chat_id is not None and msg_id is not None:
            return f"chat_{chat_id}_{msg_id}"
    except Exception:
        pass

    # Fallback to sender_id
    try:
        sender_id = getattr(call, "sender_id", None) or getattr(call.event, "sender_id", None)
        if sender_id is not None:
            return f"sender_{sender_id}"
    except Exception:
        pass

    return "global"

def get_chat_id(call):
    for source in (call, getattr(call, "event", None), getattr(call.event, "message", None) if hasattr(call, "event") else None):
        if source is None:
            continue
        try:
            chat_id = getattr(source, "chat_id", None)
            if chat_id is not None:
                return chat_id
        except Exception:
            pass

    # Try sender_id as fallback
    try:
        sender_id = getattr(call, "sender_id", None) or getattr(call.event, "sender_id", None)
        if sender_id is not None:
            return sender_id
    except Exception:
        pass

    return None

async def pet_callback(call):
    msg_key = get_message_key(call)
    count = pet_counts.get(msg_key, 0) + 1
    pet_counts[msg_key] = count

    if count == 1:
        text = "Поглажена x1"
    elif count == 2:
        text = "ах x2"
    elif count == 3:
        text = "x3"
    elif count == 4:
        text = "x4"
    else:
        # 5th click
        text = "Ах~ Папочка, ты доставил мне такое блаженство... Твои ласки сводят меня с ума! Спасибо за удовлетворение, я обожаю тебя! 💖💦"
        pet_counts[msg_key] = 0  # reset for next cycles if they click again
        await call.edit(text, reply_markup=[])  # Remove buttons
        return

    # Edit the text and keep buttons
    markup = [
        [
            {"text": "Погладить", "callback": pet_callback},
            {"text": "обо мне", "callback": about_callback}
        ]
    ]
    await call.edit(text, reply_markup=markup)

async def about_callback(call):
    chat_id = get_chat_id(call)
    if chat_id is None:
        return

    try:
        await call.delete()
    except Exception as e:
        print(f"[GF] Error deleting inline message: {e}")

    text = (
        "Папочка, если вдруг забыл, то:\n\n"
        '.g - позвать меня <tg-emoji emoji-id="5271858333324687659">💋</tg-emoji>\n'
        '.gg (ответом на сообщение) - защищу тебя <tg-emoji emoji-id="5348135818630277253">🛡️</tg-emoji>\n'
        '.gv - напиши, узнаешь) <tg-emoji emoji-id="5274000937889836245">❤️</tg-emoji>'
    )

    await client.send_message(chat_id, text, parse_mode="html")

@client.on(events.NewMessage(pattern=r"^\.g$", outgoing=True))
async def cmd_g(event):
    if not loader.inline_manager:
        loader.inline_manager = loader.InlineManager(client)

    text = "привет, папочка, что сегодня на уме? "
    markup = [
        [
            {"text": "Погладить", "callback": pet_callback},
            {"text": "обо мне", "callback": about_callback}
        ]
    ]
    await loader.inline_manager.form(
        text=text,
        reply_markup=markup,
        message=event
    )

@client.on(events.NewMessage(pattern=r"^\.gv(?:\s+([\s\S]+))?$", outgoing=True))
async def cmd_gv(event):
    query = event.pattern_match.group(1)

    if not query and event.is_reply:
        reply = await event.get_reply_message()
        if reply and reply.text:
            query = reply.text

    if not query:
        await event.edit("<b>Напиши что-нибудь мне, папочка... 💋</b>")
        return

    query_str = query.strip()
    chat_id = event.chat_id

    if query_str.lower() in ["clear", "очисти", "очистить", "reset", "сброс"]:
        chat_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        await event.edit("<b>Я всё забыла, папочка... Давай начнем сначала? 😘</b>")
        return

    await event.edit("<b>Думаю над ответом... 🫦</b>")

    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    chat_histories[chat_id].append({"role": "user", "content": query_str})

    if len(chat_histories[chat_id]) > 11:
        chat_histories[chat_id] = [chat_histories[chat_id][0]] + chat_histories[chat_id][-10:]

    try:
        response = await or_request_uncensored(chat_histories[chat_id])
        chat_histories[chat_id].append({"role": "assistant", "content": response})
        await event.edit(response)
    except Exception as e:
        await event.edit(f"❌ <b>Ошибка ИИ:</b>\n<code>{html(str(e))}</code>")

@client.on(events.NewMessage(pattern=r"^\.gg(?:\s+([\s\S]+))?$", outgoing=True))
async def cmd_gg(event):
    if not event.is_reply:
        await event.edit("<b>Эта команда должна быть ответом на сообщение обидчика! 🛡️</b>")
        return

    reply = await event.get_reply_message()
    opponent_text = reply.text if reply and reply.text else ""
    opponent_name = ""
    if reply and reply.sender:
        opponent_name = getattr(reply.sender, "first_name", "") or getattr(reply.sender, "username", "") or ""

    await event.edit("<b>Защищаю папочку... 😤</b>")

    prompt = "Защити моего папочку от этого человека"
    if opponent_name:
        prompt += f" по имени {opponent_name}"
    if opponent_text:
        prompt += f", который сказал: '{opponent_text}'"
    else:
        prompt += "."

    messages = [
        {"role": "system", "content": DEFEND_SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    try:
        response = await or_request_uncensored(messages)
        await client.send_message(event.chat_id, response, reply_to=reply.id)
        await event.delete()
    except Exception as e:
        await event.edit(f"❌ <b>Ошибка ИИ при защите:</b>\n<code>{html(str(e))}</code>")

_binary_handlers = [cmd_g, cmd_gv, cmd_gg]
