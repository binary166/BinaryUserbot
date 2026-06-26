# MODULE_NAME = "Module Manager"
# MODULE_CMD  = ".mods"
# MODULE_DESC = "Отправка, установка, перезагрузка и удаление модулей"

import os
import re
import sys
import traceback
from pathlib import Path

from telethon import events
from bot_client import client

import module_loader
from utils import html

MODULES_DIR = module_loader.MODULES_DIR


def clean_module_name(name: str) -> str:
    """
    Убирает текстовый мусор типа 'box DoxTool',
    если он уже попал в MODULE_NAME.
    """
    name = str(name or "").strip()

    bad_prefixes = (
        "box ",
        "Box ",
        "BOX ",
        "📦 ",
    )

    for prefix in bad_prefixes:
        if name.startswith(prefix):
            name = name[len(prefix):].strip()

    return name or "Без названия"


def normalize_query(text: str) -> str:
    text = str(text or "").strip().lower()
    text = text.replace(".py", "")
    text = text.replace("/", "")
    text = text.replace("\\", "")
    return text


def parse_meta_from_file(path: Path) -> dict:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        meta = module_loader.parse_module_meta(source)
    except Exception:
        meta = {"name": None, "cmd": None, "desc": None}

    return {
        "name": clean_module_name(meta.get("name") or path.stem),
        "cmd": meta.get("cmd") or f".{path.stem}",
        "desc": meta.get("desc") or "Без описания",
        "file": str(path),
        "stem": path.stem,
        "filename": path.name,
    }


def get_all_module_files() -> list[Path]:
    MODULES_DIR.mkdir(exist_ok=True)
    return sorted(
        p for p in MODULES_DIR.glob("*.py")
        if p.is_file() and not p.name.startswith("__")
    )


def find_module(query: str) -> Path | None:
    q = normalize_query(query)
    if not q:
        return None

    for path in get_all_module_files():
        meta = parse_meta_from_file(path)

        variants = {
            normalize_query(path.name),
            normalize_query(path.stem),
            normalize_query(meta["name"]),
            normalize_query(meta["cmd"]),
        }

        if q in variants:
            return path

    for path in get_all_module_files():
        meta = parse_meta_from_file(path)
        haystack = " ".join([
            path.name,
            path.stem,
            meta["name"],
            meta["cmd"],
            meta["desc"],
        ]).lower()

        if q in haystack:
            return path

    return None


async def answer(event, text: str):
    await event.edit(text, parse_mode="html", link_preview=False)


def unload_module_by_path(path: Path) -> int:
    """
    Пытается выгрузить обработчики модуля без перезапуска.

    Важно:
    если модуль создавал фоновые задачи или нестандартные обработчики,
    после удаления всё равно лучше перезапустить юзербот.
    """
    removed = 0
    try:
        builders_before = len(getattr(client, "_event_builders", []) or [])
        remover = getattr(module_loader, "_remove_registered", None)
        if remover:
            remover(path)
            builders_after = len(getattr(client, "_event_builders", []) or [])
            return max(removed, builders_before - builders_after)
    except Exception:
        pass

    module_name = f"binary_module_{path.stem}"

    try:
        builders = getattr(client, "_event_builders", None)

        if builders:
            new_builders = []

            for item in builders:
                try:
                    builder, callback = item
                    callback_module = getattr(callback, "__module__", "")
                except Exception:
                    new_builders.append(item)
                    continue

                if callback_module == module_name:
                    removed += 1
                    continue

                new_builders.append(item)

            client._event_builders = new_builders

    except Exception:
        pass

    try:
        sys.modules.pop(module_name, None)
    except Exception:
        pass

    try:
        loaded = getattr(module_loader, "_loaded_modules", {})
        for cmd, info in list(loaded.items()):
            info_file = Path(str(info.get("file", ""))).resolve()
            if info_file == path.resolve():
                loaded.pop(cmd, None)
    except Exception:
        pass

    return removed


@client.on(events.NewMessage(pattern=r"^\.mods$", outgoing=True))
async def cmd_mods(event):
    files = get_all_module_files()

    if not files:
        return await answer(
            event,
            "📦 <b>Модули</b>\n\n"
            "Папка <code>modules</code> пустая."
        )

    lines = [
        "📦 <b>Установленные модули</b>",
        "",
    ]

    for i, path in enumerate(files, 1):
        meta = parse_meta_from_file(path)

        lines.append(
            f"<b>{i}.</b> 📦 <b>{html(meta['name'])}</b>\n"
            f"   <b>Файл:</b> <code>{html(meta['filename'])}</code>\n"
            f"   <b>Команда:</b> <code>{html(meta['cmd'])}</code>\n"
            f"   <b>Описание:</b> {html(meta['desc'])}"
        )

    lines.append("")
    lines.append("<b>Команды:</b>")
    lines.append("<code>.sendmod имя</code> — отправить модуль")
    lines.append("<code>.sendmod all</code> — отправить все модули")
    lines.append("<code>.savemod</code> — сохранить модуль из ответа")
    lines.append("<code>.loadmod имя</code> — перезагрузить модуль")
    lines.append("<code>.delmod имя</code> — удалить модуль")

    await answer(event, "\n\n".join(lines))


@client.on(events.NewMessage(pattern=r"^\.sendmod(?:\s+(.+))?$", outgoing=True))
async def cmd_sendmod(event):
    arg = event.pattern_match.group(1)

    if not arg:
        return await answer(
            event,
            "📦 <b>Отправка модуля</b>\n\n"
            "Используй:\n"
            "<code>.sendmod имя</code>\n"
            "<code>.sendmod all</code>"
        )

    arg = arg.strip()

    if arg.lower() == "all":
        files = get_all_module_files()

        if not files:
            return await answer(event, "❌ <b>Модули не найдены.</b>")

        await answer(event, f"📦 <b>Отправляю модулей:</b> <code>{len(files)}</code>")

        for path in files:
            meta = parse_meta_from_file(path)
            caption = (
                f"📦 <b>{html(meta['name'])}</b>\n\n"
                f"<b>Файл:</b> <code>{html(path.name)}</code>\n"
                f"<b>Команда:</b> <code>{html(meta['cmd'])}</code>\n"
                f"<b>Описание:</b> {html(meta['desc'])}"
            )

            await client.send_file(
                event.chat_id,
                str(path),
                caption=caption,
                parse_mode="html"
            )

        try:
            await event.delete()
        except Exception:
            pass

        return

    path = find_module(arg)

    if not path:
        return await answer(
            event,
            f"❌ <b>Модуль не найден:</b> <code>{html(arg)}</code>\n\n"
            "Посмотреть список:\n"
            "<code>.mods</code>"
        )

    meta = parse_meta_from_file(path)

    await client.send_file(
        event.chat_id,
        str(path),
        caption=(
            f"📦 <b>{html(meta['name'])}</b>\n\n"
            f"<b>Файл:</b> <code>{html(path.name)}</code>\n"
            f"<b>Команда:</b> <code>{html(meta['cmd'])}</code>\n"
            f"<b>Описание:</b> {html(meta['desc'])}"
        ),
        parse_mode="html"
    )

    try:
        await event.delete()
    except Exception:
        pass


@client.on(events.NewMessage(pattern=r"^\.savemod$", outgoing=True))
async def cmd_savemod(event):
    if not event.is_reply:
        return await answer(
            event,
            "❗ <b>Ответь на файл модуля.</b>\n\n"
            "Пример:\n"
            "1. Получи <code>.py</code> файл\n"
            "2. Ответь на него командой <code>.savemod</code>"
        )

    reply = await event.get_reply_message()

    if not reply.file:
        return await answer(event, "❌ <b>В ответе нет файла.</b>")

    filename = reply.file.name or "module.py"

    if not filename.endswith(".py"):
        return await answer(
            event,
            "❌ <b>Это не Python-модуль.</b>\n\n"
            "Файл должен заканчиваться на <code>.py</code>."
        )

    await answer(event, "📦 <b>Сохраняю и загружаю модуль...</b>")

    try:
        data = await reply.download_media(file=bytes)
        info = await module_loader.install_module_smart(filename, data)

        name = clean_module_name(info.get("name"))
        cmd = info.get("cmd") or "?"

        await answer(
            event,
            f"✅ <b>Модуль установлен</b>\n\n"
            f"📦 <b>{html(name)}</b>\n"
            f"<b>Команда:</b> <code>{html(cmd)}</code>"
        )

    except Exception as e:
        await answer(
            event,
            "❌ <b>Ошибка установки модуля:</b>\n"
            f"<code>{html(str(e))}</code>\n\n"
            f"<pre>{html(traceback.format_exc()[-1500:])}</pre>"
        )


@client.on(events.NewMessage(pattern=r"^\.loadmod(?:\s+(.+))?$", outgoing=True))
async def cmd_loadmod(event):
    arg = event.pattern_match.group(1)

    if not arg:
        return await answer(
            event,
            "📦 <b>Перезагрузка модуля</b>\n\n"
            "Используй:\n"
            "<code>.loadmod имя</code>"
        )

    path = find_module(arg.strip())

    if not path:
        return await answer(
            event,
            f"❌ <b>Модуль не найден:</b> <code>{html(arg)}</code>"
        )

    await answer(event, "📦 <b>Перезагружаю модуль...</b>")

    try:
        unload_module_by_path(path)
        info = module_loader.load_module(str(path))

        name = clean_module_name(info.get("name"))
        cmd = info.get("cmd") or "?"

        await answer(
            event,
            f"✅ <b>Модуль перезагружен</b>\n\n"
            f"📦 <b>{html(name)}</b>\n"
            f"<b>Команда:</b> <code>{html(cmd)}</code>"
        )

    except Exception as e:
        await answer(
            event,
            "❌ <b>Ошибка перезагрузки:</b>\n"
            f"<code>{html(str(e))}</code>\n\n"
            f"<pre>{html(traceback.format_exc()[-1500:])}</pre>"
        )


@client.on(events.NewMessage(pattern=r"^\.(?:delmod|rmmod|deletemod)(?:\s+(.+))?$", outgoing=True))
async def cmd_delmod(event):
    arg = event.pattern_match.group(1)

    if not arg:
        return await answer(
            event,
            "🗑 <b>Удаление модуля</b>\n\n"
            "Используй:\n"
            "<code>.delmod имя</code>\n\n"
            "Пример:\n"
            "<code>.delmod DoxTool</code>"
        )

    path = find_module(arg.strip())

    if not path:
        return await answer(
            event,
            f"❌ <b>Модуль не найден:</b> <code>{html(arg)}</code>\n\n"
            "Посмотреть список:\n"
            "<code>.mods</code>"
        )

    meta = parse_meta_from_file(path)

    try:
        removed_handlers = unload_module_by_path(path)
        os.remove(path)

        await answer(
            event,
            f"✅ <b>Модуль удалён</b>\n\n"
            f"📦 <b>{html(meta['name'])}</b>\n"
            f"<b>Файл:</b> <code>{html(path.name)}</code>\n"
            f"<b>Выгружено обработчиков:</b> <code>{removed_handlers}</code>\n\n"
            "Если команда модуля всё ещё работает — перезапусти юзербот."
        )

    except Exception as e:
        await answer(
            event,
            "❌ <b>Ошибка удаления:</b>\n"
            f"<code>{html(str(e))}</code>"
        )
