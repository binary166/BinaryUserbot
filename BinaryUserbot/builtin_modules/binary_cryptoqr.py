# MODULE_NAME = "CryptoQR"
# MODULE_CMD  = ".cqr"
# MODULE_DESC = "Создание QR код в стиле CryptoBot"

import asyncio
import logging
from urllib.parse import quote_plus
from telethon import events
from bot_client import client
from premium_emoji import pe, by_line
from utils import html
import state

logger = logging.getLogger(__name__)

@client.on(events.NewMessage(pattern=r"^\.\s*cqr(?:\s+(.+))?$", outgoing=True))
async def cmd_cqr(event):
    """Создать QRcode"""
    
    # Получаем аргументы команды
    arg = (event.pattern_match.group(1) or "").strip()
    
    # Проверяем, есть ли аргументы
    if not arg:
        return await event.edit(
            f'{pe("lock")} <b>CryptoQR</b>\n\n'
            f'Использование: <code>.cqr текст или ссылка</code>',
            parse_mode="html",
        )

    # Уведомляем о начале создания QR-кода
    m = await event.edit(f'{pe("bolt")} <b>Создаю QR-код...</b>', parse_mode="html")

    # Отправляем QR-код
    await client.send_file(
        event.chat_id,
        f"https://qr.crypt.bot/?url={quote_plus(arg)}",
        force_document=True,
        caption=f'{pe("pc")} <b>Текст:</b> <code>{html(arg)}</code>\n\n{by_line()}',
        parse_mode="html",
    )
    
    # Удаляем уведомление о создании
    await m.delete()

print("[MOD] CryptoQR загружен")
