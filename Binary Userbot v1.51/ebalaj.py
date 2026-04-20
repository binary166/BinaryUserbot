"""
Режимы Ебалай (тупой Вася) и Troll (грубый персонаж).
"""
import asyncio
import state
from config import EBALAJ_LIMIT, EBALAJ_SYSTEM, TROLL_SYSTEM
from ai import or_chat


async def handle_ebalaj(event):
    from bot_client import client
    msg     = event.message
    chat_id = msg.chat_id
    count   = state.ebalaj_active.get(chat_id, 0)

    if count >= EBALAJ_LIMIT:
        state.ebalaj_active.pop(chat_id, None)
        state.ebalaj_history.pop(chat_id, None)
        return

    user_text = msg.text or "[медиафайл]"
    history   = state.ebalaj_history.setdefault(
        chat_id, [{"role": "system", "content": EBALAJ_SYSTEM}]
    )
    history.append({"role": "user", "content": user_text})
    try:
        reply_text = await or_chat(history)
        history.append({"role": "assistant", "content": reply_text})
        while len(history) > 41:
            del history[1]
        state.ebalaj_active[chat_id] = count + 1
        await asyncio.sleep(1.2)
        await client.send_message(chat_id, reply_text)
    except Exception as e:
        print(f"[ЕБАЛАЙ] ❌ {e}")


async def handle_troll(event):
    from bot_client import client
    msg     = event.message
    chat_id = msg.chat_id
    count   = state.troll_active.get(chat_id, 0)

    if count >= EBALAJ_LIMIT:
        state.troll_active.pop(chat_id, None)
        state.troll_history.pop(chat_id, None)
        return

    user_text = msg.text or "[медиафайл]"
    history   = state.troll_history.setdefault(
        chat_id, [{"role": "system", "content": TROLL_SYSTEM}]
    )
    history.append({"role": "user", "content": user_text})
    try:
        reply_text = await or_chat(history)
        history.append({"role": "assistant", "content": reply_text})
        while len(history) > 41:
            del history[1]
        state.troll_active[chat_id] = count + 1
        await asyncio.sleep(0.8)
        await client.send_message(chat_id, reply_text)
    except Exception as e:
        print(f"[TROLL] ❌ {e}")
