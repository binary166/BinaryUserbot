import aiohttp
from urllib.parse import quote
from config import WMO_CODES
from utils import html
from premium_emoji import by_line


def _wmo_text(desc: str) -> str:
    parts = desc.split(" ", 1)
    return parts[1] if len(parts) > 1 else desc


def _image_prompt(weathercode: int, city: str, country: str) -> str:
    base = "stunning cinematic photograph, ultra detailed, 8k, beautiful landscape"
    mapping = {
        0:  "golden hour clear sunny sky, warm light, vibrant colors",
        1:  "mostly sunny sky with soft light clouds, peaceful",
        2:  "dramatic partly cloudy sky, soft light rays piercing through clouds",
        3:  "moody overcast grey sky, soft diffused light, atmospheric",
        45: "thick misty fog rolling over landscape, ethereal mood",
        48: "frosty rime ice covered trees, winter wonderland",
        51: "gentle light drizzle, wet streets, reflections, cozy",
        53: "steady drizzle, moody wet atmosphere, droplets",
        55: "heavy dense drizzle, dramatic rainy mood",
        61: "soft rain, wet leaves, romantic rainy scene",
        63: "moderate rain, rain drops on window, cinematic",
        65: "heavy rainstorm, powerful rain, dramatic lighting",
        71: "light snowfall, soft snowflakes, winter fairy tale",
        73: "moderate snowfall, beautiful snowy landscape",
        75: "heavy snowstorm, magical winter scene, deep snow",
        80: "rain shower, fresh wet atmosphere",
        81: "heavy rain shower, dramatic cloudy sky",
        82: "violent rain shower, epic stormy sky",
        95: "epic thunderstorm, lightning bolts, dramatic dark sky",
        96: "thunderstorm with hail, epic dramatic weather",
        99: "massive thunderstorm with heavy hail, apocalyptic sky",
    }
    mood = mapping.get(weathercode, "beautiful weather, atmospheric")
    city_part = f"over {city}" if city else ""
    if country:
        city_part += f", {country}"
    return f"{base}, {mood} {city_part}, photorealistic, national geographic style"


async def _fetch_weather_image(prompt: str) -> bytes | None:
    encoded = quote(prompt, safe="")
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1280&height=720&nologo=true&enhance=true&seed=-1"
    )
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=aiohttp.ClientTimeout(total=45),
            ) as r:
                if r.status == 200:
                    data = await r.read()
                    if len(data) > 5000:
                        return data
    except Exception as e:
        print(f"[weather img] {e}")
    return None


async def get_weather(city: str) -> tuple[str, bytes | None]:
    async with aiohttp.ClientSession() as s:
        async with s.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "ru"},
            timeout=aiohttp.ClientTimeout(total=10),
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
            timeout=aiohttp.ClientTimeout(total=10),
        ) as r:
            met = await r.json()

    cur       = met["current"]
    wcode     = cur.get("weathercode", 0)
    desc_raw  = WMO_CODES.get(wcode, "🌡 Неизвестно")
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

    prompt = _image_prompt(wcode, city_name, country)
    img = await _fetch_weather_image(prompt)

    return caption, img
