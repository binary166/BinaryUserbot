import inspect


class Strings(dict):
    def __call__(self, key=None, *args, **kwargs):
        if key is None:
            return self
        return self.get(key, key)


class Module:
    strings = {"name": "Unknown"}

    def get_prefix(self):
        return "."

    def lookup(self, *args, **kwargs):
        return None

    def get(self, key, default=None):
        try:
            import settings
            return settings.get(f"{self.__class__.__name__}.{key}", default)
        except Exception:
            return default

    def set(self, key, value):
        try:
            import settings
            settings.set_val(f"{self.__class__.__name__}.{key}", value)
        except Exception:
            pass


class ConfigValue:
    def __init__(self, option, default=None, doc=None, validator=None, **kwargs):
        self.option = option
        self.default = default
        self.doc = doc
        self.validator = validator
        self.kwargs = kwargs


class ModuleConfig(dict):
    def __init__(self, *values, **kwargs):
        super().__init__()
        for value in values:
            if isinstance(value, ConfigValue):
                self[value.option] = value.default
            elif isinstance(value, (tuple, list)) and value:
                self[value[0]] = value[1] if len(value) > 1 else None
        self.update(kwargs)


class validators:
    class Hidden:
        pass

    class String:
        pass

    class Boolean:
        pass

    class Integer:
        pass

    class Choice:
        def __init__(self, choices):
            self.choices = choices


import uuid

import json
import os

class Database:
    def __init__(self):
        self.path = ".runtime/hikka_db.json"
        self.data = {}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                pass
    def get(self, module, key, default=None):
        return self.data.get(module, {}).get(key, default)
    def set(self, module, key, value):
        if module not in self.data:
            self.data[module] = {}
        self.data[module][key] = value
        self.save()
    def save(self):
        os.makedirs(".runtime", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f)

db_instance = Database()

inline_manager = None

class InlineManager:
    def __init__(self, client):
        self.client = client
        self.forms = {}
        
    async def form(self, text, reply_markup, message, **kwargs):
        import manager_bot
        if not manager_bot.manager_client:
            await message.edit("   -.  `.sb`.")
            return

        try:
            bot_me = await manager_bot.manager_client.get_me()
            bot_username = bot_me.username
        except Exception:
            await message.edit("-  .")
            return

        form_id = str(uuid.uuid4())
        
        from telethon import Button
        telethon_buttons = []
        for row in reply_markup:
            btn_row = []
            for btn in row:
                cb_id = str(uuid.uuid4())[:16] # limit data size
                self.forms[cb_id] = {
                    "action": btn.get("callback"),
                    "input_prompt": btn.get("input"),
                    "handler": btn.get("handler"),
                    "args": btn.get("args", ()),
                    "kwargs": btn.get("kwargs", {})
                }
                btn_row.append(Button.inline(btn["text"], cb_id.encode('utf-8')))
            telethon_buttons.append(btn_row)
            
        if not hasattr(manager_bot, "INLINE_FORMS"):
            manager_bot.INLINE_FORMS = {}
            
        manager_bot.INLINE_FORMS[form_id] = {
            "text": text,
            "buttons": telethon_buttons
        }
        
        try:
            results = await self.client.inline_query(bot_username, f"form:{form_id}")
            if results:
                await results[0].click(message.chat_id, reply_to=message.reply_to_msg_id)
                try:
                    await message.delete()
                except Exception:
                    pass
        except Exception as e:
            err_msg = f"Inline form error: {e} (make sure companion bot has inline mode enabled in @BotFather!)"
            try:
                await message.edit(err_msg)
            except Exception:
                await self.client.send_message(message.chat_id, err_msg, reply_to=message.reply_to_msg_id)

    class Boolean:
        pass

    class Integer:
        pass

    class Choice:
        def __init__(self, choices):
            self.choices = choices


def _normal_name(name: str) -> str:
    name = str(name or "").strip()
    return name[1:] if name.startswith(".") else name


def command(*decorator_args, **decorator_kwargs):
    def _decorate(func):
        names = []
        base = getattr(func, "__name__", "")
        if base.endswith("cmd"):
            names.append(base[:-3])

        explicit = decorator_kwargs.get("name") or decorator_kwargs.get("command")
        if explicit:
            names.append(explicit)

        aliases = decorator_kwargs.get("alias") or decorator_kwargs.get("aliases")
        if isinstance(aliases, str):
            names.append(aliases)
        elif aliases:
            names.extend(list(aliases))

        if not names and base:
            names.append(base)

        deduped = []
        seen = set()
        for name in names:
            normalized = _normal_name(name)
            if normalized and normalized not in seen:
                seen.add(normalized)
                deduped.append(normalized)

        func._binary_command_names = deduped
        func._binary_doc = (
            decorator_kwargs.get("ru_doc")
            or decorator_kwargs.get("doc")
            or inspect.getdoc(func)
            or ""
        )
        return func

    if decorator_args and callable(decorator_args[0]) and len(decorator_args) == 1 and not decorator_kwargs:
        return _decorate(decorator_args[0])
    return _decorate


def watcher(*args, **kwargs):
    def _decorate(func):
        func._binary_watcher = {"args": args, "kwargs": kwargs}
        return func

    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return _decorate(args[0])
    return _decorate


def loop(interval=1, autostart=False, **kwargs):
    def _decorate(func):
        func._binary_loop = {
            "interval": interval,
            "autostart": autostart,
            **kwargs,
        }
        return func

    return _decorate


def tds(cls):
    return cls


def owner(func=None, **kwargs):
    return command(func) if callable(func) else command(**kwargs)


def unrestricted(func=None, **kwargs):
    return command(func) if callable(func) else command(**kwargs)


def tag(*args, **kwargs):
    def _decorate(obj):
        obj._binary_tags = {"args": args, "kwargs": kwargs}
        return obj
    return _decorate


def callback_handler(*args, **kwargs):
    return command(*args, **kwargs)


def inline_handler(*args, **kwargs):
    return command(*args, **kwargs)
