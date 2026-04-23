import os
import io
import shutil
import asyncio
import tempfile
import datetime
import re
from urllib.parse import quote
import aiohttp
import yt_dlp
from collections import Counter
from telethon import events
from telethon.tl.types import DocumentAttributeAudio
from bot_client import client
import state
from config import LOADING, FUNSTAT_TOKEN
from premium_emoji import pe, by_line
from ai import or_request
from utils import html


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
    await event.edit(LOADING, parse_mode="html")

    tmp_dir = tempfile.mkdtemp()
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio[ext=opus]/bestaudio/best",
        "outtmpl": os.path.join(tmp_dir, "audio.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    if shutil.which("ffmpeg"):
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

    try:
        loop = asyncio.get_event_loop()

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=True)
                entry = info["entries"][0]
                fname = ydl.prepare_filename(entry)
                if not os.path.exists(fname):
                    base = fname.rsplit(".", 1)[0]
                    for ext in ("mp3", "m4a", "opus", "webm", "ogg", "wav", "aac"):
                        c = f"{base}.{ext}"
                        if os.path.exists(c):
                            fname = c
                            break
                    else:
                        files = os.listdir(tmp_dir)
                        if files:
                            fname = os.path.join(tmp_dir, files[0])
                return entry, fname

        entry, fname = await loop.run_in_executor(None, _download)
        title = entry.get("title", query)
        artist = entry.get("uploader") or entry.get("channel") or entry.get("artist") or "Unknown"
        duration = int(entry.get("duration", 0))
        thumb_url = entry.get("thumbnail")

        thumb_bytes = None
        if thumb_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(thumb_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            thumb_bytes = await resp.read()
            except Exception:
                pass

        music_emoji = '<tg-emoji emoji-id="5346296430166293639">🎵</tg-emoji>'
        by_emoji = '<tg-emoji emoji-id="5420547137584776434">⭐</tg-emoji>'
        caption = (
            f'{music_emoji} <b>{html(artist)}</b> — <b>{html(title)}</b>\n\n'
            f'{by_emoji} <i>by B1nnary</i>  '
            f'<b><a href="https://github.com/binary166/BinaryUserbot">GitHub</a></b>'
        )

        await client.send_file(
            event.chat_id,
            fname,
            attributes=[DocumentAttributeAudio(
                duration=duration,
                title=title,
                performer=artist,
            )],
            thumb=thumb_bytes,
            caption=caption,
            parse_mode="html",
        )
        await event.delete()

    except Exception as e:
        music_emoji = '<tg-emoji emoji-id="5346296430166293639">🎵</tg-emoji>'
        by_emoji = '<tg-emoji emoji-id="5420547137584776434">⭐</tg-emoji>'
        await event.edit(
            f"{music_emoji} Ошибка: <code>{html(str(e)[:200])}</code>\n\n"
            f"{by_emoji} <i>by B1nnary</i>  "
            f'<b><a href="https://github.com/binary166/BinaryUserbot">GitHub</a></b>',
            parse_mode="html"
        )
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass


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


STOP_WORDS = {
    "что", "как", "это", "или", "так", "для", "тоже", "меня", "тебе", "тебя",
    "чтобы", "если", "когда", "есть", "была", "были", "было", "один", "будет",
    "только", "себя", "свой", "свою", "также", "всех", "еще", "ещё", "вот",
    "даже", "этот", "этим", "этого", "него", "нее", "нею", "ими", "его", "её",
    "where", "what", "with", "that", "this", "from", "have", "they", "their",
    "would", "there", "https", "http",
}


@client.on(events.NewMessage(pattern=r"^\.chat$", outgoing=True))
async def cmd_chat(event):
    users_pe = pe("users"); brain = pe("brain"); bolt = pe("bolt")
    import time as _time
    t0 = _time.perf_counter()
    await event.edit(LOADING, parse_mode="html")

    import re as _re
    word_re = _re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9]{4,20}")

    cnt = Counter()
    users = Counter()
    total = 0
    media = 0

    batch_size = 200
    async for msg in client.iter_messages(event.chat_id, limit=3000):
        total += 1
        if msg.sender_id:
            users[msg.sender_id] += 1
        if msg.media:
            media += 1
        t = msg.raw_text
        if t:
            for w in word_re.findall(t.lower()):
                if w not in STOP_WORDS:
                    cnt[w] += 1

    top_user_ids = [uid for uid, _ in users.most_common(5)]
    name_map = {}
    if top_user_ids:
        results = await asyncio.gather(
            *[client.get_entity(uid) for uid in top_user_ids],
            return_exceptions=True
        )
        for uid, ent in zip(top_user_ids, results):
            if isinstance(ent, Exception):
                name_map[uid] = f"ID:{uid}"
                continue
            fn = getattr(ent, "first_name", "") or ""
            ln = getattr(ent, "last_name", "") or ""
            un = getattr(ent, "username", None)
            name = (fn + " " + ln).strip() or (getattr(ent, "title", None) or "")
            if un:
                name_map[uid] = f'<a href="https://t.me/{un}">{html(name or un)}</a>'
            else:
                name_map[uid] = html(name or f"ID:{uid}")

    top_words = "\n".join(
        f"  <b>{i+1}.</b> <code>{html(w)}</code>  —  {c}"
        for i, (w, c) in enumerate(cnt.most_common(8))
    ) or "  <i>нет данных</i>"

    top_users = "\n".join(
        f"  <b>{i+1}.</b> {name_map.get(uid, f'ID:{uid}')}  —  {c}"
        for i, (uid, c) in enumerate(users.most_common(5))
    ) or "  <i>нет данных</i>"

    elapsed = (_time.perf_counter() - t0) * 1000

    await event.edit(
        f"{users_pe} <b>Статистика чата</b>\n"
        f"<i>Проанализировано: {total} сообщ. за {elapsed:.0f} мс · медиа: {media}</i>\n\n"
        f"{brain} <b>Топ слов:</b>\n<blockquote>{top_words}</blockquote>\n\n"
        f"{bolt} <b>Топ участников:</b>\n<blockquote>{top_users}</blockquote>\n\n" + by_line(),
        parse_mode="html", link_preview=False
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


def _extract_domain(raw: str) -> str:
    from urllib.parse import urlparse
    s = raw.strip().strip("<>\"' ")
    if "://" not in s:
        s = "http://" + s
    host = urlparse(s).hostname or ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net", "ac", "gov", "edu") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


@client.on(events.NewMessage(pattern=r"^\.whois\s+([\s\S]+)$", outgoing=True))
async def cmd_whois(event):
    raw = event.pattern_match.group(1)
    domain = _extract_domain(raw)
    eye = pe("eye")
    if not domain:
        await event.edit(f"{eye} Не удалось распознать домен.", parse_mode="html")
        return
    await event.edit(LOADING, parse_mode="html")
    rdap = await _get(f"https://rdap.org/domain/{domain}")
    if not rdap:
        parts = domain.split(".")
        if len(parts) > 2:
            rdap = await _get(f"https://rdap.org/domain/{'.'.join(parts[-2:])}")
    if rdap:
        events_list = {e["eventAction"]: e["eventDate"][:10] for e in rdap.get("events", []) if "eventDate" in e}
        reg_info = next((e for e in rdap.get("entities", []) if "registrar" in e.get("roles", [])), None)
        registrar = "—"
        if reg_info:
            try:
                registrar = reg_info.get("vcardArray", [[]])[1][1][3]
            except (IndexError, TypeError):
                pass
        ns_list = rdap.get("nameservers", [])
        ns = ", ".join(n.get("ldhName", "") for n in ns_list[:3]) if ns_list else "—"
        status = ", ".join(rdap.get("status", [])[:3]) or "—"
        await event.edit(
            f"{eye} <b>Whois: {html(domain)}</b>\n\n"
            f"<blockquote>"
            f"📋 Регистратор: {html(registrar)}\n"
            f"📅 Создан: {events_list.get('registration', '—')}\n"
            f"🔄 Обновлён: {events_list.get('last changed', '—')}\n"
            f"⏳ Истекает: {events_list.get('expiration', '—')}\n"
            f"🏷 Статус: {html(status)}\n"
            f"🖥 NS: {html(ns)}"
            f"</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )
    else:
        await event.edit(
            f"{eye} <b>Whois: {html(domain)}</b>\n\n"
            f"<blockquote>⚠️ Данные не найдены.</blockquote>\n\n" + by_line(),
            parse_mode="html"
        )


@client.on(events.NewMessage(pattern=r"^\.server$", outgoing=True))
async def cmd_server(event):
    pc = pe("pc"); bolt = pe("bolt"); gear = pe("gear")
    await event.edit(LOADING, parse_mode="html")

    try:
        import psutil
    except ImportError:
        await event.edit(
            f"{pc} Модуль <code>psutil</code> не установлен.\n"
            f"Установи: <code>pip install psutil</code>",
            parse_mode="html"
        )
        return

    import platform as _plat
    import socket as _sock
    import time as _time

    cpu = psutil.cpu_percent(interval=0.5)
    cpu_count = psutil.cpu_count(logical=True)
    try:
        freq = psutil.cpu_freq()
        freq_str = f"{freq.current:.0f} МГц" if freq else "—"
    except Exception:
        freq_str = "—"
    try:
        la1, la5, la15 = psutil.getloadavg()
        load_str = f"{la1:.2f} / {la5:.2f} / {la15:.2f}"
    except (AttributeError, OSError):
        load_str = "—"

    mem = psutil.virtual_memory()
    mem_used_gb = mem.used / 1024 ** 3
    mem_total_gb = mem.total / 1024 ** 3

    disk = psutil.disk_usage("/")
    disk_used_gb = disk.used / 1024 ** 3
    disk_total_gb = disk.total / 1024 ** 3

    net = psutil.net_io_counters()
    sent_gb = net.bytes_sent / 1024 ** 3
    recv_gb = net.bytes_recv / 1024 ** 3

    up_sec = _time.time() - psutil.boot_time()
    days = int(up_sec // 86400)
    hours = int((up_sec % 86400) // 3600)
    mins = int((up_sec % 3600) // 60)
    uptime = f"{days}д {hours}ч {mins}м" if days else f"{hours}ч {mins}м"

    host = _sock.gethostname()
    plat = f"{_plat.system()} {_plat.release()}"
    arch = _plat.machine()
    pyv = _plat.python_version()

    ping_tg = "—"
    ping_google = "—"
    async def _ping(url):
        t0 = _time.perf_counter()
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, timeout=aiohttp.ClientTimeout(total=5)) as r:
                    await r.read()
                    if r.status < 500:
                        return f"{(_time.perf_counter() - t0) * 1000:.0f} мс"
        except Exception:
            pass
        return "—"

    ping_tg, ping_google = await asyncio.gather(
        _ping("https://api.telegram.org"),
        _ping("https://www.google.com/generate_204"),
    )

    def bar(pct: float, width: int = 12) -> str:
        filled = int(round(pct / 100 * width))
        return "▓" * filled + "░" * (width - filled)

    text = (
        f"{pc} <b>Сервер · мониторинг</b>\n\n"
        f"{bolt} <b>CPU</b>\n"
        f"<blockquote>"
        f"⚙️ {cpu:.1f}%  <code>{bar(cpu)}</code>\n"
        f"🧩 Ядер: {cpu_count}  ·  {freq_str}\n"
        f"📊 LA: {load_str}"
        f"</blockquote>\n"
        f"{gear} <b>Память</b>\n"
        f"<blockquote>"
        f"💾 RAM: {mem_used_gb:.2f} / {mem_total_gb:.2f} ГБ  ({mem.percent:.0f}%)\n"
        f"<code>{bar(mem.percent)}</code>\n"
        f"💿 Диск: {disk_used_gb:.1f} / {disk_total_gb:.1f} ГБ  ({disk.percent:.0f}%)\n"
        f"<code>{bar(disk.percent)}</code>"
        f"</blockquote>\n"
        f"🌐 <b>Сеть</b>\n"
        f"<blockquote>"
        f"⬆️ Отправлено: {sent_gb:.2f} ГБ\n"
        f"⬇️ Получено: {recv_gb:.2f} ГБ\n"
        f"🛰 Ping Telegram: <code>{ping_tg}</code>\n"
        f"🛰 Ping Google: <code>{ping_google}</code>"
        f"</blockquote>\n"
        f"🖥 <b>Система</b>\n"
        f"<blockquote>"
        f"🏷 Host: <code>{html(host)}</code>\n"
        f"🐧 OS: <code>{html(plat)}</code>  ({arch})\n"
        f"🐍 Python: <code>{pyv}</code>\n"
        f"⏱ Uptime: <code>{uptime}</code>"
        f"</blockquote>\n\n"
        + by_line()
    )
    await event.edit(text, parse_mode="html")


@client.on(events.NewMessage(pattern=r"^\.tonnel\s+([\s\S]+)$", outgoing=True))
async def cmd_tonnel(event):
    pc = pe("pc"); eye = pe("eye"); lock = pe("lock")
    raw = event.pattern_match.group(1).strip().strip("<>\"' ")
    url = raw if "://" in raw else "http://" + raw

    await event.edit(LOADING, parse_mode="html")

    import time as _time
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if not parsed.hostname:
        await event.edit(f"{pc} Некорректная ссылка.", parse_mode="html")
        return

    headers_req = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
    }

    t0 = _time.perf_counter()
    status = "—"; server = "—"; ctype = "—"; final_url = url; body_size = 0
    title = "—"; desc_meta = "—"; preview = ""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                url, headers=headers_req, allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=15), ssl=False,
            ) as r:
                status = r.status
                server = r.headers.get("Server", "—")
                ctype  = r.headers.get("Content-Type", "—").split(";")[0].strip()
                final_url = str(r.url)
                body = await r.content.read(200 * 1024)
                body_size = int(r.headers.get("Content-Length", len(body)))
                if ctype.startswith("text") or "html" in ctype or "json" in ctype:
                    try:
                        txt = body.decode("utf-8", errors="replace")
                    except Exception:
                        txt = ""
                    import re as _re
                    def _clean_str(x: str, lim: int) -> str:
                        x = ''.join(ch for ch in x if ch == ' ' or ord(ch) >= 0x20)
                        return x.strip()[:lim]
                    m = _re.search(r"<title[^>]*>(.*?)</title>", txt, _re.IGNORECASE | _re.DOTALL)
                    if m:
                        title = _clean_str(m.group(1), 120)
                    m = _re.search(
                        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                        txt, _re.IGNORECASE
                    )
                    if m:
                        desc_meta = _clean_str(m.group(1), 200)
                    clean = _re.sub(r"<script[\s\S]*?</script>", " ", txt, flags=_re.IGNORECASE)
                    clean = _re.sub(r"<style[\s\S]*?</style>", " ", clean, flags=_re.IGNORECASE)
                    clean = _re.sub(r"<[^>]+>", " ", clean)
                    clean = _re.sub(r"\s+", " ", clean)
                    preview = _clean_str(clean, 350)
    except Exception as e:
        await event.edit(
            f"{pc} <b>Tonnel</b>\n\n"
            f"<blockquote>❌ Ошибка: <code>{html(str(e)[:200])}</code></blockquote>\n\n"
            + by_line(),
            parse_mode="html"
        )
        return
    elapsed = (_time.perf_counter() - t0) * 1000

    shot = None
    shot_ext = "jpg"
    try:
        shot_url = f"https://image.thum.io/get/width/1280/{url}"
        async with aiohttp.ClientSession() as s:
            async with s.get(
                shot_url, headers=headers_req,
                timeout=aiohttp.ClientTimeout(total=25),
            ) as r:
                if r.status == 200:
                    data = await r.read()
                    if len(data) > 5000:
                        if data[:8] == b"\x89PNG\r\n\x1a\n":
                            shot = data; shot_ext = "png"
                        elif data[:3] == b"\xff\xd8\xff":
                            shot = data; shot_ext = "jpg"
                        elif data[:6] in (b"GIF87a", b"GIF89a"):
                            shot = data; shot_ext = "gif"
                        elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                            shot = data; shot_ext = "webp"
    except Exception:
        pass

    size_str = f"{body_size / 1024:.1f} КБ" if body_size < 1024 * 1024 else f"{body_size / 1024 / 1024:.2f} МБ"

    from urllib.parse import quote as _q
    url_clean = final_url if "://" in final_url else "http://" + final_url
    jina_url    = f"https://r.jina.ai/{url_clean}"
    archive_url = f"https://web.archive.org/web/{url_clean}"
    archive_save = f"https://web.archive.org/save/{url_clean}"
    cf_cache    = f"https://cachedview.nl/"
    ggl_trans   = f"https://translate.google.com/translate?sl=auto&tl=en&u={_q(url_clean, safe='')}"

    safe_links = (
        f"🕸 <a href=\"{html(jina_url)}\">Jina Reader</a>  —  читать через их IP\n"
        f"🏛 <a href=\"{html(archive_url)}\">Web Archive</a>  —  архивный снимок\n"
        f"💾 <a href=\"{html(archive_save)}\">Сохранить в архив</a>\n"
        f"🌍 <a href=\"{html(ggl_trans)}\">Google Translate прокси</a>"
    )

    head = (
        f"{lock} <b>Безопасный тоннель</b>\n"
        f"{eye} <b>{html(title)}</b>\n\n"
        f"🔗 <code>{html(final_url[:180])}</code>\n"
        f"📊 <b>{status}</b>  ·  ⏱ {elapsed:.0f} мс  ·  📦 {size_str}\n"
        f"📄 <code>{html(ctype)}</code>  ·  🖥 <code>{html(server)}</code>\n"
        f"🌐 <code>{html(parsed.hostname)}</code>\n\n"
        f"<b>Открыть безопасно:</b>\n{safe_links}\n\n"
    )

    extra = ""
    if desc_meta != "—":
        extra += f"📝 <i>{html(desc_meta)}</i>\n\n"
    if preview:
        extra += f"<blockquote expandable>{html(preview)}</blockquote>\n\n"

    short_caption = head + by_line()
    full_text = head + extra + by_line()

    try:
        await event.delete()
    except Exception:
        pass

    sent_ok = False
    sent_as_photo = False
    if shot:
        try:
            buf = io.BytesIO(shot); buf.name = f"preview.{shot_ext}"
            await client.send_file(
                event.chat_id, buf, caption=short_caption,
                parse_mode="html", force_document=False,
            )
            sent_ok = True
            sent_as_photo = True
        except Exception as e:
            print(f"[tonnel send_file] {e}")

    def _strip_tg_emoji(t: str) -> str:
        import re as __re
        return __re.sub(r'<tg-emoji[^>]*>([^<]*)</tg-emoji>', r'\1', t)

    def _strip_html(t: str) -> str:
        import re as __re
        t = __re.sub(r'<[^>]+>', '', t)
        t = t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return t

    def _sanitize(t: str) -> str:
        return ''.join(c for c in t if c == '\n' or c == '\t' or ord(c) >= 0x20)

    if not sent_ok:
        attempts = [
            (full_text[:4000], "html"),
            (_sanitize(full_text)[:4000], "html"),
            (_strip_tg_emoji(_sanitize(full_text))[:4000], "html"),
            (_strip_html(_sanitize(full_text))[:4000], None),
            (f"Tonnel\n\nURL: {final_url[:200]}\nСтатус: {status}\nТип: {ctype}", None),
        ]
        for body, pm in attempts:
            try:
                await client.send_message(
                    event.chat_id, body,
                    parse_mode=pm, link_preview=False,
                )
                sent_ok = True
                break
            except Exception as e:
                print(f"[tonnel send attempt] pm={pm} err={e}")
                continue

    if sent_as_photo and extra:
        try:
            extra_text = extra + by_line()
            if len(extra_text) > 4000:
                extra_text = extra_text[:3950] + "...\n\n" + by_line()
            await client.send_message(
                event.chat_id, extra_text,
                parse_mode="html", link_preview=False,
            )
        except Exception as e:
            print(f"[tonnel send extra] {e}")


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


@client.on(events.NewMessage(pattern=r"^\.telelog(?:\s+(.+))?$", outgoing=True))
async def cmd_telelog(event):
    pc = pe("pc"); eye = pe("eye")
    arg = (event.pattern_match.group(1) or "").strip()

    if not arg:
        reply = await event.get_reply_message()
        if reply and reply.sender_id:
            arg = str(reply.sender_id)
        else:
            await event.edit(
                f"❗ Укажи юзернейм: <code>.telelog @username</code>\n"
                f"или ответом на сообщение.", parse_mode="html"
            )
            return

    user_arg = arg.lstrip("@").strip()
    await event.edit(LOADING, parse_mode="html")

    try:
        from funstat_api import AsyncFunstatClient
    except ImportError:
        await event.edit(
            f"❌ Модуль <code>funstat_api</code> не установлен.\n"
            f"Установи: <code>pip install funstat-api</code>",
            parse_mode="html"
        )
        return

    try:
        async with AsyncFunstatClient(FUNSTAT_TOKEN) as fs:
            resolved = await fs.resolve_username(user_arg)
            user_info = None
            if resolved and resolved.data:
                user_info = resolved.data[0]

            result = await fs.get_chats(user_arg)
    except Exception as e:
        await event.edit(
            f"❌ Ошибка API: <code>{html(str(e)[:250])}</code>",
            parse_mode="html"
        )
        return

    if not result or not result.data:
        await event.edit(
            f"{pc} <b>Funstat / .telelog</b>\n\n"
            f"<blockquote>❌ Нет данных по пользователю <code>{html(user_arg)}</code></blockquote>\n\n"
            + by_line(),
            parse_mode="html"
        )
        return

    chats = sorted(result.data, key=lambda c: c.messages_count, reverse=True)
    total = len(chats)
    shown = chats[:40]

    header_name = ""
    if user_info:
        fn = user_info.first_name or ""
        ln = user_info.last_name or ""
        full = (fn + " " + ln).strip() or "—"
        un = f"@{user_info.username}" if user_info.username else "—"
        header_name = (
            f"{eye} <b>{html(full)}</b> · <code>{html(un)}</code>\n"
            f"🆔 <code>{user_info.id}</code>\n"
        )

    lines = []
    for i, c in enumerate(shown, 1):
        chat = c.chat
        title = html(chat.title or "—")
        if chat.username:
            title_link = f'<a href="https://t.me/{chat.username}">{title}</a>'
        else:
            title_link = title
        flags = []
        if c.is_admin:  flags.append("👑")
        if c.is_left:   flags.append("🚪")
        if chat.is_private: flags.append("🔒")
        flag_str = ("  " + "".join(flags)) if flags else ""
        lines.append(f"{i}. {title_link} — <code>{c.messages_count}</code>{flag_str}")

    tail = f"\n\n<i>Показано {len(shown)} из {total}</i>" if total > len(shown) else ""

    text = (
        f"{pc} <b>Funstat · чаты пользователя</b>\n\n"
        f"{header_name}"
        f"<blockquote>" + "\n".join(lines) + "</blockquote>"
        f"{tail}\n\n" + by_line()
    )

    if len(text) > 4000:
        text = text[:3900] + "...\n\n" + by_line()

    await event.edit(text, parse_mode="html", link_preview=False)

