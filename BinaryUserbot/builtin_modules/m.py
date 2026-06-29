# MODULE_NAME = "Кибер-Оракул"
# MODULE_CMD  = ".oracle"
# MODULE_DESC = "Анализ цифровой ауры сообщения"

import asyncio
import random

from telethon import events

from bot_client import client
from config import LOADING
from premium_emoji import by_line, pe


@client.on(events.NewMessage(pattern=r"^\.\s*oracle$", outgoing=True))
async def oracle_handler(event):
    if not event.is_reply:
        await event.edit(
            f"{pe('warning')} <b>Ошибка:</b> Нужен ответ на сообщение!",
            parse_mode="html",
        )
        return

    try:
        await event.edit(
            f"{LOADING} <b>Подключение к ноосфере...</b>",
            parse_mode="html",
        )
        await asyncio.sleep(1.5)

        reply = await event.get_reply_message()
        text = reply.text or ""
        words_count = len(text.split())

        vibes = [
            "Позитивная",
            "Токсичная",
            "Нейтральная",
            "Крипто-энергия",
            "Админский вайб",
        ]
        predictions = [
            "Это сообщение станет мемом в узких кругах.",
            "Его прочитают, но забудут через 5 минут.",
            "Оно вызовет бурную дискуссию в комментариях.",
            "Будет переслано в Избранное как минимум один раз.",
            "Удалено автором в порыве рефлексии.",
        ]

        res = (
            f"{pe('eye')} <b>Результат сканирования:</b>\n\n"
            f"{pe('brain')} <b>Аура:</b> <code>{random.choice(vibes)}</code>\n"
            f"{pe('bolt')} <b>Мощность:</b> <code>{len(text) * 1.5:.1f} Ghz</code>\n"
            f"{pe('robot')} <b>Слов:</b> <code>{words_count}</code>\n"
            f"---\n"
            f"🔮 <b>Прогноз:</b> <i>{random.choice(predictions)}</i>\n\n"
            + by_line()
        )

        await event.edit(res, parse_mode="html")
    except Exception as e:
        await event.edit(
            f"{pe('error')} <b>Сбой системы:</b>\n<code>{str(e)}</code>",
            parse_mode="html",
        )
