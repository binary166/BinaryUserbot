from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.local.json"

# The updater reads this line directly. Keep the simple assignment format.
BOT_VERSION = "v2.0"


_DEFAULTS: dict[str, Any] = {
    "API_ID": 0,
    "API_HASH": "",
    "PHONE": "",
    "PASSWORD_2FA": "",
    "MY_ID": 0,
    "CREATOR_ID": 0,
    "OR_TOKEN": "",
    "OR_MODEL": "openai/gpt-4o-mini",
    "OR_API_URL": "https://openrouter.ai/api/v1/chat/completions",
    "SCAM_CHANNEL": "GID_ScamBase",
    "SESSION_NAME": "binaryuserbot_session",
    "NOTES_FILE": "notes.json",
    "NEWS_CHANNEL": 0,
    "FUNSTAT_TOKEN": "",
    "WALLET_SEED": "",
    "BW_CHAT_ID_DEFAULT": 0,
    "CHANNEL_TO_CHAT": {},
    "STARS_BOT_ID": 0,
    "STARS_CHAT_ID": 0,
    "STARS_TIMER_SEC": 5,
}


def _read_local_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Cannot parse {CONFIG_PATH.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{CONFIG_PATH.name} must contain a JSON object.")
    return data


_LOCAL_CONFIG = {**_DEFAULTS, **_read_local_config()}


def _value(key: str, default: Any = None) -> Any:
    env_value = os.getenv(f"BINARY_{key}")
    if env_value is not None:
        return env_value
    return _LOCAL_CONFIG.get(key, default)


def _str_value(key: str, default: str = "") -> str:
    value = _value(key, default)
    return default if value is None else str(value)


def _int_value(key: str, default: int = 0) -> int:
    value = _value(key, default)
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _path_value(key: str, default: str) -> str:
    raw = Path(_str_value(key, default)).expanduser()
    if not raw.is_absolute():
        raw = BASE_DIR / raw
    return str(raw)


def _int_mapping_value(key: str) -> dict[int, int]:
    raw = _value(key, {})
    if not isinstance(raw, dict):
        return {}
    result: dict[int, int] = {}
    for source, target in raw.items():
        try:
            result[int(source)] = int(target)
        except (TypeError, ValueError):
            continue
    return result


API_ID = _int_value("API_ID")
API_HASH = _str_value("API_HASH")
PHONE = _str_value("PHONE")
PASSWORD_2FA = _str_value("PASSWORD_2FA")

MY_ID = _int_value("MY_ID")
CREATOR_ID = _int_value("CREATOR_ID", MY_ID) or MY_ID

OR_TOKEN = _str_value("OR_TOKEN")
OR_MODEL = _str_value("OR_MODEL", "openai/gpt-4o-mini")
OR_API_URL = _str_value("OR_API_URL", "https://openrouter.ai/api/v1/chat/completions")

SCAM_CHANNEL = _str_value("SCAM_CHANNEL", "GID_ScamBase")
SESSION_NAME = _str_value("SESSION_NAME", "binaryuserbot_session")
NOTES_FILE = _path_value("NOTES_FILE", "notes.json")
NEWS_CHANNEL = _int_value("NEWS_CHANNEL")
FUNSTAT_TOKEN = _str_value("FUNSTAT_TOKEN")
WALLET_SEED = _str_value("WALLET_SEED")

BW_CHAT_ID_DEFAULT = _int_value("BW_CHAT_ID_DEFAULT")
CHANNEL_TO_CHAT = _int_mapping_value("CHANNEL_TO_CHAT")

STARS_BOT_ID = _int_value("STARS_BOT_ID")
STARS_CHAT_ID = _int_value("STARS_CHAT_ID")
STARS_TIMER_SEC = max(1, _int_value("STARS_TIMER_SEC", 5))

BOT_NAME = "Binary Userbot"

CHECK_PING = "⚙️ #binary_ping_check"
CHECK_PONG = "⚙️ #binary_pong:"

LOADING = '<tg-emoji emoji-id="5846038049972031131">⏳</tg-emoji> Загружаю...'

EBALAJ_LIMIT = 50

EBALAJ_SYSTEM = _str_value(
    "EBALAJ_SYSTEM",
    (
        "Ты отвечаешь как рассеянный собеседник. На каждое сообщение давай короткую, "
        "нелепую и безобидную реплику до 8 слов. Без объяснений, списков и признаний, "
        "что ты бот или ИИ."
    ),
)

TROLL_SYSTEM = _str_value(
    "TROLL_SYSTEM",
    (
        "Ты отвечаешь резко и иронично, но без угроз, травли и оскорблений по личным "
        "или защищённым признакам. Одна короткая фраза до 10 слов. Без объяснений."
    ),
)

WMO_CODES = {
    0: "☀️ Ясно",
    1: "🌤 Преимущественно ясно",
    2: "⛅ Переменная облачность",
    3: "☁️ Пасмурно",
    45: "🌫 Туман",
    48: "🌫 Изморозь",
    51: "🌦 Слабая морось",
    53: "🌦 Морось",
    55: "🌧 Сильная морось",
    61: "🌧 Слабый дождь",
    63: "🌧 Дождь",
    65: "🌧 Сильный дождь",
    71: "🌨 Слабый снег",
    73: "🌨 Снег",
    75: "❄️ Сильный снег",
    80: "🌦 Ливень",
    81: "🌦 Ливни",
    82: "⛈ Сильный ливень",
    95: "⛈ Гроза",
    96: "⛈ Гроза с градом",
    99: "⛈ Гроза с крупным градом",
}

PROXY_TEXT = (
    '<tg-emoji emoji-id="5258073068852485953">✈️</tg-emoji> '
    "<b>Бесплатные MTProto прокси для Telegram</b>\n\n"
    '<tg-emoji emoji-id="5274008024585871702">➕</tg-emoji> <b>Сервер 1</b>\n'
    "<code>tg://proxy?server=quackton.life&port=443&secret=ee65fc7553a1f5ca8b50b71c015b38722479616e6465782e7275</code>\n"
    '<tg-emoji emoji-id="5274008024585871702">➕</tg-emoji> <b>Сервер 2</b>\n'
    "<code>tg://proxy?server=mtproto.online&port=443&secret=ee139e0ee36150c1ea3bf299796586b5457777772e7674622e7275</code>\n"
    '<tg-emoji emoji-id="5274008024585871702">➕</tg-emoji> <b>Сервер 3</b>\n'
    "<code>tg://proxy?server=dog.mtproto.online&port=443&secret=eed41d8cd98f00b204e9800998ecf8322e7777772e676c6f676c652e636f6d</code>\n"
)


def missing_required_values() -> list[str]:
    missing = []
    for key in ("API_ID", "API_HASH", "PHONE", "MY_ID"):
        value = globals().get(key)
        if value in (0, "", None):
            missing.append(key)
    return missing
