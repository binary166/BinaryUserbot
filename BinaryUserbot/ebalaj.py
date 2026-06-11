import asyncio
import hashlib
import state
import settings
from config import EBALAJ_LIMIT, EBALAJ_SYSTEM, TROLL_SYSTEM
from ai import or_chat


EBALAJ_FALLBACKS = [
    "а чё вообще происходит",
    "я не понял и не хочу",
    "это куда вообще тыкать",
    "логика где-то потерялась",
    "мозг уехал в отпуск",
    "подожди, я туплю страшно",
    "что-то совсем мимо темы",
    "я завис и норм",
]

TROLL_FALLBACKS = [
    "Ну и чушь ты выдал.",
    "Бред, даже читать лень.",
    "Ты вообще думал перед этим?",
    "Тупой текст, соберись.",
    "Мусорная мысль, не более.",
    "Дрянь, а не сообщение.",
    "Идиотский набор слов.",
    "Херня уровня пола.",
]

TROLL_MARKERS = (
    "чуш", "бред", "туп", "херн", "идиот", "мусор", "дрян", "дичь",
    "фигн", "ерунд", "позор", "клоун", "гений", "лох", "дурак",
)

EBALAJ_DUMB_MARKERS = (
    "чё", "че", "што", "зачем", "куда", "не понял", "не пойму", "наоборот",
    "завис", "туп", "мозг", "мысл", "кругл", "хлеб", "антенн", "мимо",
    "ээ", "ну", "подожди", "потерял", "куда ты", "что это",
)

EBALAJ_NORMAL_MARKERS = (
    "думаю", "считаю", "можно", "нужно", "рекомендую", "советую", "предлагаю",
    "попробуйте", "попробуй", "возможно", "вероятно", "скорее", "логично",
    "потому", "поэтому", "если", "объясню", "сделайте", "сделай",
)

TROLL_SOFT_MARKERS = (
    "думаю", "считаю", "можно", "нужно", "возможно", "скорее", "кажется",
    "советую", "рекомендую", "попробуй", "попробуйте", "не совсем",
)

TROLL_AGGRESSIVE_MARKERS = (
    "чуш", "бред", "туп", "хер", "идиот", "мусор", "дрян", "дичь",
    "фигн", "ерунд", "позор", "дурак", "лох", "клоун", "жалк",
)


def _pick_fallback(items: list[str], chat_id: int, count: int, text: str) -> str:
    seed = f"{chat_id}:{count}:{text}".encode("utf-8", errors="ignore")
    digest = hashlib.blake2s(seed, digest_size=2).digest()
    index = int.from_bytes(digest, "big") % len(items)
    return items[index]


def _shorten(text: str, max_words: int, max_chars: int) -> str:
    clean = " ".join((text or "").replace("\n", " ").split()).strip(" \"'`")
    if not clean:
        return ""
    words = clean.split()
    if len(words) > max_words:
        clean = " ".join(words[:max_words])
    return clean[:max_chars].strip()


def _ensure_mode_history(store: dict, chat_id: int, system_text: str) -> list[dict]:
    history = store.get(chat_id)
    if not isinstance(history, list) or not history:
        history = [{"role": "system", "content": system_text}]
        store[chat_id] = history
        return history

    first = history[0] if history else None
    if not isinstance(first, dict) or first.get("role") != "system" or first.get("content") != system_text:
        history = [{"role": "system", "content": system_text}]
        store[chat_id] = history
    return history


def _current_prompt(key: str, default: str) -> tuple[str, bool]:
    value = settings.get(key)
    value = str(value).strip() if value else ""
    return (value, True) if value else (default, False)


def _force_troll(text: str, fallback: str) -> str:
    clean = _shorten(text, max_words=10, max_chars=120)
    low = clean.lower()
    if not clean:
        return fallback
    if any(marker in low for marker in TROLL_SOFT_MARKERS):
        return fallback
    if not any(marker in low for marker in TROLL_AGGRESSIVE_MARKERS):
        return fallback
    return clean.lower()


def _force_ebalaj(text: str, fallback: str) -> str:
    clean = _shorten(text, max_words=8, max_chars=90)
    low = clean.lower()
    if not clean:
        return fallback
    if any(marker in low for marker in EBALAJ_NORMAL_MARKERS):
        return fallback
    if not any(marker in low for marker in EBALAJ_DUMB_MARKERS):
        return fallback
    return clean.lower()


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
    system_prompt, custom_prompt = _current_prompt("ebalaj_system_prompt", EBALAJ_SYSTEM)
    history   = _ensure_mode_history(state.ebalaj_history, chat_id, system_prompt)
    history.append({"role": "user", "content": user_text})
    try:
        fallback = _pick_fallback(EBALAJ_FALLBACKS, chat_id, count, user_text)
        reply_text = await asyncio.wait_for(or_chat(history, max_tokens=20), timeout=12)
        reply_text = (_shorten(reply_text, max_words=24, max_chars=220) or fallback) if custom_prompt else _force_ebalaj(reply_text, fallback)
        history.append({"role": "assistant", "content": reply_text})
        while len(history) > 41:
            del history[1]
        state.ebalaj_active[chat_id] = count + 1
        await asyncio.sleep(1.2)
        await client.send_message(chat_id, reply_text, reply_to=msg.id)
    except Exception as e:
        reply_text = _pick_fallback(EBALAJ_FALLBACKS, chat_id, count, user_text)
        state.ebalaj_active[chat_id] = count + 1
        try:
            await client.send_message(chat_id, reply_text, reply_to=msg.id)
        except Exception:
            pass
        print(f"[EBALAJ] {e}")


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
    system_prompt, custom_prompt = _current_prompt("troll_system_prompt", TROLL_SYSTEM)
    history   = _ensure_mode_history(state.troll_history, chat_id, system_prompt)
    history.append({"role": "user", "content": user_text})
    try:
        fallback = _pick_fallback(TROLL_FALLBACKS, chat_id, count, user_text)
        reply_text = await asyncio.wait_for(or_chat(history, max_tokens=20), timeout=12)
        reply_text = (_shorten(reply_text, max_words=24, max_chars=220) or fallback) if custom_prompt else _force_troll(reply_text, fallback)
        history.append({"role": "assistant", "content": reply_text})
        while len(history) > 41:
            del history[1]
        state.troll_active[chat_id] = count + 1
        await asyncio.sleep(0.8)
        await client.send_message(chat_id, reply_text, reply_to=msg.id)
    except Exception as e:
        reply_text = _pick_fallback(TROLL_FALLBACKS, chat_id, count, user_text)
        state.troll_active[chat_id] = count + 1
        try:
            await client.send_message(chat_id, reply_text, reply_to=msg.id)
        except Exception:
            pass
        print(f"[TROLL] {e}")
