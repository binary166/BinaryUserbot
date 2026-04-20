"""
Получение погоды через Open-Meteo + wttr.in картинка.
"""
import aiohttp
from config import WMO_CODES
from utils import html
from premium_emoji import by_line


def _wmo_text(desc: str) -> str:
    parts = desc.split(" ", 1)
    return parts[1] if len(parts) > 1 else desc


async def get_weather(city: str) -> tuple[str, bytes | None]:
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "ru"},
            timeout=aiohttp.ClientTimeout(total=10)
        ) as r:
            geo = await r.json()

    results = geo.get("results")
    if not results:
        return f"❌ Город <b>{html(city)}</b> не найден.", None

    loc       = results[0]
    lat, lon  = loc["latitude"], loc["longitude"]
    city_name = loc.get("name", city)
    country   = loc.get("country", "")
    tz        = loc.get("timezone", "Europe/Moscow")

    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weathercode,precipitation",
                "timezone": tz,
            },
            timeout=aiohttp.ClientTimeout(total=10)
        ) as r:
            met = await r.json()

    cur       = met["current"]
    desc_raw  = WMO_CODES.get(cur.get("weathercode", 0), "🌡 Неизвестно")
    desc_text = _wmo_text(desc_raw)
    temp      = cur.get("temperature_2m", "?")
    feels     = cur.get("apparent_temperature", "?")
    hum       = cur.get("relative_humidity_2m", "?")
    wind      = cur.get("wind_speed_10m", "?")

    caption = (
        f'<tg-emoji emoji-id="5258509201306557640">📍</tg-emoji> <b>{html(city_name)}, {html(country)}</b>\n\n'
        f'- {html(desc_text)}\n\n'
        f'<tg-emoji emoji-id="5258391025281408576">📈</tg-emoji> {temp}°C  (ощущается {feels}°C)\n'
        f'<tg-emoji emoji-id="5258503720928288433">ℹ️</tg-emoji> {hum}% / {wind} км/ч\n\n'
        + by_line()
    )

    img = None
    city_slug = city_name.replace(" ", "+")
    for url in [f"https://v2.wttr.in/{city_slug}.png", f"https://wttr.in/{city_slug}_2.png"]:
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(url, headers={"User-Agent": "curl/7.68.0"},
                                 timeout=aiohttp.ClientTimeout(total=15)) as r:
                    if r.status == 200:
                        img = await r.read()
                        break
        except Exception as e:
            print(f"[weather img] {e}")

    return caption, img
