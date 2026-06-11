# MODULE_NAME = "Executor"
# MODULE_CMD  = ".exec"
# MODULE_DESC = "Выполнение Python-кода прямо из чата (.exec <code>)"

import sys
import time
import html as _html
import asyncio
import traceback
import telethon
from io import StringIO

from telethon import events
from bot_client import client
from premium_emoji import by_line
import settings

_HIDE_PHONE_KEY = "exec_hide_phone"


async def _meval(code: str, glb: dict, **kwargs):
    """Минимальный async-eval: оборачиваем код в async-функцию и выполняем."""
    indented = "\n".join("    " + line for line in code.splitlines())
    wrapper = f"async def __aexec(__locals__):\n"
    for k in kwargs:
        wrapper += f"    {k} = __locals__['{k}']\n"
    wrapper += indented + "\n"
    # Преобразуем последнее выражение в return, если оно валидно
    try:
        import ast
        tree = ast.parse(code)
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            lines = code.splitlines()
            last = ast.get_source_segment(code, tree.body[-1])
            if last is not None:
                # Пересобираем: всё кроме последнего + return last
                start_lineno = tree.body[-1].lineno - 1
                head = "\n".join(lines[:start_lineno])
                ret_block = "return (" + last + ")"
                head_indented = "\n".join("    " + l for l in head.splitlines())
                ret_indented = "\n".join("    " + l for l in ret_block.splitlines())
                wrapper = f"async def __aexec(__locals__):\n"
                for k in kwargs:
                    wrapper += f"    {k} = __locals__['{k}']\n"
                if head_indented.strip():
                    wrapper += head_indented + "\n"
                wrapper += ret_indented + "\n"
    except Exception:
        pass

    loc = {}
    exec(wrapper, glb, loc)
    return await loc["__aexec"](kwargs)


@client.on(events.NewMessage(pattern=r"^\.exec(?:\s+([\s\S]+))?$", outgoing=True))
async def cmd_exec(event):
    code = (event.pattern_match.group(1) or "").strip()
    if not code:
        await event.edit(
            "🚫 <b>Использование:</b> <code>.exec [python код]</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    await event.edit("🔄 <b>Выполняю код...</b>", parse_mode="html")

    reply = await event.get_reply_message()
    me = await client.get_me()

    sandbox = {
        "message": event,
        "event":   event,
        "m":       event,
        "client":  client,
        "c":       client,
        "reply":   reply,
        "r":       reply,
        "chat":    await event.get_chat(),
        "me":      me,
        "telethon": telethon,
        "tl":      telethon.tl,
        "f":       telethon.tl.functions,
        "asyncio": asyncio,
    }

    old_stdout = sys.stdout
    buf = sys.stdout = StringIO()
    cerr = False
    res = None
    try:
        res = await _meval(code, globals(), **sandbox)
        out = buf.getvalue().strip()
    except Exception:
        out = traceback.format_exc().strip()
        cerr = True
    finally:
        sys.stdout = old_stdout

    out = str(out)
    res_str = "" if res is None else str(res)

    if settings.get(_HIDE_PHONE_KEY, True) and getattr(me, "phone", None):
        mask = "never gonna give you up"
        for ph in (("+" + me.phone), me.phone):
            out = out.replace(ph, mask)
            res_str = res_str.replace(ph, mask)

    parts = [
        f"💻 <b>Код:</b>\n<pre>{_html.escape(code)}</pre>",
    ]
    if out:
        head = "🚫 Ошибка" if cerr else "✅ Результат"
        parts.append(f"<b>{head}:</b>\n<pre>{_html.escape(out)}</pre>")
    if res is not None:
        parts.append(f"💾 <b>Код вернул:</b>\n<pre>{_html.escape(res_str)}</pre>")

    elapsed = round(time.perf_counter() - getattr(event, "_t0", time.perf_counter()), 5)
    parts.append(f"⏳ <i>Выполнен за {elapsed}s</i>\n\n" + by_line())

    text = "\n\n".join(parts)
    if len(text) > 4000:
        text = text[:4000] + "\n…<i>обрезано</i>\n\n" + by_line()

    await event.edit(text, parse_mode="html", link_preview=False)


@client.on(events.NewMessage(pattern=r"^\.exechide(?:\s+(on|off))?$", outgoing=True))
async def cmd_exec_hide(event):
    arg = (event.pattern_match.group(1) or "").lower()
    if arg in ("on", "off"):
        settings.set_val(_HIDE_PHONE_KEY, arg == "on")
    cur = "вкл" if settings.get(_HIDE_PHONE_KEY, True) else "выкл"
    await event.edit(
        f"🔒 <b>Скрытие телефона в .exec:</b> <code>{cur}</code>\n"
        f"<i>Использование:</i> <code>.exechide on|off</code>\n\n" + by_line(),
        parse_mode="html",
    )
