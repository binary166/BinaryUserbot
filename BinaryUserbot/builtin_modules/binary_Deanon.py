# MODULE_NAME = "Deanon"
# MODULE_CMD  = ".deanon"
# MODULE_DESC = "Поиск по @UserName/Number/Email"

from telethon import events
from telethon.tl.types import Message
from bot_client import client
from premium_emoji import pe, by_line
import state

# Инициализация глобального состояния для отслеживания количества попыток
if not hasattr(state, "deanon_flag"):
    state.deanon_flag = 0

@client.on(events.NewMessage(pattern=r"^\.\s*deanon(?:\s+(.+))?$", outgoing=True))
async def cmd_deanon(event: Message):
    """Поиск по @UserName/Number/Email"""
    await event.delete()  # Удаляем исходное сообщение

    # Увеличиваем счетчик попыток
    state.deanon_flag += 1

    # Проверяем количество попыток
    if state.deanon_flag <= 1:
        response_text = f'{pe("lock")} <b>Нельзя таким заниматься. Интернет - герой.</b>\n\n' + by_line()
    else:
        response_text = f'{pe("lock")} <b>Еще раз и удалю аккаунт за такие приколы.</b>\n\n' + by_line()

    # Отправляем ответ пользователю
    await client.send_message(event.chat_id, response_text, parse_mode="html")

print("[MOD] Deanon загружен")