# MODULE_NAME = "GitMD"
# MODULE_CMD  = ".md"
# MODULE_DESC = "Переписывание обычных, GitHub и Heroku/UserBot модулей под BinaryUserbot"

import io
import re
import traceback
from pathlib import Path
from urllib.parse import urlparse

import aiohttp
from telethon import events

from bot_client import client
from utils import html
from ai import or_request

try:
    from module_loader import can_try_native, install_module, install_module_smart
except Exception:
    can_try_native = None
    install_module = None
    install_module_smart = None

try:
    from premium_emoji import by_line
except Exception:
    def by_line():
        return "<i>Binary Userbot</i>"


URL_RE = re.compile(r"https?://[^\s<>()\"']+", re.I)


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    fence = re.search(r"```(?:python|py)?\s*([\s\S]+?)```", text, re.I)
    if fence:
        return fence.group(1).strip()
    return text.strip()


def _clean_url(url: str) -> str:
    return (url or "").strip().rstrip(".,);]}>\"'")


def _github_to_raw(url: str) -> str:
    url = _clean_url(url)
    if "raw.githubusercontent.com" in url:
        return url

    parsed = urlparse(url)
    if parsed.netloc.lower() == "github.com":
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 5 and parts[2] == "blob":
            user = parts[0]
            repo = parts[1]
            branch = parts[3]
            file_path = "/".join(parts[4:])
            return f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{file_path}"
    return url


def _extract_first_url(text: str) -> str | None:
    m = URL_RE.search(text or "")
    return _clean_url(m.group(0)) if m else None


def _decode_bytes(data: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", errors="ignore")


def _safe_filename(name: str) -> str:
    name = (name or "").strip().replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w.\-]", "_", name, flags=re.U)
    if not name:
        name = "converted_module.py"
    if not name.endswith(".py"):
        name += ".py"
    return name


def _guess_name_from_source(source: str, fallback: str = "Converted Module") -> str:
    patterns = [
        r"#\s*MODULE_NAME\s*=\s*['\"](.+?)['\"]",
        r"__mod_name__\s*=\s*['\"](.+?)['\"]",
        r"__module__\s*=\s*['\"](.+?)['\"]",
        r"__name__\s*=\s*['\"](.+?)['\"]",
    ]
    for pattern in patterns:
        m = re.search(pattern, source or "", re.I)
        if m:
            return m.group(1).strip()

    m = re.search(r"CMD_HELP\s*\[\s*['\"](.+?)['\"]\s*\]", source or "", re.I)
    if m:
        return m.group(1).strip().title()
    return fallback


def _guess_cmd_from_source(source: str, fallback: str = ".mod") -> str:
    source = source or ""
    patterns = [
        r"#\s*MODULE_CMD\s*=\s*['\"](.+?)['\"]",
        r"admin_cmd\s*\(\s*pattern\s*=\s*r?['\"]\.?([a-zA-Zа-яА-Я0-9_]+)",
        r"sudo_cmd\s*\(\s*pattern\s*=\s*r?['\"]\.?([a-zA-Zа-яА-Я0-9_]+)",
        r"register\s*\([^)]*pattern\s*=\s*r?['\"]\^?\\?\.?([a-zA-Zа-яА-Я0-9_]+)",
        r"NewMessage\s*\([^)]*pattern\s*=\s*r?['\"]\^?\\?\.?([a-zA-Zа-яА-Я0-9_]+)",
        r"async\s+def\s+([a-zA-Zа-яА-Я0-9_]+)cmd\s*\(",
    ]
    for pattern in patterns:
        m = re.search(pattern, source, re.I)
        if m and m.lastindex:
            cmd = m.group(1).strip().lower()
            cmd = re.sub(r"[^\wа-яА-Я]", "", cmd)
            if cmd:
                return "." + cmd.lstrip(".")
    return fallback if fallback.startswith(".") else "." + fallback


def _parse_converted_meta(code: str) -> dict:
    meta = {
        "name": _guess_name_from_source(code, "Converted Module"),
        "cmd": _guess_cmd_from_source(code, ".mod"),
        "desc": "Модуль, переписанный через GitMD",
    }
    m = re.search(r"#\s*MODULE_DESC\s*=\s*['\"](.+?)['\"]", code or "", re.I)
    if m:
        meta["desc"] = m.group(1).strip()
    return meta


def _escape_header_value(value: str) -> str:
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"')


def _ensure_binary_header(code: str, source: str, fallback_filename: str = "converted_module.py") -> str:
    code = _strip_code_fence(code)
    meta = _parse_converted_meta(code)
    if not meta["name"] or meta["name"] == "Converted Module":
        meta["name"] = _guess_name_from_source(source, Path(fallback_filename).stem.title())
    if not meta["cmd"] or meta["cmd"] == ".mod":
        meta["cmd"] = _guess_cmd_from_source(source, "." + Path(fallback_filename).stem)

    if "# MODULE_NAME" not in code[:500]:
        header = (
            f'# MODULE_NAME = "{_escape_header_value(meta["name"])}"\n'
            f'# MODULE_CMD  = "{_escape_header_value(meta["cmd"])}"\n'
            f'# MODULE_DESC = "{_escape_header_value(meta["desc"])}"\n\n'
        )
        code = header + code.lstrip()
    return code.strip() + "\n"


def _make_filename(code: str, original_filename: str = "") -> str:
    meta = _parse_converted_meta(code)
    cmd = (meta.get("cmd") or "").strip().lstrip(".")
    name = (meta.get("name") or "").strip()
    if cmd:
        return _safe_filename(cmd + ".py")
    if original_filename:
        return _safe_filename("converted_" + original_filename)
    return _safe_filename(name or "converted_module.py")


def _detect_kind(source: str) -> str:
    s = source or ""
    heroku_markers = [
        "CMD_HELP",
        "admin_cmd",
        "sudo_cmd",
        "edit_or_reply",
        "edit_delete",
        "from userbot",
        "import userbot",
        "@borg.on",
        "@bot.on",
        "userbot.events",
        "USERBOT",
        "Config.HEROKU",
        "heroku3",
    ]
    hikka_markers = [
        "loader.Module",
        "@loader.command",
        "self._client",
        "utils.answer",
    ]
    if any(x in s for x in heroku_markers):
        return "Heroku/UserBot plugin"
    if any(x in s for x in hikka_markers):
        return "Hikka/FTG module"
    if "# MODULE_NAME" in s and "bot_client" in s:
        return "BinaryUserbot module"
    return "generic Telegram userbot python module"


async def _download_url(url: str) -> tuple[str, str]:
    raw_url = _github_to_raw(url)
    headers = {
        "User-Agent": "BinaryUserbot-GitMD/2.0",
        "Accept": "text/plain,*/*",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(
            raw_url,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=25),
        ) as response:
            if response.status != 200:
                body = await response.text(errors="ignore")
                raise RuntimeError(f"HTTP {response.status}: {body[:250]}")
            data = await response.read()
    filename = Path(urlparse(raw_url).path).name or "module.py"
    return _decode_bytes(data), _safe_filename(filename)


async def _source_from_reply(reply) -> tuple[str, str]:
    if not reply:
        raise RuntimeError("Нет ответа на сообщение.")

    file = getattr(reply, "file", None)
    if file:
        filename = getattr(file, "name", None) or "module.py"
        mime = getattr(file, "mime_type", "") or ""
        is_code_file = (
            filename.endswith((".py", ".txt"))
            or "python" in mime.lower()
            or "text" in mime.lower()
            or filename == "module.py"
        )
        if is_code_file:
            data = await reply.download_media(bytes)
            if not data:
                raise RuntimeError("Не удалось скачать файл из ответа.")
            return _decode_bytes(data), _safe_filename(filename)

    text = getattr(reply, "raw_text", None) or getattr(reply, "text", None) or ""
    text = text.strip()
    if not text:
        raise RuntimeError("В ответе нет Python-кода, ссылки или .py файла.")

    url = _extract_first_url(text)
    if url:
        return await _download_url(url)
    return _strip_code_fence(text), "reply_module.py"


async def _get_source(event, args: str) -> tuple[str, str, bool]:
    args = (args or "").strip()
    install = False
    if args:
        first = args.split(maxsplit=1)[0].lower()
        if first in {"install", "inst", "i", "установить", "поставить"}:
            install = True
            args = args[len(args.split(maxsplit=1)[0]):].strip()

    url = _extract_first_url(args)
    if url:
        source, filename = await _download_url(url)
        return source, filename, install

    reply = await event.get_reply_message()
    if reply:
        source, filename = await _source_from_reply(reply)
        return source, filename, install

    if args and ("\n" in args or "import " in args or "from " in args or "async def " in args):
        return _strip_code_fence(args), "inline_module.py", install

    raise RuntimeError(
        "Нет источника модуля. Используй ссылку, ответ на .py файл или ответ на сообщение с кодом."
    )


async def _convert_to_binary(source: str, original_filename: str) -> str:
    source = _strip_code_fence(source)
    if not source or len(source) < 20:
        raise RuntimeError("Источник слишком короткий, это не похоже на модуль.")

    kind = _detect_kind(source)
    system = """
Ты конвертер Telegram userbot модулей в формат BinaryUserbot.

Формат BinaryUserbot:
- В начале обязательно добавь:
  # MODULE_NAME = "..."
  # MODULE_CMD = ".команда"
  # MODULE_DESC = "..."
- Используй Telethon.
- Импортируй:
  from telethon import events
  from bot_client import client
  from utils import html
- Можно использовать:
  try:
      from premium_emoji import by_line
  except Exception:
      def by_line(): return "<i>Binary Userbot</i>"
- Хендлеры должны быть через:
  @client.on(events.NewMessage(pattern=r"^\\.cmd(?:\\s+(.+))?$", outgoing=True))
- Ответы делай через event.edit(..., parse_mode="html") или client.send_message(...).
- Если исходник использует edit_or_reply/edit_delete, замени на event.edit.
- Если исходник использует event.pattern_match.group(1), сохрани это поведение.
- Если исходник использует reply, используй await event.get_reply_message().
- Не используй loader.Module, utils.answer, userbot, borg, bot, catub, friday, ultroid, Config, CMD_HELP.
- Не оставляй Heroku/userbot-specific импорты.
- Сохрани основную логику модуля, но адаптируй под BinaryUserbot.
- Если исходник Heroku/UserBot:
  * @borg.on(admin_cmd(pattern="ping")) -> @client.on(events.NewMessage(pattern=r"^\\.ping(?:\\s+(.+))?$", outgoing=True))
  * @register(outgoing=True, pattern="...") -> @client.on(events.NewMessage(pattern=..., outgoing=True))
  * CMD_HELP преврати в MODULE_NAME/MODULE_CMD/MODULE_DESC.
- Если исходник уже BinaryUserbot — просто аккуратно исправь метаданные и импорты.
- Верни только готовый Python-код без объяснений и без markdown.
""".strip()

    user = f"""
Тип исходника: {kind}
Имя файла: {original_filename}

Исходный код:
```python
{source}
```
""".strip()

    converted = await or_request(system, user, max_tokens=4000)
    converted = _ensure_binary_header(converted, source, original_filename)

    if "from bot_client import client" not in converted and "bot_client import client" not in converted:
        raise RuntimeError("Конвертация не дала BinaryUserbot-код: нет импорта client.")
    if "@client.on" not in converted:
        raise RuntimeError("Конвертация не дала хендлеров @client.on.")
    return converted


async def _send_result(event, code: str, filename: str, install: bool):
    meta = _parse_converted_meta(code)

    if install:
        if not install_module:
            raise RuntimeError("install_module недоступен в этом окружении.")
        info = install_module(filename, code.encode("utf-8"))
        return await event.edit(
            "✅ <b>Модуль переписан, установлен и загружен</b>\n\n"
            f"<b>Имя:</b> {html(info.get('name', meta.get('name')))}\n"
            f"<b>Команда:</b> <code>{html(info.get('cmd', meta.get('cmd')))}</code>\n"
            f"<b>Файл:</b> <code>{html(filename)}</code>\n\n"
            f"{by_line()}",
            parse_mode="html",
            link_preview=False,
        )

    buf = io.BytesIO(code.encode("utf-8"))
    buf.name = filename
    await client.send_file(
        event.chat_id,
        buf,
        caption=(
            "✅ <b>Модуль переписан под BinaryUserbot</b>\n\n"
            f"<b>Имя:</b> {html(meta.get('name'))}\n"
            f"<b>Команда:</b> <code>{html(meta.get('cmd'))}</code>\n"
            f"<b>Файл:</b> <code>{html(filename)}</code>\n\n"
            f"<b>Установка:</b> ответь на файл командой <code>.savemod</code>\n"
            f"<b>Или сразу:</b> <code>.md install</code> ответом на исходник\n\n"
            f"{by_line()}"
        ),
        parse_mode="html",
    )

    try:
        await event.delete()
    except Exception:
        pass


async def _send_native_result(event, source: str, filename: str, install: bool, reason: str):
    if install:
        if not install_module_smart:
            raise RuntimeError("install_module_smart недоступен в этом окружении.")
        info = await install_module_smart(filename, source.encode("utf-8"))
        return await event.edit(
            "✅ <b>Модуль установлен через GitMD</b>\n\n"
            f"<b>Имя:</b> {html(info.get('name'))}\n"
            f"<b>Команда:</b> <code>{html(info.get('cmd'))}</code>\n"
            f"<b>Файл:</b> <code>{html(filename)}</code>\n"
            f"<b>Проверка:</b> {html(reason or 'нативная совместимость')}\n\n"
            f"{by_line()}",
            parse_mode="html",
            link_preview=False,
        )

    buf = io.BytesIO(source.encode("utf-8"))
    buf.name = filename
    await client.send_file(
        event.chat_id,
        buf,
        caption=(
            "✅ <b>GitMD: модуль можно ставить нативно</b>\n\n"
            f"<b>Файл:</b> <code>{html(filename)}</code>\n"
            f"<b>Проверка:</b> {html(reason or 'совместим с текущим загрузчиком')}\n\n"
            f"<b>Установка:</b> ответь на файл командой <code>.savemod</code>\n"
            f"<b>Или сразу:</b> <code>.md install</code> ответом на исходник\n\n"
            f"{by_line()}"
        ),
        parse_mode="html",
    )
    try:
        await event.delete()
    except Exception:
        pass


@client.on(events.NewMessage(pattern=r"^\.md(?:\s+([\s\S]+))?$", outgoing=True))
async def cmd_md(event):
    args = event.pattern_match.group(1) or ""

    if not args.strip() and not event.is_reply:
        return await event.edit(
            "🧩 <b>GitMD</b>\n\n"
            "<b>Что умеет:</b>\n"
            "• переписывает модули под BinaryUserbot\n"
            "• принимает GitHub/raw ссылку\n"
            "• принимает ответ на <code>.py</code> файл\n"
            "• принимает ответ на сообщение с Python-кодом\n"
            "• поддерживает Heroku/UserBot-style плагины\n\n"
            "<b>Примеры:</b>\n"
            "<code>.md https://github.com/user/repo/blob/main/plugin.py</code>\n"
            "<code>.md</code> — ответом на .py файл или код\n"
            "<code>.md install</code> — ответом на исходник, сразу установить\n\n"
            f"{by_line()}",
            parse_mode="html",
            link_preview=False,
        )

    await event.edit(
        "🧩 <b>GitMD</b>\n\n"
        "Получаю исходник и переписываю модуль под BinaryUserbot...",
        parse_mode="html",
    )

    try:
        source, original_filename, install = await _get_source(event, args)

        native_ok = False
        native_reason = ""

        if "# MODULE_NAME" in source and "from bot_client import client" in source:
            native_ok = True
            native_reason = "BinaryUserbot module"
        elif can_try_native and can_try_native(source):
            await event.edit(
                "🧩 <b>GitMD</b>\n\n"
                f"<b>Тип:</b> <code>{html(_detect_kind(source))}</code>\n"
                "Проверяю через AI, можно ли установить модуль без переписывания...",
                parse_mode="html",
            )
            from module_ai import assess_native_support_with_ai

            native_ok, native_reason = await assess_native_support_with_ai(source, original_filename)

        if native_ok:
            await _send_native_result(event, source, _safe_filename(original_filename), install, native_reason)
            return

        if "# MODULE_NAME" in source and "from bot_client import client" in source:
            converted = _ensure_binary_header(source, source, original_filename)
        else:
            await event.edit(
                "🧩 <b>GitMD</b>\n\n"
                f"<b>Тип:</b> <code>{html(_detect_kind(source))}</code>\n"
                f"<b>Нативно:</b> <code>{html(native_reason or 'нет')}</code>\n"
                "Переписываю код под BinaryUserbot...",
                parse_mode="html",
            )
            converted = await _convert_to_binary(source, original_filename)

        filename = _make_filename(converted, original_filename)
        await _send_result(event, converted, filename, install)

    except Exception as e:
        await event.edit(
            "❌ <b>GitMD ошибка</b>\n\n"
            f"<code>{html(str(e)[:900])}</code>\n\n"
            f"<pre>{html(traceback.format_exc()[-1800:])}</pre>",
            parse_mode="html",
            link_preview=False,
        )
