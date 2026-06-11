# MODULE_NAME = "yg_circle"
# MODULE_CMD = ".kr"
# MODULE_DESC = "Модуль для конвертации видео в кружочек"

import os
from telethon import events
from bot_client import client
from utils import html

try:
    from premium_emoji import by_line
except Exception:
    def by_line(): return "<i>Binary Userbot</i>"

@client.on(events.NewMessage(pattern=r"^\.kr(?:\s+(.+))?$", outgoing=True))
async def krcmd(event):
    """<reply to video> конвертировать видео в кружочек"""
    reply = await event.get_reply_message()
    if not reply or not reply.video:
        await event.edit("<b><emoji document_id=5210952531676504517>❌</emoji> Ответьте на видео командой <code>.kr</code> для конвертации в кружочек 🎥</b>")
        return
    try:
        await event.edit("<b><emoji document_id=4988080790286894217>🫥</emoji> Обработка...</b>")
        video = await reply.download_media()
        square_video = await crop_to_square(video)
        if square_video:
            await event.edit("<b><emoji document_id=4988080790286894217>🫥</emoji> Отправка...</b>")
            await event.client.send_file(event.to_id, square_video, video_note=True)
    except Exception as e:
        await event.edit(f"<b><emoji document_id=5210952531676504517>❌</emoji> Произошла ошибка при конвертации видео в кружочек: {str(e)}</b>")
    finally:
        if os.path.exists(video):
            os.remove(video)
        if square_video and os.path.exists(square_video):
            os.remove(square_video)
    await event.delete()

async def crop_to_square(video):
    """Обрезать видео до квадратного формата (1:1) с помощью ffmpeg"""
    square_video = f"{video}_square.mp4"
    command = (
        f"ffmpeg -i {video} -vf \"crop='min(in_w,in_h)':'min(in_w,in_h)':'(in_w-out_w)/2':'(in_h-out_h)/2'\" -c:a copy {square_video}"
    )
    os.system(command)
    return square_video if os.path.exists(square_video) else None
