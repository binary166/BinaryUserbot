"""
Система динамической загрузки модулей для Binary Userbot.
Команда: .md (ответом на .py файл)

Формат модуля:
    # MODULE_NAME = "Название команды"
    # MODULE_CMD  = ".mycommand"
    # MODULE_DESC = "Описание что делает команда"
"""
import os
import re
import sys
import importlib.util
import importlib
from pathlib import Path

MODULES_DIR = Path(__file__).parent / "modules"
MODULES_DIR.mkdir(exist_ok=True)

_loaded_modules: dict = {}


def parse_module_meta(source: str) -> dict:
    """Парсит метаданные из комментариев в начале файла."""
    meta = {"name": None, "cmd": None, "desc": None}
    for line in source.splitlines()[:30]:
        line = line.strip()
        m = re.match(r"#\s*MODULE_NAME\s*=\s*['\"](.+)['\"]", line)
        if m:
            meta["name"] = m.group(1)
        m = re.match(r"#\s*MODULE_CMD\s*=\s*['\"](.+)['\"]", line)
        if m:
            meta["cmd"] = m.group(1)
        m = re.match(r"#\s*MODULE_DESC\s*=\s*['\"](.+)['\"]", line)
        if m:
            meta["desc"] = m.group(1)
    return meta


def load_module(filepath: str) -> dict:
    """
    Загружает Python-модуль из файла.
    Возвращает dict с метаданными или выбрасывает исключение.
    """
    path = Path(filepath)
    source = path.read_text(encoding="utf-8")
    meta = parse_module_meta(source)

    module_name = f"binary_module_{path.stem}"

    if module_name in sys.modules:
        old = sys.modules.pop(module_name)
        if hasattr(old, "_binary_handlers"):
            try:
                from bot_client import client
                for h in old._binary_handlers:
                    client.remove_event_handler(h)
            except Exception:
                pass

    spec = importlib.util.spec_from_file_location(module_name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)

    cmd = meta.get("cmd") or f".{path.stem}"
    _loaded_modules[cmd] = {
        "name": meta.get("name") or path.stem,
        "cmd":  cmd,
        "desc": meta.get("desc") or "Модуль без описания",
        "file": str(path),
        "module_name": module_name,
    }
    return _loaded_modules[cmd]


def install_module(filename: str, content: bytes) -> dict:
    """Сохраняет файл в папку modules/ и загружает его."""
    safe_name = re.sub(r"[^\w.\-]", "_", filename)
    if not safe_name.endswith(".py"):
        safe_name += ".py"
    dest = MODULES_DIR / safe_name
    dest.write_bytes(content)
    return load_module(str(dest))


def get_loaded_modules() -> dict:
    return dict(_loaded_modules)


def load_all_saved():
    """При запуске загружает все ранее установленные модули из папки modules/."""
    for pyfile in sorted(MODULES_DIR.glob("*.py")):
        try:
            load_module(str(pyfile))
            print(f"[MOD] Загружен: {pyfile.name}")
        except Exception as e:
            print(f"[MOD] Ошибка загрузки {pyfile.name}: {e}")
