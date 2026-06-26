# MODULE_NAME = "RPSgame"
# MODULE_CMD  = ".rps"
# MODULE_DESC = "Камень-Ножницы-Бумага против бота: с анимацией, статистикой и премиум-эмодзи"

import random
import asyncio
from telethon import events
from bot_client import client
from premium_emoji import by_line
import settings

# ───────────────────────────── константы ─────────────────────────────

CHOICES = ("rock", "scissors", "paper")

# что чем бьётся
BEATS = {
    "rock":     "scissors",
    "scissors": "paper",
    "paper":    "rock",
}

EMOJI = {
    "rock":     "🪨",
    "scissors": "✂️",
    "paper":    "📄",
}

NAME_RU = {
    "rock":     "Камень",
    "scissors": "Ножницы",
    "paper":    "Бумага",
}

# алиасы пользовательского ввода → канон
ALIASES = {
    "rock": "rock", "r": "rock", "камень": "rock", "к": "rock", "🪨": "rock",
    "scissors": "scissors", "s": "scissors", "ножницы": "scissors", "н": "scissors", "✂️": "scissors", "✂": "scissors",
    "paper": "paper", "p": "paper", "бумага": "paper", "б": "paper", "📄": "paper",
    "random": "random", "rand": "random", "?": "random", "рандом": "random",
}

ANIM_FRAMES = ["🪨", "📄", "✂️", "🪨", "📄", "✂️"]

STATS_KEY = "rps_stats"


def _stats() -> dict:
    s = settings.get(STATS_KEY) or {}
    for k in ("wins", "losses", "draws"):
        s.setdefault(k, 0)
    return s


def _save_stats(s: dict) -> None:
    settings.set_val(STATS_KEY, s)


def _winner(p: str, b: str) -> str:
    """'win' / 'lose' / 'draw' с точки зрения игрока."""
    if p == b:
        return "draw"
    return "win" if BEATS[p] == b else "lose"


def _parse(arg: str | None) -> str | None:
    if not arg:
        return "random"
    return ALIASES.get(arg.lower().strip())


# ───────────────────────────── команды ─────────────────────────────

@client.on(events.NewMessage(pattern=r"^\.rps(?:\s+(.+))?$", outgoing=True))
async def rps_play(event):
    arg = (event.pattern_match.group(1) or "").strip()
    choice = _parse(arg)

    if choice is None:
        await event.edit(
            "🎮 <b>Камень-Ножницы-Бумага</b>\n\n"
            "Использование: <code>.rps [камень|ножницы|бумага|рандом]</code>\n"
            "Без аргумента — случайный выбор.\n\n"
            "Статистика: <code>.rpsстат</code>\n"
            "Сброс: <code>.rpsсброс</code>\n\n" + by_line(),
            parse_mode="html",
        )
        return

    player_random = (choice == "random")
    if player_random:
        choice = random.choice(CHOICES)

    bot_choice = random.choice(CHOICES)

    # анимация «трясём кулаком»
    for f in ANIM_FRAMES:
        try:
            await event.edit(f"<b>🎲 Бросаем...</b> {f}", parse_mode="html")
        except Exception:
            pass
        await asyncio.sleep(0.35)

    result = _winner(choice, bot_choice)

    s = _stats()
    if result == "win":
        s["wins"] += 1
        head = "🏆 <b>Победа!</b>"
    elif result == "lose":
        s["losses"] += 1
        head = "💀 <b>Поражение.</b>"
    else:
        s["draws"] += 1
        head = "🤝 <b>Ничья.</b>"
    _save_stats(s)

    you_line = f"{EMOJI[choice]} <b>Ты:</b> {NAME_RU[choice]}"
    if player_random:
        you_line += " <i>(рандом)</i>"

    text = (
        f"{head}\n\n"
        f"{you_line}\n"
        f"{EMOJI[bot_choice]} <b>Бот:</b> {NAME_RU[bot_choice]}\n\n"
        f"📊 <b>Счёт:</b> {s['wins']}W / {s['losses']}L / {s['draws']}D\n\n"
        + by_line()
    )
    await event.edit(text, parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.rpsстат$", outgoing=True))
async def rps_stats(event):
    s = _stats()
    total = s["wins"] + s["losses"] + s["draws"]
    wr = (s["wins"] / total * 100) if total else 0.0
    await event.edit(
        "📊 <b>Статистика RPS</b>\n\n"
        f"🏆 Побед: <b>{s['wins']}</b>\n"
        f"💀 Поражений: <b>{s['losses']}</b>\n"
        f"🤝 Ничьих: <b>{s['draws']}</b>\n"
        f"🎯 Сыграно: <b>{total}</b>\n"
        f"📈 Винрейт: <b>{wr:.1f}%</b>\n\n" + by_line(),
        parse_mode="html",
    )


@client.on(events.NewMessage(pattern=r"^\.rpsсброс$", outgoing=True))
async def rps_reset(event):
    _save_stats({"wins": 0, "losses": 0, "draws": 0})
    await event.edit(
        "🧹 <b>Статистика RPS сброшена.</b>\n\n" + by_line(),
        parse_mode="html",
    )
