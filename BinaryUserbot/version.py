from config import BOT_VERSION


def _parse_version(value: str) -> tuple[int, ...]:
    parts = []
    for item in str(value).lstrip("vV").split("."):
        try:
            parts.append(int(item))
        except ValueError:
            break
    return tuple(parts or [0])


__version__ = _parse_version(BOT_VERSION)
branch = "main"
