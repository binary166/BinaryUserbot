# MODULE_NAME = "BinaryInfo"
# MODULE_CMD  = ".infocmd"
# MODULE_DESC = "Показать информацию о юзерботе"

try:
    import git
except Exception:
    git = None
from telethon import events
from telethon.tl.types import Message
from telethon.utils import get_display_name
from bot_client import client
from premium_emoji import pe, by_line
import state
import version
import utils
import asyncio

# Функция для рендеринга информации о юзерботе
async def _render_info(inline: bool) -> str:
    try:
        if git:
            repo = git.Repo(search_parent_directories=True)
            diff = repo.git.log([f"HEAD..origin/{version.branch}", "--oneline"])
            upd = "Обновление требуется" if diff else "На данный момент актуально"
        else:
            upd = ""
    except Exception:
        upd = ""

    me_obj = await client.get_me()
    me = f'<b><a href="tg://user?id={me_obj.id}">{get_display_name(me_obj)}</a></b>'
    _version = f'<i>{".".join(list(map(str, list(version.__version__))))}</i>'
    prefix = f"«<code>{'.'}</code>»"  # Префикс команды

    platform = "Платформа"  # Здесь должна быть логика получения платформы

    # Замена эмодзи на иконки
    for emoji, icon in [
        ("🍊", "<emoji document_id=5449599833973203438>🧡</emoji>"),
        ("🍇", "<emoji document_id=5449468596952507859>💜</emoji>"),
        ("❓", "<emoji document_id=5407025283456835913>📱</emoji>"),
        ("🍀", "<emoji document_id=5395325195542078574>🍀</emoji>"),
        ("🦾", "<emoji document_id=5386766919154016047>🦾</emoji>"),
        ("🚂", "<emoji document_id=5359595190807962128>🚂</emoji>"),
        ("🐳", "<emoji document_id=5431815452437257407>🐳</emoji>"),
        ("🕶", "<emoji document_id=5407025283456835913>📱</emoji>"),
        ("🐈‍⬛", "<emoji document_id=6334750507294262724>🐈‍⬛</emoji>"),
        ("✌️", "<emoji document_id=5469986291380657759>✌️</emoji>"),
        ("📻", "<emoji document_id=5471952986970267163>💎</emoji>"),
    ]:
        platform = platform.replace(emoji, icon)

    return (
        f"{pe('star_pe')} <b>BinaryUserbot</b>\n"
        + f"{pe('user')} <b>Владелец:</b> {me}\n"
        + f"{pe('gear')} <b>Версия:</b> {_version}\n"
        + f"{pe('chain')} <b>Ветка:</b> <code>{version.branch}</code>\n"
        + f"{upd}\n"
        + f"{pe('bolt')} <b>Префикс:</b> {prefix}\n"
        + f"{pe('generation')} <b>Время работы:</b> {utils.formatted_uptime()}\n"
        + f"{pe('brain')} <b>Загрузка CPU:</b> <i>~{utils.get_cpu_usage()} %</i>\n"
        + f"{pe('pc')} <b>Использование RAM:</b> <i>~{utils.get_ram_usage()} MB</i>\n"
    )

# Команда для получения информации о юзерботе
@client.on(events.NewMessage(pattern=r"^\.\s*infocmd\s*$", outgoing=True))
async def infocmd(event: Message):
    # Получаем информацию о юзерботе
    info_text = await _render_info(True)
    await event.edit(info_text, parse_mode="html")

# Команда для установки пользовательского сообщения
@client.on(events.NewMessage(pattern=r"^\.\s*setinfo\s+(.*)", outgoing=True))
async def setinfo(event: Message):
    args = event.pattern_match.group(1)
    if not args:
        return await event.reply("Не указаны аргументы для установки сообщения.", parse_mode="html")
    
    # Сохраняем пользовательское сообщение
    state.custom_message = args
    await event.reply("Пользовательское сообщение успешно установлено.", parse_mode="html")

# Команда для получения описания
@client.on(events.NewMessage(pattern=r"^\.\s*binaryinfo\s*$", outgoing=True))
async def binaryinfo(event: Message):
    await event.reply("Это команда для получения информации о юзерботе.", parse_mode="html")

print("[MOD] BinaryInfo загружен")
