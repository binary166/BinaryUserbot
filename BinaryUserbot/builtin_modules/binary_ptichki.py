# MODULE_NAME = "Ptichki"
# MODULE_CMD  = ".ptichka"
# MODULE_DESC = "Генератор птиц 🦅✨"

import json
import random
import aiohttp  # для HTTP-запросов
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from telethon import events
from bot_client import client       # ГЛАВНЫЙ КЛИЕНТ
from premium_emoji import pe, by_line  # премиум-эмодзи
from utils import html               # экранирование HTML
import state                          # глобальное состояние
import settings                       # настройки (если нужно хранить данные)

# Логирование
import logging
logger = logging.getLogger(__name__)

# URL для ресурсов
assets_link = "https://famods.fajox.one/assets"
font_url = f"{assets_link}/impact.ttf"
birds_url = f"{assets_link}/birds/birds.json"

# Функция для получения байтов по URL
async def fetch_bytes(url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            resp.raise_for_status()
            return await resp.read()

# Функция для получения URL птицы
async def get_bird_url() -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(birds_url) as resp:
            birds_list = json.loads(await resp.text())
    return f"{assets_link}/birds/{random.choice(birds_list)}.png"

# Функция для генерации изображения птицы
async def generate_bird(text: str, format: str) -> bytes:
    text = text.upper()
    img_bytes = await fetch_bytes(await get_bird_url())
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    img.thumbnail((512, 512))
    width, height = img.size
    draw = ImageDraw.Draw(img)

    font_bytes = await fetch_bytes(font_url)
    font_size = 55
    min_font_size = 12
    max_width_fraction = 0.9

    font = ImageFont.truetype(BytesIO(font_bytes), font_size)
    text_width = font.getlength(text)

    if text_width > max_width_fraction * width:
        scale = (max_width_fraction * width) / text_width
        font_size = max(int(font_size * scale), min_font_size)
        font = ImageFont.truetype(BytesIO(font_bytes), font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) / 2
    y = height - text_height - (height * 0.05)

    draw.text(
        (x, y),
        text,
        font=font,
        fill="white",
        stroke_width=2,
        stroke_fill="black"
    )

    output = BytesIO()
    img.save(output, format=format.upper())
    output.seek(0)
    output.name = f"ptitchka.{format.lower()}"

    return output

@client.on(events.NewMessage(pattern=r"^\.\s*ptichka(?:\s+(.+))?$", outgoing=True))
async def cmd_ptichka(event):
    """[текст] - Сгенерировать стикер с птицей"""
    args = event.raw_text.split(None, 1)
    text = args[1] if len(args) > 1 else ""
    
    if not text:
        return await event.reply(
            pe("eyes") + " <b>Нужно </b><code>{}{} {}</code>".format(".", "ptichka", "[текст]"),
            parse_mode="html"
        )

    m = await event.reply(pe("generation") + " <i>Генерирую птичку...</i>", parse_mode="html")

    await client.send_file(
        event.chat_id, 
        mime_type="image/webp",
        file=await generate_bird(text, format="webp"),
        reply_to=getattr(event.reply_to, "reply_to_msg_id", None),
    )

    await m.delete()

@client.on(events.NewMessage(pattern=r"^\.\s*ptichka_img(?:\s+(.+))?$", outgoing=True))
async def cmd_ptichka_img(event):
    """[текст] - Сгенерировать фото с птицей"""
    args = event.raw_text.split(None, 1)
    text = args[1] if len(args) > 1 else ""
    
    if not text:
        return await event.reply(
            pe("eyes") + " <b>Нужно </b><code>{}{} {}</code>".format(".", "ptichka_img", "[текст]"),
            parse_mode="html"
        )

    m = await event.reply(pe("generation") + " <i>Генерирую птичку...</i>", parse_mode="html")

    await client.send_file(
        event.chat_id, 
        mime_type="image/png",
        file=await generate_bird(text, format="png"),
        reply_to=getattr(event.reply_to, "reply_to_msg_id", None),
    )

    await m.delete()

print("[MOD] Ptichki загружен")
