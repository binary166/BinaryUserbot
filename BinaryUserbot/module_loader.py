import asyncio
import hashlib
import importlib
import importlib.util
import inspect
import re
import sys
import types
from pathlib import Path

from telethon import events


BASE_DIR = Path(__file__).parent
BUILTIN_MODULES_DIR = BASE_DIR / "builtin_modules"
MODULES_DIR = BASE_DIR / "modules"

BUILTIN_MODULES_DIR.mkdir(exist_ok=True)
MODULES_DIR.mkdir(exist_ok=True)

RUNTIME_PACKAGE = "binary_runtime"

_loaded_modules: dict = {}
_loaded_by_path: dict[str, list[str]] = {}
_loader_instances: list = []
_deferred_loops: list[tuple[object, object, dict]] = []
_started_tasks: list[asyncio.Task] = []


class _CompatLoop:
    def __init__(self, instance, method, info: dict):
        self.instance = instance
        self.method = method
        self.info = info
        self.interval = float(info.get("interval") or 1)
        self.task: asyncio.Task | None = None
        self.func = getattr(method, "__func__", method)
        self.__name__ = getattr(method, "__name__", "loop")
        self._binary_loop = info

    async def __call__(self, *args, **kwargs):
        result = self.method(*args, **kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    async def _runner(self):
        while True:
            try:
                await self()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[COMPAT] loop error in {self.__name__}: {e}")
            await asyncio.sleep(self.interval)

    def start(self):
        if self.task and not self.task.done():
            return self.task
        self.task = asyncio.create_task(self._runner())
        setattr(self.task, "_binary_module_path", getattr(self.instance, "__binary_module_path__", ""))
        _started_tasks.append(self.task)
        return self.task

    def stop(self):
        if self.task and not self.task.done():
            self.task.cancel()


def parse_module_meta(source: str) -> dict:
    meta = {"name": None, "cmd": None, "desc": None}
    for line in source.splitlines()[:60]:
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


def _safe_mod_part(value: str) -> str:
    value = re.sub(r"\W+", "_", value or "", flags=re.ASCII).strip("_")
    return value or "module"


def _module_name_for_path(path: Path, builtin: bool = False) -> str:
    bucket = "builtin_modules" if builtin else "modules"
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"{RUNTIME_PACKAGE}.{bucket}.{_safe_mod_part(path.stem)}_{digest}"


def _ensure_runtime_package() -> None:
    pkg = sys.modules.get(RUNTIME_PACKAGE)
    if pkg is None:
        pkg = types.ModuleType(RUNTIME_PACKAGE)
        pkg.__path__ = [str(BASE_DIR)]
        sys.modules[RUNTIME_PACKAGE] = pkg

    for local_name in ("loader", "utils"):
        mod = importlib.import_module(local_name)
        runtime_name = f"{RUNTIME_PACKAGE}.{local_name}"
        sys.modules[runtime_name] = mod
        setattr(pkg, local_name, mod)

    for folder_name, folder in (
        ("builtin_modules", BUILTIN_MODULES_DIR),
        ("modules", MODULES_DIR),
    ):
        runtime_name = f"{RUNTIME_PACKAGE}.{folder_name}"
        subpkg = sys.modules.get(runtime_name)
        if subpkg is None:
            subpkg = types.ModuleType(runtime_name)
            sys.modules[runtime_name] = subpkg
        subpkg.__path__ = [str(folder)]
        setattr(pkg, folder_name, subpkg)


def _remove_registered(path: Path) -> None:
    path_key = str(path.resolve())
    module_names = _loaded_by_path.pop(path_key, [])
    try:
        from bot_client import client
    except Exception:
        client = None

    for module_name in module_names:
        old = sys.modules.pop(module_name, None)
        if old and client and hasattr(old, "_binary_handlers"):
            for handler in list(getattr(old, "_binary_handlers", [])):
                try:
                    client.remove_event_handler(handler)
                except Exception:
                    pass

    for task in list(_started_tasks):
        mod_path = getattr(task, "_binary_module_path", None)
        if mod_path == path_key and not task.done():
            task.cancel()
            _started_tasks.remove(task)

    for cmd, info in list(_loaded_modules.items()):
        if str(Path(info.get("file", "")).resolve()) == path_key:
            _loaded_modules.pop(cmd, None)


def _normal_cmd(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    return value if value.startswith(".") else "." + value


def _add_loaded_command(cmd: str, info: dict) -> None:
    cmd = _normal_cmd(cmd)
    if not cmd:
        return
    data = dict(info)
    data["cmd"] = cmd
    _loaded_modules[cmd] = data


def _method_command_names(method) -> list[str]:
    names = list(getattr(method, "_binary_command_names", []) or [])
    method_name = getattr(method, "__name__", "")
    if method_name.endswith("cmd") and not method_name.startswith("_"):
        names.insert(0, method_name[:-3])

    result = []
    seen = set()
    for name in names:
        cmd = _normal_cmd(name)
        key = cmd.lower()
        if cmd and key not in seen:
            seen.add(key)
            result.append(cmd)
    return result


def _wrap_strings(instance) -> None:
    try:
        import loader as compat_loader
    except Exception:
        return

    strings = getattr(instance, "strings", None)
    if isinstance(strings, dict) and not callable(strings):
        instance.strings = compat_loader.Strings(strings)


def _register_loader_module(mod, path: Path, meta: dict, builtin: bool, module_name: str) -> list[dict]:
    try:
        import loader as compat_loader
        from bot_client import client
    except Exception:
        return []

    registered = []
    handlers = list(getattr(mod, "_binary_handlers", []))

    for obj in list(vars(mod).values()):
        if not inspect.isclass(obj):
            continue
        try:
            if not issubclass(obj, compat_loader.Module) or obj is compat_loader.Module:
                continue
        except Exception:
            continue

        instance = obj()
        instance.client = client
        instance._client = client
        instance.name = getattr(getattr(instance, "strings", {}), "get", lambda *_: obj.__name__)("name", obj.__name__)
        instance.__binary_module_path__ = str(path.resolve())
        _wrap_strings(instance)
        _loader_instances.append(instance)

        ready = getattr(instance, "client_ready", None)
        if ready:
            setattr(instance, "__binary_client_ready_pending__", True)

        for attr_name, method in inspect.getmembers(instance, predicate=callable):
            loop_info = getattr(method, "_binary_loop", None)
            if loop_info:
                controller = _CompatLoop(instance, method, loop_info)
                setattr(instance, attr_name, controller)
                _deferred_loops.append((instance, controller, loop_info))
                method = controller

            for cmd in _method_command_names(method):
                if _normal_cmd(cmd) in _loaded_modules:
                    continue
                pattern = rf"^{re.escape(cmd)}(?:\s+([\s\S]+))?$"

                async def _handler(event, _method=method):
                    await _method(event.message)

                _handler.__module__ = module_name
                client.add_event_handler(
                    _handler,
                    events.NewMessage(pattern=pattern, outgoing=True),
                )
                handlers.append(_handler)

                desc = (
                    getattr(method, "_binary_doc", None)
                    or inspect.getdoc(method)
                    or meta.get("desc")
                    or "Heroku/Hikka compatible command"
                )
                info = {
                    "name": meta.get("name") or getattr(instance, "name", obj.__name__),
                    "cmd": cmd,
                    "desc": desc,
                    "file": str(path),
                    "module_name": module_name,
                    "builtin": builtin,
                    "compat": "loader",
                }
                registered.append(info)

    if handlers:
        mod._binary_handlers = handlers
    return registered


def can_try_native(source: str) -> bool:
    source = source or ""
    markers = (
        "# MODULE_NAME",
        "@client.on",
        "from bot_client import client",
        "loader.Module",
        "@loader.command",
        "utils.answer",
        "from .. import loader",
        "from .. import utils",
    )
    return any(marker in source for marker in markers)


def load_module(filepath: str, builtin: bool = False) -> dict:
    _ensure_runtime_package()

    path = Path(filepath).resolve()
    source = path.read_text(encoding="utf-8", errors="ignore")
    meta = parse_module_meta(source)
    module_name = _module_name_for_path(path, builtin=builtin)

    _remove_registered(path)

    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot create import spec for {path.name}")

    mod = importlib.util.module_from_spec(spec)
    mod.__package__ = module_name.rsplit(".", 1)[0]
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)

    _loaded_by_path.setdefault(str(path), []).append(module_name)

    base_info = {
        "name": meta.get("name") or path.stem,
        "cmd": meta.get("cmd") or f".{path.stem}",
        "desc": meta.get("desc") or "Module without description",
        "file": str(path),
        "module_name": module_name,
        "builtin": builtin,
        "compat": "telethon",
    }

    compat_infos = _register_loader_module(mod, path, meta, builtin, module_name)
    if compat_infos:
        for info in compat_infos:
            _add_loaded_command(info["cmd"], info)
        return compat_infos[0]

    _add_loaded_command(base_info["cmd"], base_info)
    return _loaded_modules[_normal_cmd(base_info["cmd"])]


def install_module(filename: str, content: bytes) -> dict:
    safe_name = re.sub(r"[^\w.\-]", "_", filename, flags=re.U)
    if not safe_name.endswith(".py"):
        safe_name += ".py"
    dest = MODULES_DIR / safe_name
    dest.write_bytes(content)
    return load_module(str(dest), builtin=False)


async def install_module_smart(filename: str, content: bytes) -> dict:
    try:
        return install_module(filename, content)
    except Exception as native_error:
        safe_name = re.sub(r"[^\w.\-]", "_", filename, flags=re.U)
        if not safe_name.endswith(".py"):
            safe_name += ".py"
        try:
            (MODULES_DIR / safe_name).unlink(missing_ok=True)
        except Exception:
            pass

        from module_ai import convert_module_with_ai

        converted_name, converted_code = await convert_module_with_ai(
            content.decode("utf-8", errors="ignore"),
            filename,
            native_error=str(native_error),
        )
        return install_module(converted_name, converted_code.encode("utf-8"))


def get_loaded_modules() -> dict:
    return dict(_loaded_modules)


def load_all_saved():
    for root, builtin in ((BUILTIN_MODULES_DIR, True), (MODULES_DIR, False)):
        for pyfile in sorted(root.glob("*.py")):
            if pyfile.name.startswith("__"):
                continue
            try:
                load_module(str(pyfile), builtin=builtin)
                label = "BASE" if builtin else "MOD"
                print(f"[{label}] Loaded: {pyfile.name}")
            except Exception as e:
                label = "BASE" if builtin else "MOD"
                print(f"[{label}] Load error {pyfile.name}: {e}")


async def run_deferred_startups():
    from bot_client import client

    try:
        me = await client.get_me()
        tg_id = getattr(me, "id", None)
    except Exception:
        tg_id = None

    for instance in list(_loader_instances):
        if not getattr(instance, "__binary_client_ready_pending__", False):
            continue
        ready = getattr(instance, "client_ready", None)
        if not ready:
            continue
        if tg_id is not None and not hasattr(instance, "_tg_id"):
            instance._tg_id = tg_id
        if not hasattr(instance, "inline"):
            instance.inline = types.SimpleNamespace(bot=client)
        if not hasattr(instance, "allmodules"):
            instance.allmodules = types.SimpleNamespace()
        try:
            result = ready(client, None)
            if inspect.isawaitable(result):
                await result
        except Exception as e:
            print(f"[COMPAT] client_ready error in {instance.__class__.__name__}: {e}")
        finally:
            setattr(instance, "__binary_client_ready_pending__", False)

    for instance, method, info in list(_deferred_loops):
        if not info.get("autostart"):
            continue
        if hasattr(method, "start"):
            method.start()
