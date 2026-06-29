import json
import re
from pathlib import Path

from ai import or_request


def strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    fence = re.search(r"```(?:python|py)?\s*([\s\S]+?)```", text, re.I)
    if fence:
        return fence.group(1).strip()
    return text.strip()


def safe_filename(name: str) -> str:
    name = (name or "").strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w.\-]", "_", name, flags=re.U)
    if not name:
        name = "generated_module.py"
    if not name.endswith(".py"):
        name += ".py"
    return name


def parse_generated_meta(code: str) -> dict:
    meta = {"name": "Generated Module", "cmd": ".generated", "desc": "AI generated BinaryUserbot module"}
    for key, field in (("MODULE_NAME", "name"), ("MODULE_CMD", "cmd"), ("MODULE_DESC", "desc")):
        m = re.search(rf"#\s*{key}\s*=\s*['\"](.+?)['\"]", code or "", re.I)
        if m:
            meta[field] = m.group(1).strip()
    if not meta["cmd"].startswith("."):
        meta["cmd"] = "." + meta["cmd"]
    return meta


def filename_from_code(code: str, fallback: str = "generated_module.py") -> str:
    meta = parse_generated_meta(code)
    cmd = (meta.get("cmd") or "").lstrip(".")
    if cmd:
        return safe_filename(f"{cmd}.py")
    return safe_filename(fallback)


def ensure_binary_header(code: str, source_name: str = "module.py") -> str:
    code = strip_code_fence(code)
    meta = parse_generated_meta(code)
    if "# MODULE_NAME" not in code[:700]:
        stem = Path(source_name).stem or "Generated Module"
        cmd_stem = re.sub(r"[^\w]", "_", stem.lower(), flags=re.U)
        header = (
            f'# MODULE_NAME = "{stem}"\n'
            f'# MODULE_CMD  = ".{cmd_stem}"\n'
            f'# MODULE_DESC = "BinaryUserbot module"\n\n'
        )
        code = header + code.lstrip()
    return code.strip() + "\n"


async def assess_native_support_with_ai(source: str, filename: str) -> tuple[bool, str]:
    source = (source or "")[:18000]
    system = """
Ты проверяешь, сможет ли Binary Userbot загрузить модуль без переписывания.

Нативно поддерживается:
- Binary-модули с @client.on(events.NewMessage(...)) и импортом from bot_client import client.
- Простые Heroku/Hikka/FTG-модули формата loader.Module.
- @loader.command, alias/aliases, методы вида somethingcmd.
- utils.answer, utils.get_args_raw, utils.run_sync, loader.ModuleConfig, loader.ConfigValue.
- client_ready(client, db) и @loader.loop(..., autostart=True) в базовом виде.

Не поддерживается нативно:
- inline-кнопки/inline bot, callback_handler, inline_handler как реальная inline-логика.
- сложная база Heroku/Hikka, allmodules, security, веб-панели, внешние сервисы Heroku.
- плагины, где логика зависит от отсутствующих сторонних библиотек.
- код с несовместимыми импортами userbot/borg/catub/ultroid без loader.Module.

Ответь строго JSON без markdown:
{"native": true/false, "reason": "короткая причина"}
""".strip()
    user = f"Файл: {filename}\n\n```python\n{source}\n```"
    try:
        raw = await or_request(system, user, max_tokens=300)
        match = re.search(r"\{[\s\S]*\}", raw)
        data = json.loads(match.group(0) if match else raw)
        return bool(data.get("native")), str(data.get("reason") or "")
    except Exception as e:
        return False, f"AI check failed: {e}"


async def convert_module_with_ai(source: str, original_filename: str, native_error: str = "") -> tuple[str, str]:
    source = strip_code_fence(source)
    system = """
Ты конвертер Telegram userbot-модулей в формат BinaryUserbot.

Сделай рабочий Python-файл. Требования:
- В самом начале обязательно добавь:
  # MODULE_NAME = "..."
  # MODULE_CMD  = ".команда"
  # MODULE_DESC = "..."
- Используй Telethon и глобальный клиент Binary:
  from telethon import events
  from bot_client import client
  from utils import html
- Хендлеры команд регистрируй так:
  @client.on(events.NewMessage(pattern=r"^\\.cmd(?:\\s+([\\s\\S]+))?$", outgoing=True))
- Ответы делай через event.edit(..., parse_mode="html") или client.send_message/send_file.
- Для аргументов используй event.pattern_match.group(1) или raw_text.
- Для reply используй await event.get_reply_message().
- Если нужен state/settings/premium_emoji/config/ai, импортируй их из BinaryUserbot.
- Не используй loader.Module, utils.answer, userbot, borg, bot, catub, friday, ultroid, Config, CMD_HELP.
- Не оставляй markdown, комментарии о конвертации и объяснения.
- Сохрани основную идею и команды исходного модуля, но убери несовместимые куски.
- Не добавляй опасные действия: кражу сессий/токенов, скрытые автозапуски, удаление файлов вне временных файлов.

Верни только Python-код.
""".strip()
    user = f"""
Имя файла: {original_filename}
Ошибка нативной загрузки, если была: {native_error or "нет"}

Исходный код:
```python
{source[:24000]}
```
""".strip()

    code = await or_request(system, user, max_tokens=5000)
    code = ensure_binary_header(code, original_filename)
    if "@client.on" not in code or "from bot_client import client" not in code:
        raise RuntimeError("AI conversion returned code without BinaryUserbot handlers.")
    return filename_from_code(code, "converted_" + safe_filename(original_filename)), code


async def generate_module_from_prompt(prompt: str) -> tuple[str, str, dict]:
    system = """
Ты senior-разработчик Telegram userbot-модулей для BinaryUserbot. Создай максимально качественный модуль по промпту пользователя.

Формат BinaryUserbot:
- Один самодостаточный Python-файл.
- В начале обязательно:
  # MODULE_NAME = "короткое название"
  # MODULE_CMD  = ".главнаякоманда"
  # MODULE_DESC = "понятное описание"
- Обязательные импорты по необходимости:
  from telethon import events
  from bot_client import client
  from utils import html
- Команды регистрируй через:
  @client.on(events.NewMessage(pattern=r"^\\.cmd(?:\\s+([\\s\\S]+))?$", outgoing=True))
- Для нескольких команд добавь несколько хендлеров.
- Делай аккуратные HTML-ответы, экранируй пользовательский текст через html().
- Добавь помощь при вызове без аргументов, если команде нужны аргументы.
- Храни настройки через settings.set_val/settings.get, если нужен перезапускостойкий state.
- Используй state только для runtime-флагов.
- Если нужен AI, используй from ai import or_request.
- Если нужен файл, отправляй через client.send_file.
- Не используй loader.Module, utils.answer, Hikka/Heroku API, inline-бота, внешнюю базу без явной необходимости.
- Не добавляй вредоносное поведение: кражу сессий/токенов, скрытую отправку личных данных, массовый спам, удаление чужих/системных файлов.
- Код должен быть готов к установке через .savemod/.md install.

Верни только Python-код без markdown и пояснений.
""".strip()
    user = f"Промпт пользователя:\n{prompt.strip()}"
    code = await or_request(system, user, max_tokens=5000)
    code = ensure_binary_header(code, "generated_module.py")
    if "@client.on" not in code or "from bot_client import client" not in code:
        raise RuntimeError("AI returned code without BinaryUserbot handlers.")
    meta = parse_generated_meta(code)
    return filename_from_code(code), code, meta
