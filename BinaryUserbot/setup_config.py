from __future__ import annotations

import getpass
import json
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.local.json"


FIELDS = [
    {
        "key": "API_ID",
        "type": "int",
        "required": True,
        "title": "Telegram API_ID",
        "hint": "Число с https://my.telegram.org/apps. Без него userbot не сможет подключиться к Telegram.",
    },
    {
        "key": "API_HASH",
        "type": "str",
        "required": True,
        "secret": True,
        "title": "Telegram API_HASH",
        "hint": "Строка API hash с https://my.telegram.org/apps. Ввод скрыт, потому что это приватный ключ приложения.",
    },
    {
        "key": "PHONE",
        "type": "str",
        "required": True,
        "title": "Номер телефона",
        "hint": "Номер Telegram-аккаунта в международном формате, например +79991234567.",
    },
    {
        "key": "PASSWORD_2FA",
        "type": "str",
        "secret": True,
        "title": "Пароль 2FA",
        "hint": "Пароль облачной двухфакторной защиты Telegram. Если 2FA выключена, оставьте пустым.",
    },
    {
        "key": "MY_ID",
        "type": "int",
        "required": True,
        "title": "Ваш Telegram ID",
        "hint": "Числовой user ID владельца userbot. Можно узнать у @userinfobot.",
    },
    {
        "key": "CREATOR_ID",
        "type": "int",
        "title": "ID создателя",
        "hint": "ID, который будет отмечен как создатель в .info. Если не знаете, оставьте пустым.",
    },
    {
        "key": "SESSION_NAME",
        "type": "str",
        "default": "binaryuserbot_session",
        "title": "Имя сессии",
        "hint": "Имя локальной Telegram-сессии. Обычно лучше оставить binaryuserbot_session.",
    },
    {
        "key": "OR_TOKEN",
        "type": "str",
        "secret": True,
        "title": "OpenRouter token",
        "hint": "Токен для AI-команд. Если AI не нужен, оставьте пустым.",
    },
    {
        "key": "OR_MODEL",
        "type": "str",
        "default": "openai/gpt-4o-mini",
        "title": "OpenRouter model",
        "hint": "Модель для AI-команд. Пример: openai/gpt-4o-mini.",
    },
    {
        "key": "OR_API_URL",
        "type": "str",
        "default": "https://openrouter.ai/api/v1/chat/completions",
        "title": "OpenRouter API URL",
        "hint": "URL OpenRouter Chat Completions API. Обычно оставьте значение по умолчанию.",
    },
    {
        "key": "SCAM_CHANNEL",
        "type": "str",
        "default": "GID_ScamBase",
        "title": "Scam channel",
        "hint": "Username канала/базы для проверки скама. По умолчанию GID_ScamBase.",
    },
    {
        "key": "NEWS_CHANNEL",
        "type": "int",
        "title": "News channel ID",
        "hint": "ID канала для дайджеста новостей. Если функция не нужна, оставьте пустым.",
    },
    {
        "key": "WALLET_SEED",
        "type": "str",
        "secret": True,
        "title": "TON wallet seed",
        "hint": "Seed-фраза TON-кошелька для crypto-модуля. Оставьте пустым, если модуль не нужен.",
    },
    {
        "key": "STARS_BOT_ID",
        "type": "int",
        "title": "Stars bot ID",
        "hint": "ID бота, от которого приходят Stars-инвойсы. Нужен только для Stars AutoPay.",
    },
    {
        "key": "STARS_CHAT_ID",
        "type": "int",
        "title": "Stars chat ID",
        "hint": "ID чата, где отслеживать Stars-инвойсы. Нужен только для Stars AutoPay.",
    },
    {
        "key": "STARS_TIMER_SEC",
        "type": "int",
        "default": 5,
        "title": "Stars timer",
        "hint": "Сколько секунд ждать перед автооплатой Stars-инвойса. По умолчанию 5.",
    },
]


def _load_existing() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Не удалось прочитать {CONFIG_PATH.name}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{CONFIG_PATH.name} должен быть JSON-объектом.")
    return data


def _masked(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    if len(text) <= 6:
        return "*" * len(text)
    return f"{text[:2]}{'*' * (len(text) - 4)}{text[-2:]}"


def _convert_value(raw: str, field: dict[str, Any]) -> Any:
    if field.get("type") != "int":
        return raw
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError:
        raise ValueError("нужно ввести целое число")


def _ask_field(field: dict[str, Any], existing: dict[str, Any]) -> Any:
    key = field["key"]
    current = existing.get(key, field.get("default", ""))
    required = bool(field.get("required"))

    while True:
        print(f"\n{field['title']} ({key})")
        print(field["hint"])
        if current not in ("", None, 0):
            shown = _masked(current) if field.get("secret") else current
            print(f"Текущее значение: {shown}")
        elif "default" in field:
            print(f"По умолчанию: {field['default']}")
        prompt = "Введите значение"
        if not required:
            prompt += " или Enter, чтобы пропустить"
        prompt += ": "

        raw = getpass.getpass(prompt) if field.get("secret") else input(prompt)
        raw = raw.strip()
        if not raw and current not in ("", None):
            return current
        if not raw and "default" in field:
            return field["default"]
        if not raw and not required:
            return "" if field.get("type") != "int" else 0
        if not raw and required:
            print("Это обязательное поле.")
            continue

        try:
            return _convert_value(raw, field)
        except ValueError as exc:
            print(f"Ошибка: {exc}")


def _ask_channel_mapping(existing: dict[str, Any]) -> dict[str, int]:
    current = existing.get("CHANNEL_TO_CHAT", {})
    if not isinstance(current, dict):
        current = {}

    print("\nАвтокомментарии (CHANNEL_TO_CHAT)")
    print("Введите пары канал:чат через запятую. Пример: -100123:-100456, -100777:-100888")
    print("Если автокомментарии не нужны, оставьте пустым.")
    if current:
        print(f"Текущее значение: {json.dumps(current, ensure_ascii=False)}")

    raw = input("Пары канал:чат или Enter, чтобы оставить как есть: ").strip()
    if not raw:
        return {str(k): int(v) for k, v in current.items()}
    if raw in {"-", "none", "нет", "no"}:
        return {}

    result: dict[str, int] = {}
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        if ":" not in item:
            print(f"Пропускаю {item}: нет двоеточия.")
            continue
        source, target = [part.strip() for part in item.split(":", 1)]
        try:
            result[str(int(source))] = int(target)
        except ValueError:
            print(f"Пропускаю {item}: ID должны быть числами.")
    return result


def main() -> None:
    existing = _load_existing()
    result: dict[str, Any] = {}

    print("Binary Userbot v2.0 — мастер настройки")
    print("Все приватные значения будут сохранены локально в config.local.json.")

    for field in FIELDS:
        value = _ask_field(field, existing)
        if value not in ("", None, 0) or field.get("required") or "default" in field:
            result[field["key"]] = value

    result["CHANNEL_TO_CHAT"] = _ask_channel_mapping(existing)

    CONFIG_PATH.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(CONFIG_PATH, 0o600)
    except OSError:
        pass

    print(f"\nГотово: {CONFIG_PATH.name} создан.")
    print("Следующий шаг: python main.py")


if __name__ == "__main__":
    main()
