"""
Auto-Chat (AC) — ИИ отвечает в стиле владельца бота.
"""
import asyncio
import state
from ai import or_chat, or_request


def fname_or_me(me) -> str:
    return getattr(me, "first_name", None) or getattr(me, "username", None) or "Пользователь"


async def build_ac_system(chat_id: int) -> str:
    from bot_client import client
    me = await client.get_me()
    my_messages = []
    try:
        async for msg in client.iter_messages(chat_id, limit=60):
            if msg.out and msg.text and len(msg.text) > 5:
                my_messages.append(msg.text[:200])
                if len(my_messages) >= 30:
                    break
    except Exception:
        pass
    my_messages.reverse()
    style_sample = "\n".join(my_messages[:20]) if my_messages else "(нет примеров)"
    return (
        f"Ты — {fname_or_me(me)}. Ты общаешься в Telegram. "
        f"Твой стиль общения основан на этих примерах:\n\n{style_sample}\n\n"
        "Отвечай В ТОЧНОСТИ в том же стиле, тоне и формате. "
        "Не выходи из образа. Отвечай коротко как в мессенджере. "
        "НЕ раскрывай что ты ИИ."
    )


async def handle_ac(event):
    from bot_client import client
    msg       = event.message
    chat_id   = msg.chat_id
    user_text = msg.text or "[медиафайл]"

    history = state.ac_history.get(chat_id)
    if history is None:
        system  = await build_ac_system(chat_id)
        history = [{"role": "system", "content": system}]
        state.ac_history[chat_id] = history

    history.append({"role": "user", "content": user_text})
    try:
        reply_text = await or_chat(history, max_tokens=120)
        history.append({"role": "assistant", "content": reply_text})
        while len(history) > 41:
            del history[1]
        await asyncio.sleep(1.0)
        await client.send_message(chat_id, reply_text)
    except Exception as e:
        print(f"[AC] ❌ {e}")
