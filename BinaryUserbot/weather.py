import io
import aiohttp
from urllib.parse import quote
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import WMO_CODES
from utils import html
from premium_emoji import by_line


BASE_DIR = Path(__file__).parent
FONT_CANDIDATES = [
    Path("C:/Windows/Fonts/arial.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
    Path("C:/Windows/Fonts/segoeui.ttf"),
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


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


def _load_font(size: int, bold: bool = False):
    preferred = []
    if bold:
        preferred.extend([
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("C:/Windows/Fonts/segoeuib.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ])
    preferred.extend(FONT_CANDIDATES)
    for path in preferred:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _theme_color(weathercode: int) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
    if weathercode in {0, 1}:
        return (43, 102, 173), (245, 248, 255), (14, 28, 52)
    if weathercode in {2, 3, 45, 48}:
        return (88, 99, 115), (244, 246, 250), (28, 34, 45)
    if weathercode in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return (55, 92, 134), (242, 247, 252), (19, 31, 46)
    if weathercode in {71, 73, 75}:
        return (111, 159, 182), (248, 252, 255), (18, 34, 43)
    if weathercode in {95, 96, 99}:
        return (58, 51, 78), (247, 244, 255), (24, 19, 37)
    return (54, 107, 144), (244, 248, 252), (22, 31, 41)


def _weather_symbol(weathercode: int) -> str:
    if weathercode in {0}:
        return "SUN"
    if weathercode in {1, 2}:
        return "SKY"
    if weathercode in {3, 45, 48}:
        return "FOG"
    if weathercode in {51, 53, 55, 61, 63, 65, 80, 81, 82}:
        return "RAIN"
    if weathercode in {71, 73, 75}:
        return "SNOW"
    if weathercode in {95, 96, 99}:
        return "STORM"
    return "WEATHER"


def _make_weather_card(
    city_name: str,
    country: str,
    desc_text: str,
    temp,
    feels,
    hum,
    wind,
    weathercode: int,
) -> bytes:
    width, height = 1280, 720
    base, panel, text_color = _theme_color(weathercode)
    accent = (
        min(base[0] + 35, 255),
        min(base[1] + 35, 255),
        min(base[2] + 35, 255),
    )
    image = Image.new("RGB", (width, height), base)
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, width, 128), fill=accent)
    draw.rectangle((0, height - 88, width, height), fill=(0, 0, 0))
    draw.rounded_rectangle((56, 170, width - 56, height - 88), radius=32, fill=panel)

    title_font = _load_font(60, bold=True)
    subtitle_font = _load_font(32)
    info_font = _load_font(34)
    big_font = _load_font(132, bold=True)
    small_font = _load_font(24)

    city_line = city_name
    if country:
        city_line = f"{city_name}, {country}"

    draw.text((66, 34), "Binary Weather", font=title_font, fill=(255, 255, 255))
    draw.text((80, 214), city_line, font=title_font, fill=text_color)
    draw.text((80, 300), desc_text, font=subtitle_font, fill=(70, 70, 70))
    draw.text((80, 382), f"Feels like {feels}°C", font=info_font, fill=(55, 55, 55))
    draw.text((80, 438), f"Humidity: {hum}%", font=info_font, fill=(55, 55, 55))
    draw.text((80, 494), f"Wind: {wind} km/h", font=info_font, fill=(55, 55, 55))

    temp_text = f"{temp}°C"
    temp_box = draw.textbbox((0, 0), temp_text, font=big_font)
    temp_w = temp_box[2] - temp_box[0]
    draw.text((width - temp_w - 120, 250), temp_text, font=big_font, fill=(34, 34, 34))
    symbol = _weather_symbol(weathercode)
    sym_font = _load_font(84, bold=True)
    draw.text((width - 260, 420), symbol, font=sym_font, fill=(65, 65, 65))
    draw.text((width - 360, 530), f"Code {weathercode}", font=small_font, fill=(90, 90, 90))

    footer = "Weather data via Open-Meteo"
    footer_box = draw.textbbox((0, 0), footer, font=small_font)
    footer_w = footer_box[2] - footer_box[0]
    draw.text((width - footer_w - 40, height - 62), footer, font=small_font, fill=(255, 255, 255))

    buf = io.BytesIO()
    image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _is_valid_image(data: bytes | None) -> bool:
    if not data:
        return False
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        return True
    except Exception:
        return False


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
    if not _is_valid_image(img):
        img = _make_weather_card(city_name, country, desc_text, temp, feels, hum, wind, wcode)

    return caption, img
