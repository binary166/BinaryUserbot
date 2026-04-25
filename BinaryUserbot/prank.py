import asyncio
from utils import html
from premium_emoji import pe


async def run_prank(chat_id: int, target_name: str):
    from bot_client import client

    skull = pe("skull")
    bolt  = pe("bolt")
    alien = pe("alien")

    msg = await client.send_message(
        chat_id,
        f"{alien} <b>BinaryShoser load...</b>",
        parse_mode="html"
    )
    await asyncio.sleep(5)

    await msg.edit(
        f"{skull} <b>Working...\n\n"
        f"📡 Активных сессий: <b>810</b>\n\n"
        f"{bolt} <b>Запускаю отправку жалоб...</b>",
        parse_mode="html"
    )
    await asyncio.sleep(5)

    steps = list(range(0, 101, 5))
    delay_per_step = 15.0 / len(steps)
    for pct in steps:
        filled = int(pct / 5)
        empty  = 20 - filled
        bar    = "█" * filled + "░" * empty
        await msg.edit(
            f"{skull} <b>Target:</b> {html(target_name)}\n\n"
            f"📡 Активных сессий: <b>810</b>\n\n"
            f"📨 Отправка жалоб...\n"
            f"<code>[{bar}]</code>  <b>{pct}%</b>",
            parse_mode="html"
        )
        await asyncio.sleep(delay_per_step)

    await asyncio.sleep(1)
    try:
        await msg.delete()
    except Exception:
        pass
    await client.send_message(chat_id, "😂 бро, это была добрая шутка)", parse_mode="html")
