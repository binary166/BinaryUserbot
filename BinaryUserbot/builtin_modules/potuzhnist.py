# MODULE_NAME = "Потужність"
# MODULE_CMD  = ".pm"
# MODULE_DESC = "Вимірювання потужності юзера та режим української потужності"

import random
import hashlib

from telethon import events
from bot_client import client
from utils import html


PM_MODE = False


PREMIUM_EMOJI_IDS = [
    5359764051742192201,
    5397743730281182837,
    5397671884068247533,
    5352930758774252728,
    5402456662319588196,
    5262780267109582053,
    5285418438431365137,
    5282882049789676444,
    5375337405588985863,
    5375531508045992457,
    5375285616873327710,
    5375595150871384727,
    5375479697855501783,
    5375432861237137277,
    5375404003351877002,
    5375259782645044214,
]


UKR_PHRASES = [
    "Слава Україні, потужність активовано!",
    "Рівень потужності вийшов за межі здорового глузду.",
    "Українська енергія заряджає це повідомлення.",
    "Паляниця, борщ і максимальна потужність!",
    "Цей текст тепер офіційно потужний.",
    "Козацький вайб зафіксовано.",
    "Жовто-блакитна хвиля накрила чат.",
    "Потужність росте, прапори майорять.",
    "Незламність увімкнена.",
    "Український режим повідомлення активний.",
]


POWER_TITLES = [
    "Легендарний козак",
    "Паляничний чемпіон",
    "Борщовий магістр",
    "Жовто-блакитний титан",
    "Незламний герой чату",
    "Карпатський демон потужності",
    "Дніпровський енергетик",
    "Галицький ультравайбер",
    "Київський потужнометр",
    "Запорізький характерник",
]


def tg_emoji(emoji_id: int, fallback: str = "🇺🇦") -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def premium_pack(count: int = 4) -> str:
    ids = random.sample(PREMIUM_EMOJI_IDS, min(count, len(PREMIUM_EMOJI_IDS)))
    return " ".join(tg_emoji(i) for i in ids)


def get_seed(value: str) -> int:
    raw = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()
    return int(raw[:12], 16)


def stat(seed: int, salt: int, min_value: int = 1, max_value: int = 100) -> int:
    random.seed(seed + salt)
    return random.randint(min_value, max_value)


def bar(value: int, size: int = 10) -> str:
    filled = round(value / 100 * size)
    empty = size - filled
    return "🟨" * filled + "⬛" * empty


async def send_html(event, text: str):
    await event.edit(text, parse_mode="html", link_preview=False)


@client.on(events.NewMessage(pattern=r"^\.pm(?:\s+(.+))?$", outgoing=True))
async def cmd_pm(event):
    global PM_MODE

    arg = event.pattern_match.group(1)
    arg = arg.strip().lower() if arg else ""

    if arg in ("старт", "start", "on", "вкл"):
        PM_MODE = True
        return await send_html(
            event,
            f"🇺🇦 <b>Режим потужності увімкнено</b> 🇺🇦\n\n"
            f"{premium_pack(5)}\n\n"
            f"Тепер кожне твоє звичайне повідомлення буде заряджене "
            f"<b>українською потужністю</b>.\n\n"
            f"<code>.pm стоп</code> — вимкнути режим."
        )

    if arg in ("стоп", "stop", "off", "выкл", "викл"):
        PM_MODE = False
        return await send_html(
            event,
            f"🛑 <b>Режим потужності вимкнено</b>\n\n"
            f"🇺🇦 Прапори складено, але сила залишилась у серці."
        )

    if not event.is_reply:
        return await send_html(
            event,
            "🇺🇦 <b>Потужнометр</b>\n\n"
            "Використання:\n"
            "<code>.pm</code> — відповіддю на повідомлення, щоб виміряти потужність юзера\n"
            "<code>.pm старт</code> — увімкнути режим потужних повідомлень\n"
            "<code>.pm стоп</code> — вимкнути режим"
        )

    reply = await event.get_reply_message()

    try:
        sender = await reply.get_sender()
    except Exception:
        sender = None

    user_id = getattr(sender, "id", None) or reply.sender_id or reply.id
    first_name = getattr(sender, "first_name", "") or ""
    last_name = getattr(sender, "last_name", "") or ""
    username = getattr(sender, "username", None)

    display_name = (first_name + " " + last_name).strip()
    if not display_name:
        display_name = f"ID {user_id}"

    if username:
        display_name += f" (@{username})"

    seed = get_seed(str(user_id))

    potuzhnist = stat(seed, 1, 50, 100)
    nezlamnist = stat(seed, 2, 1, 100)
    boroshno = stat(seed, 3, 1, 100)
    salo = stat(seed, 4, 1, 100)
    bandera = stat(seed, 5, 1, 100)
    palyanytsya = stat(seed, 6, 1, 100)
    ukr_energy = stat(seed, 7, 1, 100)

    total = round(
        (
            potuzhnist
            + nezlamnist
            + boroshno
            + salo
            + bandera
            + palyanytsya
            + ukr_energy
        ) / 7
    )

    random.seed(seed)
    title = random.choice(POWER_TITLES)
    phrase = random.choice(UKR_PHRASES)

    result = (
        f"🇺🇦 {premium_pack(4)} 🇺🇦\n\n"
        f"<b>ПОТУЖНОМЕТР ЗАПУЩЕНО</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Користувач:</b> <code>{html(display_name)}</code>\n"
        f"🏷 <b>Титул:</b> <b>{html(title)}</b>\n\n"
        f"⚡ <b>Загальна потужність:</b> <code>{total}%</code>\n"
        f"{bar(total)}\n\n"
        f"📊 <b>Статистика потужності:</b>\n\n"
        f"🇺🇦 <b>Потужність:</b> <code>{potuzhnist}%</code>\n"
        f"{bar(potuzhnist)}\n\n"
        f"🛡 <b>Незламність:</b> <code>{nezlamnist}%</code>\n"
        f"{bar(nezlamnist)}\n\n"
        f"🥖 <b>Паляничність:</b> <code>{palyanytsya}%</code>\n"
        f"{bar(palyanytsya)}\n\n"
        f"🥣 <b>Борщова енергія:</b> <code>{boroshno}%</code>\n"
        f"{bar(boroshno)}\n\n"
        f"🥓 <b>Сальний резерв:</b> <code>{salo}%</code>\n"
        f"{bar(salo)}\n\n"
        f"🔥 <b>Бандерометр:</b> <code>{bandera}%</code>\n"
        f"{bar(bandera)}\n\n"
        f"💙💛 <b>Український вайб:</b> <code>{ukr_energy}%</code>\n"
        f"{bar(ukr_energy)}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 <i>{html(phrase)}</i>\n\n"
        f"🇺🇦 <b>Висновок:</b> користувач має "
        f"<b>{total}% потужності</b> та офіційно заряджений "
        f"жовто-блакитною енергією."
    )

    await send_html(event, result)

@client.on(events.NewMessage(outgoing=True))
async def pm_auto_mode(event):
    global PM_MODE

    if not PM_MODE:
        return

    msg = event.message
    text = msg.raw_text or ""

    if not text:
        return

    clean = text.strip()

    if not clean:
        return

    # Не трогаем команды юзербота
    if clean.startswith("."):
        return

    # Защита от повторной обработки
    if "🇺🇦" in clean and "💙💛" in clean:
        return

    phrases = [
        "Слава Україні",
        "потужність",
        "незламність",
        "паляниця",
        "український вайб",
        "жовто-блакитна сила",
        "козацька енергія",
        "борщ зарядив",
        "сила на максимумі",
        "потужно",
    ]

    flags = [
        "🇺🇦",
        "💙💛",
        "🇺🇦🇺🇦",
        "💛💙",
    ]

    words = clean.split()

    if len(words) <= 1:
        middle_text = (
            f"{random.choice(flags)} "
            f"{premium_pack(random.randint(1, 3))} "
            f"{html(clean)} "
            f"{random.choice(phrases)} "
            f"{premium_pack(random.randint(1, 3))} "
            f"{random.choice(flags)}"
        )
    else:
        result = []

        for index, word in enumerate(words):
            result.append(html(word))

            # Вставка между словами, но не после последнего слова
            if index != len(words) - 1:
                chance = random.randint(1, 100)

                if chance <= 35:
                    result.append(random.choice(flags))

                elif chance <= 60:
                    result.append(premium_pack(random.randint(1, 2)))

                elif chance <= 82:
                    result.append(random.choice(phrases))

                else:
                    result.append(
                        f"{random.choice(flags)} "
                        f"{premium_pack(1)} "
                        f"{random.choice(phrases)}"
                    )

        middle_text = " ".join(result)

    if len(middle_text) > 3900:
        return

    try:
        await event.edit(
            middle_text,
            parse_mode="html",
            link_preview=False
        )
    except Exception:
        pass