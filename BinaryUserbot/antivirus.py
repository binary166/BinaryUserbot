from pathlib import Path

import settings
from ai import or_request
from config import MY_ID
from premium_emoji import by_line
from utils import get_username, html, resolve_sender, send_me


CODE_EXTS = {
    ".py", ".pyw", ".bat", ".cmd", ".ps1", ".sh", ".js", ".ts", ".jsx", ".tsx",
    ".vbs", ".vbe", ".wsf", ".php", ".pl", ".rb", ".lua", ".go", ".rs", ".c",
    ".cpp", ".cs", ".java", ".kt",
}

DANGEROUS_EXTS = {
    ".apk", ".exe", ".dll", ".msi", ".scr", ".com", ".jar", ".lnk", ".reg",
    ".vbe", ".wsf", ".hta", ".dmg", ".pkg", ".iso", ".img", ".cab", ".bin",
    ".zip", ".rar", ".7z", ".tar", ".gz", ".xz", ".ace",
}

SUSPICIOUS_MIME = {
    "application/x-msdownload",
    "application/vnd.android.package-archive",
    "application/x-msdos-program",
    "application/x-dosexec",
    "application/java-archive",
    "application/octet-stream",
}


def _clean_ext(value: str | None) -> str:
    value = (value or "").strip().lower()
    if value and not value.startswith("."):
        value = "." + value
    return value


def _file_ext(msg) -> str:
    file = getattr(msg, "file", None)
    if not file:
        return ""
    name = (getattr(file, "name", None) or "").lower()
    if name:
        return Path(name).suffix.lower()
    return _clean_ext(getattr(file, "ext", None))


def _file_name(msg) -> str:
    file = getattr(msg, "file", None)
    if not file:
        return "file"
    return (getattr(file, "name", None) or f"unknown{_file_ext(msg) or ''}").strip() or "file"


def _mime(msg) -> str:
    file = getattr(msg, "file", None)
    return ((getattr(file, "mime_type", None) or "") if file else "").lower()


def _is_trackable_document(msg) -> bool:
    if not getattr(msg, "document", None):
        return False
    if getattr(msg, "video", False) or getattr(msg, "photo", False) or getattr(msg, "voice", False):
        return False
    mime = _mime(msg)
    if mime.startswith("video/"):
        return False
    return True


def _label_for_sender(sender, sender_id) -> str:
    if sender is None:
        return f"ID {sender_id or 'unknown'}"
    username = getattr(sender, "username", None)
    if username:
        return f"@{username}"
    return get_username(sender)


async def _download_code_text(msg) -> str | None:
    try:
        raw = await msg.download_media(bytes)
    except Exception:
        return None
    if not raw:
        return None
    for encoding in ("utf-8-sig", "utf-8", "cp1251", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except Exception:
            text = None
    if not text:
        text = raw.decode("utf-8", errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text[:30000]


async def handle_antivirus_incoming(event) -> bool:
    if not settings.get("antivirus_enabled", False):
        return False

    msg = event.message
    if not event.is_private or msg.out:
        return False
    if not _is_trackable_document(msg):
        return False

    ext = _file_ext(msg)
    mime = _mime(msg)
    if ext not in DANGEROUS_EXTS and ext not in CODE_EXTS and mime not in SUSPICIOUS_MIME:
        return False

    sender = await resolve_sender(msg)
    sender_label = _label_for_sender(sender, msg.sender_id)
    file_name = _file_name(msg)

    if ext in CODE_EXTS:
        code = await _download_code_text(msg)
        if not code:
            await send_me(
                f"🛡 <b>Антивирус</b>\n\n"
                f"От: <b>{html(sender_label)}</b>\n"
                f"Файл: <code>{html(file_name)}</code>\n\n"
                f"⚠️ Не удалось прочитать содержимое для анализа.\n\n" + by_line()
            )
            return True

        await send_me(
            f"🛡 <b>Антивирус</b>\n\n"
            f"От: <b>{html(sender_label)}</b>\n"
            f"Файл: <code>{html(file_name)}</code>\n"
            f"Тип: <code>{html(ext or mime or 'code')}</code>\n\n"
            f"🧠 Анализирую код...\n\n" + by_line()
        )

        system = (
            "Ты эксперт по анализу кода и вредоносных вложений. "
            "Коротко и точно объясни, что делает код: запуск, сеть, файлы, автозапуск, кража данных, удаление, обход защиты. "
            "Если есть подозрительные действия, перечисли их отдельным блоком. "
            "Пиши по-русски, структурно, без лишней воды."
        )
        try:
            analysis = await or_request(system, code, max_tokens=700)
        except Exception as e:
            analysis = f"Не удалось проанализировать код: {e}"

        await send_me(
            f"🛡 <b>Анализ файла</b>\n\n"
            f"От: <b>{html(sender_label)}</b>\n"
            f"Файл: <code>{html(file_name)}</code>\n\n"
            f"<blockquote>{html(analysis)}</blockquote>\n\n" + by_line()
        )
        return True

    danger_reason = "опасное расширение" if ext in DANGEROUS_EXTS else "подозрительный MIME"
    await send_me(
        f"🛡 <b>Антивирус</b>\n\n"
        f"От: <b>{html(sender_label)}</b>\n"
        f"Файл: <code>{html(file_name)}</code>\n"
        f"Тип: <code>{html(ext or mime or 'unknown')}</code>\n\n"
        f"⚠️ Обнаружен опасный файл ({danger_reason}).\n\n" + by_line()
    )
    return True
