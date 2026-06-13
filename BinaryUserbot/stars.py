import asyncio
import re
import state
from config import STARS_BOT_ID, STARS_CHAT_ID, STARS_TIMER_SEC
from utils import html, send_me
from premium_emoji import by_line

from telethon.tl.functions.payments import GetPaymentFormRequest, SendStarsFormRequest
from telethon.tl.types import InputInvoiceSlug


def stars_extract_value(text: str) -> int | None:
    m = re.search(r"Всего\s+собрано[:\s]*\*{0,2}(\d+)\*{0,2}", text)
    return int(m.group(1)) if m else None


def stars_extract_invoice_url(message) -> str | None:
    try:
        for row in message.reply_markup.rows:
            for btn in row.buttons:
                url = getattr(btn, "url", "") or ""
                if "$" in url and "t.me" in url:
                    return url
    except Exception:
        pass
    return None


async def stars_pay_invoice(url: str):
    from bot_client import client
    try:
        slug          = url.split("$", 1)[-1].strip()
        invoice_input = InputInvoiceSlug(slug=slug)
        form          = await client(GetPaymentFormRequest(invoice=invoice_input))
        await client(SendStarsFormRequest(form_id=form.form_id, invoice=invoice_input))
        await send_me(
            f"⭐ <b>Stars AutoPay</b>\n\n✅ Инвойс оплачен!\n"
            f"💳 <code>{html(slug)}</code>\n\n" + by_line()
        )
    except Exception as e:
        await send_me(
            f"⭐ <b>Stars AutoPay</b>\n\n❌ Ошибка:\n<code>{html(str(e)[:300])}</code>"
        )


async def _stars_timer_job(invoice_url: str, expected_value: int):
    await asyncio.sleep(STARS_TIMER_SEC)
    if state.stars_current_value == expected_value:
        await stars_pay_invoice(invoice_url)


def stars_restart_timer(invoice_url: str, value: int):
    if state.stars_timer_task and not state.stars_timer_task.done():
        state.stars_timer_task.cancel()
    state.stars_timer_task = asyncio.create_task(_stars_timer_job(invoice_url, value))


def stars_handle_message(message):
    if not state.stars_active:
        return
    text        = message.text or ""
    invoice_url = stars_extract_invoice_url(message)
    if invoice_url and invoice_url != state.stars_last_invoice:
        state.stars_last_invoice = invoice_url
    value = stars_extract_value(text)
    if value is not None and value != state.stars_current_value:
        state.stars_current_value = value
        if state.stars_last_invoice:
            stars_restart_timer(state.stars_last_invoice, value)


async def stars_load_last_message():
    from bot_client import client
    try:
        async for msg in client.iter_messages(STARS_CHAT_ID, from_user=STARS_BOT_ID, limit=1):
            stars_handle_message(msg)
    except Exception as e:
        print(f"[STARS] load: {e}")
