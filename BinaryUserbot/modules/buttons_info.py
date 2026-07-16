from .. import loader, utils
from telethon.tl.types import (
    KeyboardButtonCallback,
    KeyboardButtonUrl,
    KeyboardButtonSwitchInline,
    KeyboardButton
)

def pe(emoji: str, eid: str) -> str:
    return f'<emoji document_id="{eid}">{emoji}</emoji>'

# Эмодзи для оформления
E_INFO = pe('ℹ️', '6028435952299413210')
E_ERROR = pe('❌', '5472164874886846699')
E_STAR = pe('⭐', '5982845664122391696')
E_LINK = pe('🔗', '5963103826075456248')
E_BTN = pe('🔘', '5886285355279193209')

@loader.tds
class ButtonsInfoMod(loader.Module):
    """Показывает информацию о кнопках в сообщении"""
    strings = {"name": "ButtonsInfo"}

    async def кнопкиcmd(self, message):
        """<reply> - Вывести информацию о кнопках в отвеченном сообщении"""
        if not message.is_reply:
            await utils.answer(message, f"{E_ERROR} <b>Ответьте на сообщение с кнопками!</b>")
            return

        reply = await message.get_reply_message()
        markup = reply.reply_markup

        if not markup or not hasattr(markup, 'rows'):
            await utils.answer(message, f"{E_ERROR} <b>В этом сообщении нет инлайн-кнопок.</b>")
            return

        text = f"{E_INFO} <b>Информация о кнопках:</b>\n\n"

        for i, row in enumerate(markup.rows):
            text += f"<b>{E_STAR} Ряд {i + 1}:</b>\n"
            for j, btn in enumerate(row.buttons):
                text += f"  <b>{j + 1}.</b> {E_BTN} <b>Текст:</b> <code>{btn.text}</code>\n"

                if isinstance(btn, KeyboardButtonCallback):
                    try:
                        data = btn.data.decode('utf-8') if isinstance(btn.data, bytes) else btn.data
                    except UnicodeDecodeError:
                        data = str(btn.data)
                    text += f"     ├ <b>Тип:</b> <code>Callback</code>\n     └ <b>Data:</b> <code>{data}</code>\n"

                elif isinstance(btn, KeyboardButtonUrl):
                    text += f"     ├ <b>Тип:</b> <code>URL</code>\n     └ <b>{E_LINK} Link:</b> {btn.url}\n"

                elif isinstance(btn, KeyboardButtonSwitchInline):
                    text += f"     ├ <b>Тип:</b> <code>Switch Inline</code>\n     └ <b>Query:</b> <code>{btn.query}</code>\n"

                elif isinstance(btn, KeyboardButton):
                    text += f"     └ <b>Тип:</b> <code>Обычная кнопка (Reply)</code>\n"

                else:
                    text += f"     └ <b>Тип:</b> <code>{type(btn).__name__}</code>\n"
            text += "\n"

        if len(text) > 4096:
            text = text[:4090] + "..."

        await utils.answer(message, text)
