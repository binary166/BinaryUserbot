"""
Постоянное хранилище настроек бота (settings.json).
Все настройки из .setting сохраняются между перезапусками.
"""
import json
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent / "settings.json"

_DEFAULTS: dict = {
    "eng_mode_active":        False,
    "premium_emoji_active":   True,
    "logs_chat_id":           None,
    "bw_words":               [],
    "bw_chat_id":             0,
    "auto_comment_channels":  {},
}

_data: dict = {}


def load(default_logs_id: int, default_bw_chat_id: int = 0) -> None:
    """Загружает settings.json; незнакомые ключи заполняются дефолтами."""
    global _data
    if SETTINGS_FILE.exists():
        try:
            _data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[SETTINGS] Ошибка чтения, используем дефолты: {e}")
            _data = {}
    else:
        _data = {}

    for k, v in _DEFAULTS.items():
        if k not in _data:
            _data[k] = v

    if _data["logs_chat_id"] is None:
        _data["logs_chat_id"] = default_logs_id


def save() -> None:
    """Сохраняет текущее состояние в settings.json."""
    try:
        SETTINGS_FILE.write_text(
            json.dumps(_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        print(f"[SETTINGS] Ошибка сохранения: {e}")


def get(key: str, default=None):
    return _data.get(key, default)


def set_val(key: str, value) -> None:
    """Устанавливает значение и сразу сохраняет на диск."""
    _data[key] = value
    save()


def get_auto_comment_channels() -> dict:
    """Возвращает {channel_id(int): discussion_chat_id(int)}."""
    raw = _data.get("auto_comment_channels", {})
    return {int(k): int(v) for k, v in raw.items()}


def add_auto_comment_channel(channel_id: int, discussion_id: int) -> None:
    raw = _data.get("auto_comment_channels", {})
    raw[str(channel_id)] = discussion_id
    _data["auto_comment_channels"] = raw
    save()


def remove_auto_comment_channel(channel_id: int) -> bool:
    raw = _data.get("auto_comment_channels", {})
    key = str(channel_id)
    if key not in raw:
        return False
    del raw[key]
    _data["auto_comment_channels"] = raw
    save()
    return True
