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
