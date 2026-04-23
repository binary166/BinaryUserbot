# MODULE_NAME = "DoxTool"
# MODULE_CMD  = ".dox"
# MODULE_DESC = "Шуточный деанон пользователя с анимированным поиском по 'базам'"

import asyncio
import random
from telethon import events
from telethon.tl.types import PeerUser

from bot_client import client
from premium_emoji import by_line, pe
from utils import html, get_username

REGIONS = [
    "Пиздоболов", "Конченых", "Сыктывкарский", "Воронежский", "Урюпинский",
    "Нижнетагильский", "Бибирево", "Жопинск", "Задрищенск", "Мухосранск",
    "Рязанский", "Оренбургский", "Таганрогский", "Череповецкий",
]

CITIES = [
    "под забором на Арбате", "в канаве у вокзала", "в подворотне на окраине",
    "в коммуналке без света", "в съёмной хрущёвке", "за гаражами",
    "у мусорки у ТЦ", "в подвале рядом с котельной", "на чердаке дома 5",
    "в ЛТП", "в нарко-реабилитационном центре", "в интернате №4",
]

STREETS = [
    "ул. Помойная, 13", "пр. Опущенных, 66", "пер. Глухой, 9",
    "ш. Энтузиастов, нет дома", "ул. Забытая, без номера",
    "ул. Вокзальная, под скамейкой", "пр. Маргинальный, 228",
    "наб. Канавы, 1А", "ул. Пиздец, д.0",
]

SCHOOLS = [
    "Школа №228 коррекционная", "Спецшкола для одарённых (в обратную сторону)",
    "ПТУ «Отчаянье»", "Лицей «Последний шанс»",
    "Гимназия «У помойки»", "Интернат для трудновоспитуемых",
    "Школа-закрытие №13", "ВТУ «Три класса»",
]

PARENT_JOBS = [
    "работает на трассе", "собирает бутылки у вокзала",
    "сидит на мели уже 10 лет", "торгует суррогатом",
    "сторож на стройке за еду", "санитар в морге (по бартеру)",
    "официально безработный с 1998", "бомбила без лицензии",
    "попрошайничает у метро", "продаёт палёную водку",
]

CHARACTERISTICS = [
    ("Телефон",          ["разбит об колено", "утоплен в унитазе", "отобран коллекторами", "заблокирован за неуплату"]),
    ("Доход в месяц",    ["300 руб", "на хлеб не хватает", "минусовой", "«скоро всё будет»"]),
    ("Вредные привычки", ["курит окурки с пола", "нюхает клей", "пьёт одеколон", "всё сразу"]),
    ("Образование",      ["3 класса ЦПШ", "вечерняя школа (не закончил)", "ПТУ на сварщика (отчислен)", "никакого"]),
    ("Семейное положение", ["разведён дважды", "живёт с мамой в 35", "платит алименты троим", "одинок и плачет"]),
    ("Статус",           ["в розыске", "на учёте", "под подпиской", "отрабатывает общественные работы"]),
    ("Судимости",        ["2 условных", "5 административок", "1 по малолетке", "официально — нет"]),
    ("Хобби",            ["ковыряется в носу", "смотрит TikTok 14 часов", "кричит на жену", "пишет доносы"]),
]

SEARCH_STEPS = [
    ("🔍", "Пробиваю номер по базе ГИБДД..."),
    ("📞", "Сканирую Getcontact и HLR-lookup..."),
    ("🏠", "Сверяю адрес по ФМС и ЕГРН..."),
    ("👪", "Ищу родственников в базе ЗАГС..."),
    ("🎓", "Поиск школы и классного журнала..."),
    ("💼", "Пробиваю родителей по СБИС и HH..."),
    ("🏦", "Сверяю с базой должников ФССП..."),
    ("🚔", "Запрашиваю базу МВД и судимости..."),
    ("💳", "Анализирую траты по СБП..."),
    ("📊", "Собираю досье воедино..."),
]


def _bar(pct: float, width: int = 14) -> str:
    filled = int(round(pct / 100 * width))
    return "▰" * filled + "▱" * (width - filled)


async def _get_target(event):
    reply = await event.get_reply_message()
    if reply:
        try:
            ent = await client.get_entity(reply.sender_id)
            return ent
        except Exception:
            pass
    args = event.raw_text.split(None, 1)
    if len(args) > 1:
        q = args[1].strip()
        try:
            if q.lstrip("-").isdigit():
                return await client.get_entity(int(q))
            return await client.get_entity(q.lstrip("@"))
        except Exception:
            return None
    return None


def _fake_phone() -> str:
    return f"+7 ({random.randint(900, 999)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"


def _fake_passport() -> str:
    return f"{random.randint(1000, 9999)} {random.randint(100000, 999999)}"


def _fake_inn() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(12))


def _dossier(target_name: str, username: str) -> str:
    parents_mom = random.choice(PARENT_JOBS)
    parents_dad = random.choice(PARENT_JOBS)
    region      = random.choice(REGIONS)
    city        = random.choice(CITIES)
    street      = random.choice(STREETS)
    school      = random.choice(SCHOOLS)

    chars = random.sample(CHARACTERISTICS, 5)
    char_lines = "\n".join(
        f"├ <b>{k}:</b> <i>{random.choice(v)}</i>"
        for k, v in chars
    )

    return (
        f"💀 <b>Досье собрано</b>\n"
        f"🎯 Цель: <b>{html(target_name)}</b>  ·  <code>{html(username)}</code>\n"
        f"<blockquote>"
        f"├ <b>Телефон:</b>  <code>{_fake_phone()}</code>\n"
        f"├ <b>Паспорт:</b>  <code>{_fake_passport()}</code>\n"
        f"├ <b>ИНН:</b>  <code>{_fake_inn()}</code>\n"
        f"├ <b>Регион:</b>  {region}\n"
        f"├ <b>Город:</b>  найден {city}\n"
        f"├ <b>Адрес:</b>  {street}\n"
        f"├ <b>Школа:</b>  {school}\n"
        f"{char_lines}\n"
        f"└ ─────────────────────"
        f"</blockquote>\n\n"
        f"<b>👩 Мать:</b>  {parents_mom}\n"
        f"<b>👨 Отец:</b>  {parents_dad}\n\n"
        f"Все совпадения случайны.</i>\n\n"
        + by_line()
    )


@client.on(events.NewMessage(pattern=r"^\.(dox|гб|deanon)(?:\s|$)", outgoing=True))
async def cmd_dox(event):
    target = await _get_target(event)
    if target:
        fn = getattr(target, "first_name", "") or ""
        ln = getattr(target, "last_name", "") or ""
        name = (fn + " " + ln).strip() or getattr(target, "title", None) or "Неизвестный"
        username = get_username(target)
    else:
        name = "твой собеседник"
        username = "—"

    total = len(SEARCH_STEPS)
    for i, (icon, step) in enumerate(SEARCH_STEPS, 1):
        pct = i / total * 100
        try:
            await event.edit(
                f"{icon} <b>Деанон:</b> <i>{html(name)}</i>\n\n"
                f"<blockquote>"
                f"<code>{_bar(pct)}</code>  {pct:.0f}%\n\n"
                f"{step}"
                f"</blockquote>\n\n"
                f"<i>Шаг {i}/{total}</i>",
                parse_mode="html",
            )
        except Exception:
            pass
        await asyncio.sleep(random.uniform(0.7, 1.2))

    try:
        await event.edit(_dossier(name, username), parse_mode="html")
    except Exception as e:
        print(f"[dox] {e}")
        await event.edit(f"❌ Ошибка: <code>{html(str(e)[:200])}</code>", parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.dinfo$", outgoing=True))
async def cmd_dinfo(event):
    skull = pe("skull")
    await event.edit(
        f"{skull} <b>DoxTool</b>\n\n"
        f"<blockquote>"
        f"🎭 Шуточный модуль для развлечения в чатах.\n\n"
        f"<b>Команды:</b>\n"
        f"• <code>.dox</code> / <code>.гб</code> <i>(реплай / @юзер)</i>\n"
        f"   Фейковый «деанон» с анимацией поиска и рандомным досье\n"
        f"• <code>.deanon</code> — отговорка бота от реального деанона\n"
        f"• <code>.dinfo</code> — это сообщение"
        f"</blockquote>\n\n"
        f"<i>Все данные в досье — сгенерированы рандомно. Никакого реального "
        f"деанона модуль не производит. Только для прикола!</i>\n\n"
        + by_line(),
        parse_mode="html",
    )
