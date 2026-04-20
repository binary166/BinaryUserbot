"""
Новые команды Binary Userbot v1.5
"""
import os
import io
import datetime
import re
from urllib.parse import quote
import aiohttp
import yt_dlp
from collections import Counter
from telethon import events
from bot_client import client
import state
from config import LOADING
from premium_emoji import pe, by_line
from ai import or_request


async def _get(url, params=None, headers=None):
    try:
        h = {"User-Agent": "BinaryUserbot/1.5"}
        if headers:
            h.update(headers)
        async with aiohttp.ClientSession() as s:
            async with s.get(url, params=params, headers=h,
                             timeout=aiohttp.ClientTimeout(total=12)) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
    except Exception:
        pass
    return None



@client.on(events.NewMessage(pattern=r"^\.premium$", outgoing=True))
async def cmd_premium(event):
    state.premium_emoji_active = not getattr(state, "premium_emoji_active", True)
    cloak = pe("cloak"); star = pe("star_pe")
    if state.premium_emoji_active:
        status = f"<b>АКТИВИРОВАН</b> {star}"; hint = "Анимированные эмодзи включены."
    else:
        status = "<b>ВЫКЛЮЧЕН</b> ❌"; hint = "Используются обычные эмодзи."
    await event.edit(
        f"{cloak} <b>Премиум эмодзи: {status}</b>\n\n<blockquote>{hint}</blockquote>\n\n" + by_line(),
        parse_mode="html"
    )


@client.on(events.NewMessage(pattern=r"^\.afk(?:\s+(.+))?$", outgoing=True))
async def cmd_afk(event):
    reason = event.pattern_match.group(1)
    state.is_afk = not getattr(state, "is_afk", False)
    tracks = pe("tracks"); speak = pe("speak")
    if state.is_afk:
        state.afk_reason = reason or "Нет на месте"
        state.afk_time   = datetime.datetime.now()
        await event.edit(
            f"{tracks} <b>AFK активирован</b>\n\n"
            f"<blockquote>{speak} Причина: {state.afk_reason}\n"
            f"⏰ С: {state.afk_time.strftime('%H:%M  %d.%m.%Y')}</blockquote>\n\n"
            f"<i>Буду авто-отвечать на упоминания и в ЛС.</i>\n\n" + by_line(),
            parse_mode="html"
        )
    else:
        away_str = ""
        if hasattr(state, "afk_time") and state.afk_time:
            delta = datetime.datetime.now() - state.afk_time
            mins  = int(delta.total_seconds() // 60)
            away_str = f"\n<i>Отсутствовал: {mins} мин.</i>"
        await event.edit(f"{tracks} <b>Я снова в сети!</b>{away_str}\n\n" + by_line(), parse_mode="html")

@client.on(events.NewMessage(incoming=True))
async def afk_autoresponder(event):
    if not getattr(state, "is_afk", False): return
    if event.is_private or event.mentioned:
        reason = getattr(state, "afk_reason", "Нет на месте")
        tracks = pe("tracks"); speak = pe("speak")
        await event.reply(
            f"{tracks} <b>Сейчас недоступен</b>\n\n"
            f"<blockquote>{speak} Причина: {reason}</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )


@client.on(events.NewMessage(pattern=r"^\.wiki\s+(.+)$", outgoing=True))
async def cmd_wiki(event):
    query = event.pattern_match.group(1).strip()
    brain = pe("brain")
    await event.edit(LOADING, parse_mode="html")

    search_data = await _get(
        "https://ru.wikipedia.org/w/api.php",
        params={"action":"query","list":"search","srsearch":query,
                "format":"json","utf8":"1","srlimit":"3"}
    )
    page_title = None
    if search_data:
        results = search_data.get("query",{}).get("search",[])
        if results:
            page_title = results[0]["title"]

    if page_title:
        data = await _get(
            f"https://ru.wikipedia.org/api/rest_v1/page/summary/{quote(page_title, safe='')}"
        )
        if data and data.get("extract"):
            extract = data["extract"][:1200]
            url     = data.get("content_urls",{}).get("desktop",{}).get("page","")
            link    = f'\n🔗 <a href="{url}">Читать полностью</a>' if url else ""
            await event.edit(
                f"{brain} <b>Wikipedia: {page_title}</b>\n\n"
                f"<blockquote>{extract}</blockquote>{link}\n\n" + by_line(),
                parse_mode="html"
            )
            return

    try:
        ans = await or_request(
            "Ты энциклопедия. Дай краткую справку на русском языке, до 400 символов.",
            query, max_tokens=400
        )
        await event.edit(
            f"{brain} <b>{query}</b>\n\n<blockquote>{ans}</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
    except Exception:
        await event.edit(f"{brain} Ничего не найдено: <code>{query}</code>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.tz\s+(.+)$", outgoing=True))
async def cmd_tz(event):
    city = event.pattern_match.group(1).strip()
    bolt = pe("bolt")
    await event.edit(LOADING, parse_mode="html")
    geo = await _get("https://geocoding-api.open-meteo.com/v1/search",
                     params={"name": city, "count": "1", "language": "ru"})
    tz_name = city.replace(" ", "_"); city_name = city; country = ""
    if geo and geo.get("results"):
        loc = geo["results"][0]
        tz_name = loc.get("timezone", tz_name)
        city_name = loc.get("name", city); country = loc.get("country","")
    data = await _get(f"https://worldtimeapi.org/api/timezone/{tz_name}")
    if data and data.get("datetime"):
        dt_str = data["datetime"][:19].replace("T", " ")
        offset = data.get("utc_offset","?")
        label  = f"{city_name}, {country}" if country else city_name
        await event.edit(
            f"{bolt} <b>{label}</b>\n\n"
            f"<blockquote>🕐 {dt_str}\n📍 {tz_name}\n↔️ UTC{offset}</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
    else:
        await event.edit(
            f"{bolt} <b>Не найдено: {city}</b>\n\n"
            f"<blockquote>⚠️ Пример: <code>.tz Москва</code></blockquote>\n\n" + by_line(),
            parse_mode="html"
        )


@client.on(events.NewMessage(pattern=r"^\.ip\s+(.+)$", outgoing=True))
async def cmd_ip(event):
    ip = event.pattern_match.group(1).strip()
    pc = pe("pc"); eye = pe("eye")
    await event.edit(LOADING, parse_mode="html")
    data = await _get(f"http://ip-api.com/json/{ip}?lang=ru")
    if data and data.get("status") == "success":
        await event.edit(
            f"{pc} <b>IP: <code>{ip}</code></b>\n\n"
            f"<blockquote>"
            f"🌍 Страна: <b>{data.get('country','?')}</b>  [{data.get('countryCode','')}]\n"
            f"🏙 Регион: {data.get('regionName','?')}\n"
            f"🏘 Город: {data.get('city','?')}\n"
            f"📮 Индекс: {data.get('zip','?')}\n"
            f"📡 Провайдер: {data.get('isp','?')}\n"
            f"🏢 Организация: {data.get('org','?')}"
            f"</blockquote>\n\n"
            f"{eye} Координаты: <code>{data.get('lat')}, {data.get('lon')}</code>\n\n" + by_line(),
            parse_mode="html"
        )
    else:
        await event.edit(f"{pc} Не удалось получить данные: <code>{ip}</code>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.meme$", outgoing=True))
async def cmd_meme(event):
    alien = pe("alien")
    await event.edit(LOADING, parse_mode="html")
    data = await _get("https://meme-api.com/gimme/ru")
    if not data or not data.get("url"): data = await _get("https://meme-api.com/gimme")
    if data and data.get("url"):
        await client.send_file(
            event.chat_id, data["url"],
            caption=(f"{alien} <b>{data['title']}</b>\n\n<i>r/{data.get('subreddit','memes')} · ⬆️ {data.get('ups',0)}</i>\n\n" + by_line()),
            parse_mode="html"
        )
        await event.delete()
    else:
        await event.edit(f"{alien} Не удалось загрузить мем.\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.music\s+(.+)$", outgoing=True))
async def cmd_music(event):
    query = event.pattern_match.group(1)
    speak = pe("speak"); bolt = pe("bolt")
    await event.edit(LOADING, parse_mode="html")
    ydl_opts = {"format":"bestaudio/best","outtmpl":"/tmp/binary_music.%(ext)s","noplaylist":True,"quiet":True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=True)["entries"][0]
            title = info.get("title", query)
            dur = info.get("duration", 0); mins, secs = divmod(dur, 60)
            fname = ydl.prepare_filename(info)
        await client.send_file(
            event.chat_id, fname,
            caption=(f"{speak} <b>{title}</b>\n\n⏱ {mins}:{secs:02d}\n\n" + by_line()),
            parse_mode="html"
        )
        try: os.remove(fname)
        except OSError: pass
        await event.delete()
    except Exception as e:
        await event.edit(f"{speak} Ошибка: <code>{e}</code>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.lyr\s+(.+)$", outgoing=True))
async def cmd_lyr(event):
    song  = event.pattern_match.group(1).strip()
    speak = pe("speak")
    await event.edit(LOADING, parse_mode="html")

    lyrics = None

    if "/" in song:
        parts  = song.split("/", 1)
        artist = parts[0].strip(); title = parts[1].strip()
        data   = await _get(f"https://api.lyrics.ovh/v1/{quote(artist,safe='')}/{quote(title,safe='')}")
        if data and data.get("lyrics"):
            lyrics = data["lyrics"]

    if not lyrics:
        try:
            lyrics = await or_request(
                "Ты музыкальная энциклопедия. Пользователь ищет текст песни. "
                "Если знаешь точный текст — дай первый куплет и припев (до 600 символов). "
                "Если не знаешь точно — дай описание трека: исполнитель, альбом, год, стиль музыки, тематика текстов. "
                "Отвечай на русском языке.",
                f"Трек: {song}",
                max_tokens=500
            )
        except Exception:
            lyrics = None

    if lyrics:
        short = lyrics[:2000]
        await event.edit(
            f"{speak} <b>{song}</b>\n\n"
            f"<blockquote>{short}{'...' if len(lyrics) > 2000 else ''}</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
    else:
        await event.edit(
            f"{speak} Не найдено: <b>{song}</b>\n\n"
            f"<blockquote>💡 Формат: <code>.lyr Исполнитель / Название</code></blockquote>\n\n" + by_line(),
            parse_mode="html"
        )


@client.on(events.NewMessage(pattern=r"^\.chat$", outgoing=True))
async def cmd_chat(event):
    users_pe = pe("users"); brain = pe("brain")
    await event.edit(LOADING, parse_mode="html")
    cnt = Counter(); users = Counter()
    async for msg in client.iter_messages(event.chat_id, limit=3000):
        if msg.text:
            for word in msg.text.lower().split():
                if len(word) > 3: cnt[word] += 1
        if msg.sender_id: users[msg.sender_id] += 1
    top_words = "\n".join(f"  <b>{i+1}.</b> {w}  —  {c} раз" for i,(w,c) in enumerate(cnt.most_common(5))) or "  <i>нет данных</i>"
    top_users = "\n".join(f"  <b>{i+1}.</b> <code>{u}</code>  —  {c} сообщ." for i,(u,c) in enumerate(users.most_common(5))) or "  <i>нет данных</i>"
    await event.edit(
        f"{users_pe} <b>Статистика чата</b>\n\n"
        f"{brain} <b>Топ слов:</b>\n<blockquote>{top_words}</blockquote>\n\n"
        f"👥 <b>Топ участников:</b>\n<blockquote>{top_users}</blockquote>\n\n" + by_line(),
        parse_mode="html"
    )


@client.on(events.NewMessage(pattern=r"^\.history\s+(\d+)$", outgoing=True))
async def cmd_history(event):
    count = int(event.pattern_match.group(1)); eye = pe("eye")
    if not event.is_reply:
        return await event.edit(f"{eye} Ответь на чьё-то сообщение!", parse_mode="html")
    await event.edit(LOADING, parse_mode="html")
    reply = await event.get_reply_message(); msgs = []
    async for m in client.iter_messages(event.chat_id, from_user=reply.sender_id, limit=count):
        if m.text: msgs.append(f"• {m.text[:120]}")
    if not msgs:
        return await event.edit(f"{eye} Сообщений не найдено.\n\n" + by_line(), parse_mode="html")
    await event.edit(
        f"{eye} <b>История</b>  ({len(msgs)} сообщ.)\n\n<blockquote>{'|'.join(msgs).replace('|',chr(10))}</blockquote>\n\n" + by_line(),
        parse_mode="html"
    )


@client.on(events.NewMessage(pattern=r"^\.гороскоп\s+(.+)$", outgoing=True))
async def cmd_horo(event):
    sign  = event.pattern_match.group(1).strip()
    star  = pe("star_pe"); love = pe("love")
    await event.edit(LOADING, parse_mode="html")
    try:
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        text  = await or_request(
            "Ты астролог. Напиши короткий, интересный и личный гороскоп на сегодня. "
            "3-4 предложения. Добавь тематическое эмодзи в начало. На русском языке.",
            f"Знак зодиака: {sign}. Дата: {today}", max_tokens=300
        )
        await event.edit(
            f"{star} <b>Гороскоп — {sign.capitalize()}</b>\n<i>{today}</i>\n\n"
            f"<blockquote>{text}</blockquote>\n\n{love} Удачного дня!\n\n" + by_line(),
            parse_mode="html"
        )
    except Exception as e:
        await event.edit(f"❌ <code>{e}</code>", parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.movie\s+(.+)$", outgoing=True))
async def cmd_movie(event):
    title = event.pattern_match.group(1).strip()
    cloak = pe("cloak"); eye = pe("eye")
    await event.edit(LOADING, parse_mode="html")

    async def try_omdb(t):
        return await _get("https://www.omdbapi.com/",
                          params={"t": t, "apikey": "trilogy", "plot": "short", "r": "json"})

    data = await try_omdb(title)

    if not data or data.get("Response") != "True":
        try:
            en_title = await or_request(
                "Translate this movie/series title to English. Return ONLY the English title.",
                title, max_tokens=60
            )
            en_title = en_title.strip().strip('"\'')
            data = await try_omdb(en_title)
        except Exception:
            pass

    if data and data.get("Response") == "True":
        await event.edit(
            f"{cloak} <b>{data.get('Title', title)}</b>  ({data.get('Year','?')})\n\n"
            f"<blockquote>"
            f"⭐ IMDb: {data.get('imdbRating','?')}/10\n"
            f"🎬 Жанр: {data.get('Genre','?')}\n"
            f"🎥 Режиссёр: {data.get('Director','?')}\n"
            f"👥 Актёры: {data.get('Actors','?')[:100]}\n"
            f"📝 {data.get('Plot','?')[:300]}"
            f"</blockquote>\n\n"
            f"{eye} <i>Источник: IMDb</i>\n\n" + by_line(),
            parse_mode="html"
        )
        return

    try:
        text = await or_request(
            "Ты кинокритик. Расскажи о фильме/сериале: год, жанр, краткое описание, рейтинг. На русском.",
            f"Фильм/сериал: {title}", max_tokens=400
        )
        await event.edit(
            f"{cloak} <b>{title}</b>\n\n<blockquote>{text}</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
    except Exception:
        await event.edit(
            f"{cloak} <b>Фильм: {title}</b>\n\n<blockquote>❌ Не найдено.</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )


# ─── STEAM ────────────────────────────────────────────────────────────────────

@client.on(events.NewMessage(pattern=r"^\.steam\s+(.+)$", outgoing=True))
async def cmd_steam(event):
    game  = event.pattern_match.group(1)
    pc    = pe("pc"); money = pe("money")
    await event.edit(LOADING, parse_mode="html")
    search = await _get("https://store.steampowered.com/api/storesearch/",
                        params={"term": game, "cc": "ru", "l": "russian"})
    if search and search.get("items"):
        item   = search["items"][0]; app_id = item.get("id"); name = item.get("name", game)
        details = await _get("https://store.steampowered.com/api/appdetails",
                             params={"appids": app_id, "cc": "ru", "l": "russian"})
        if details and details.get(str(app_id),{}).get("success"):
            d     = details[str(app_id)]["data"]
            price = d.get("price_overview",{}).get("final_formatted","Бесплатно")
            genres= ", ".join(g["description"] for g in d.get("genres",[])[:3]) or "—"
            short = d.get("short_description","—")[:200]
            await event.edit(
                f"{pc} <b>{name}</b>\n\n"
                f"<blockquote>{money} Цена: {price}\n🎮 Жанры: {genres}\n📝 {short}\n🆔 AppID: {app_id}</blockquote>\n\n" + by_line(),
                parse_mode="html"
            )
            return
    await event.edit(f"{pc} <b>Steam: {game}</b>\n\n<blockquote>❌ Не найдено.</blockquote>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.metadata\s+(.+)$", outgoing=True))
async def cmd_meta(event):
    url = event.pattern_match.group(1).strip()
    pc  = pe("pc"); eye = pe("eye")
    await event.edit(LOADING, parse_mode="html")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10),
                                   allow_redirects=True, headers={"User-Agent":"Mozilla/5.0"}) as resp:
                ct=resp.headers.get("Content-Type","?"); server=resp.headers.get("Server","—")
                powered=resp.headers.get("X-Powered-By","—"); status=resp.status; final_url=str(resp.url)
        await event.edit(
            f"{pc} <b>Метаданные</b>\n\n"
            f"<blockquote>🔗 URL: <code>{final_url[:80]}</code>\n📊 Статус: {status}\n📄 Тип: {ct.split(';')[0]}\n🖥 Сервер: {server}\n⚙️ Движок: {powered}</blockquote>\n\n"
            f"{eye} <i>HTTP-заголовки</i>\n\n" + by_line(),
            parse_mode="html"
        )
    except Exception as e:
        await event.edit(f"{pc} Ошибка: <code>{e}</code>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.whois\s+(.+)$", outgoing=True))
async def cmd_whois(event):
    domain = event.pattern_match.group(1).strip().lstrip("https://").lstrip("http://").split("/")[0]
    eye = pe("eye")
    await event.edit(LOADING, parse_mode="html")
    rdap = await _get(f"https://rdap.org/domain/{domain}")
    if rdap:
        events_list = {e["eventAction"]: e["eventDate"][:10] for e in rdap.get("events",[]) if "eventDate" in e}
        reg_info = next((e for e in rdap.get("entities",[]) if "registrar" in e.get("roles",[])), None)
        registrar = "—"
        if reg_info:
            try: registrar = reg_info.get("vcardArray",[[]])[1][1][3]
            except (IndexError, TypeError): pass
        ns_list = rdap.get("nameservers",[])
        ns = ", ".join(n.get("ldhName","") for n in ns_list[:3]) if ns_list else "—"
        await event.edit(
            f"{eye} <b>Whois: {domain}</b>\n\n"
            f"<blockquote>📋 Регистратор: {registrar}\n📅 Создан: {events_list.get('registration','—')}\n⏳ Истекает: {events_list.get('expiration','—')}\n🖥 NS: {ns}</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
    else:
        await event.edit(f"{eye} <b>Whois: {domain}</b>\n\n<blockquote>⚠️ Данные не найдены.</blockquote>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.dict\s+(.+)$", outgoing=True))
async def cmd_dict(event):
    word  = event.pattern_match.group(1).strip()
    brain = pe("brain")
    await event.edit(LOADING, parse_mode="html")

    is_english = bool(re.match(r'^[a-zA-Z\s\-]+$', word))

    if is_english:
        data = await _get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word, safe='')}")
        if data and isinstance(data, list) and not data[0].get("title"):
            entry = data[0]; meanings = entry.get("meanings", []); lines = []
            for m in meanings[:3]:
                pos = m.get("partOfSpeech",""); defs = m.get("definitions",[])
                if defs:
                    lines.append(f"<b>{pos}:</b> {defs[0].get('definition','')}")
                    if defs[0].get("example"): lines.append(f"<i>✏️ {defs[0]['example']}</i>")
            synonyms = []
            for m in meanings[:2]: synonyms += m.get("synonyms",[])[:3]
            syn_line = "  ".join(f"<code>{s}</code>" for s in synonyms[:5])
            text_block = "\n".join(lines) if lines else None
            if text_block:
                try:
                    ru_def = await or_request(
                        "Переведи словарное определение на русский язык. Сохрани HTML-теги <b> и <i>. Только перевод.",
                        text_block, max_tokens=400
                    )
                except Exception:
                    ru_def = text_block
                await event.edit(
                    f"{brain} <b>📖 {word}</b>\n\n<blockquote>{ru_def}</blockquote>\n"
                    + (f"\n🔀 Синонимы: {syn_line}\n" if syn_line else "")
                    + "\n" + by_line(),
                    parse_mode="html"
                )
                return

    try:
        result = await or_request(
            "Ты толковый словарь. Дай чёткое краткое определение слова на русском языке. "
            "Формат: (часть речи) значение. Пример использования. "
            "Если слово английское — переведи и объясни на русском.",
            f"Слово: {word}", max_tokens=400
        )
        await event.edit(
            f"{brain} <b>📖 {word}</b>\n\n<blockquote>{result}</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
    except Exception as e:
        await event.edit(f"{brain} <b>{word}</b>\n\n<blockquote>❌ Ошибка: {e}</blockquote>\n\n" + by_line(), parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.md$", outgoing=True))
async def cmd_md(event):
    brain = pe("brain"); cloak = pe("cloak"); bolt = pe("bolt")

    if not event.is_reply:
        await event.edit(
            f"{brain} <b>.md — Загрузка модуля</b>\n\n"
            f"<blockquote>"
            f"Ответь на сообщение с прикреплённым <code>.py</code> файлом.\n\n"
            f"Формат модуля:\n"
            f"<code># MODULE_NAME = \"Название\"\n"
            f"# MODULE_CMD  = \".mycommand\"\n"
            f"# MODULE_DESC = \"Описание\"</code>"
            f"</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
        return

    reply = await event.get_reply_message()
    if not reply or not reply.document:
        await event.edit("❌ В сообщении нет файла.", parse_mode="html"); return

    doc = reply.document; fname = ""
    for attr in doc.attributes:
        if hasattr(attr, "file_name"): fname = attr.file_name; break

    if not fname.endswith(".py"):
        await event.edit(f"❌ Файл должен быть <code>.py</code>. Получено: <code>{fname}</code>", parse_mode="html"); return

    await event.edit(f"{bolt} <i>Загружаю <code>{fname}</code>...</i>", parse_mode="html")

    try:
        file_bytes = await client.download_media(reply.document, bytes)
    except Exception as e:
        await event.edit(f"❌ Ошибка скачивания: <code>{e}</code>", parse_mode="html"); return

    try:
        from module_loader import install_module
        meta = install_module(fname, file_bytes)
    except Exception as e:
        await event.edit(f"❌ Ошибка загрузки модуля:\n<code>{e}</code>", parse_mode="html"); return

    await event.edit(
        f"{cloak} <b>Модуль загружен!</b>\n\n"
        f"<blockquote>"
        f"📦 Файл: <code>{fname}</code>\n"
        f"🔖 Название: <b>{meta['name']}</b>\n"
        f"⌨️ Команда: <code>{meta['cmd']}</code>\n"
        f"📝 Описание: {meta['desc']}"
        f"</blockquote>\n\n"
        f"{bolt} Команда <code>{meta['cmd']}</code> активна!\n\n" + by_line(),
        parse_mode="html"
    )
