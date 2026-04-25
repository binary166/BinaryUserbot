from datetime import datetime, timezone, timedelta
from utils import html
from premium_emoji import by_line
from ai import or_request
from config import NEWS_CHANNEL


async def get_last_news() -> str:
    from bot_client import client

    cutoff     = datetime.now(timezone.utc) - timedelta(hours=24)
    news_items = []
    try:
        async for msg in client.iter_messages(NEWS_CHANNEL, limit=80):
            if msg.date < cutoff:
                break
            if msg.text and len(msg.text.strip()) > 30:
                news_items.append(msg.text[:400].strip())
    except Exception as e:
        return f"❌ <b>Ошибка получения новостей:</b>\n<code>{html(str(e))}</code>"

    if not news_items:
        return "📰 <b>За последние 24 часа новостей не найдено.</b>"

    news_items.reverse()
    combined = "\n\n---\n\n".join(news_items[:20])

    try:
        summary = await or_request(
            "Ты редактор новостного Telegram-канала. Создай стильный дайджест.\n"
            'Формат КАЖДОГО пункта (строго одна строка):\n'
            '<tg-emoji emoji-id="5257965174979042426">📝</tg-emoji> Заголовок — краткое описание 1-2 предложения.\n'
            "Выдели 5-7 событий. Начни с самого горячего. "
            "Пиши живо, без канцелярита. На русском. HTML bold/italic разрешён.",
            f"Посты за 24 часа:\n\n{combined[:3000]}",
            max_tokens=700
        )
    except Exception as e:
        return f"❌ <b>Ошибка AI:</b> <code>{html(str(e)[:200])}</code>"

    now_str = datetime.now().strftime("%d.%m.%Y  %H:%M")
    clock   = '<tg-emoji emoji-id="5199457120428249992">🕘</tg-emoji>'
    src     = '<tg-emoji emoji-id="5429571366384842791">🔎</tg-emoji>'
    return (
        '<blockquote><tg-emoji emoji-id="5258328383183396223">📖</tg-emoji>  ДАЙДЖЕСТ НОВОСТЕЙ</blockquote>\n\n'
        + summary +
        f'\n\n{src} Источник: @binary_news\n'
        f'{clock} {now_str}\n'
        + by_line()
    )
