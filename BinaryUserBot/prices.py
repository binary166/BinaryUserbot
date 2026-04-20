"""
Курсы валют и крипты + крипто-конвертор для .calc.
"""
import asyncio
import re
import aiohttp
from datetime import datetime
from utils import html
from premium_emoji import by_line

_price_cache: dict = {}
_price_cache_ts: float = 0


async def fetch_prices() -> dict:
    global _price_cache, _price_cache_ts
    now = asyncio.get_event_loop().time()
    if now - _price_cache_ts < 60 and _price_cache:
        return _price_cache

    data = {}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "bitcoin,the-open-network,ethereum,tether",
                        "vs_currencies": "usd,rub", "include_24hr_change": "true"},
                timeout=aiohttp.ClientTimeout(total=12)
            ) as r:
                crypto = await r.json()
        data["btc_usd"] = crypto.get("bitcoin", {}).get("usd", 0)
        data["btc_rub"] = crypto.get("bitcoin", {}).get("rub", 0)
        data["btc_24h"] = crypto.get("bitcoin", {}).get("usd_24h_change", 0.0) or 0.0
        data["ton_usd"] = crypto.get("the-open-network", {}).get("usd", 0)
        data["ton_rub"] = crypto.get("the-open-network", {}).get("rub", 0)
        data["ton_24h"] = crypto.get("the-open-network", {}).get("usd_24h_change", 0.0) or 0.0
        data["eth_usd"] = crypto.get("ethereum", {}).get("usd", 0)
        data["eth_rub"] = crypto.get("ethereum", {}).get("rub", 0)
        data["eth_24h"] = crypto.get("ethereum", {}).get("usd_24h_change", 0.0) or 0.0
        data["usdt_usd"] = 1.0
        data["usdt_rub"] = crypto.get("tether", {}).get("rub", 0) or 0
    except Exception as e:
        print(f"[prices crypto] {e}")

    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.exchangerate-api.com/v4/latest/USD",
                             timeout=aiohttp.ClientTimeout(total=10)) as r:
                fx = await r.json()
        rates = fx.get("rates", {})
        data["usd_rub"] = rates.get("RUB", data.get("btc_rub", 90) / max(data.get("btc_usd", 1), 1))
        data["eur_rub"] = data["usd_rub"] / rates.get("EUR", 0.9) if rates.get("EUR") else 0
        data["cny_rub"] = data["usd_rub"] / rates.get("CNY", 7.0) if rates.get("CNY") else 0
    except Exception as e:
        print(f"[prices fiat] {e}")

    _price_cache = data
    _price_cache_ts = now
    return data


async def get_prices() -> str:
    p = await fetch_prices()

    def fmt(n, d=2): return f"{n:,.{d}f}".replace(",", " ")
    def chg(c: float) -> str:
        if c > 0: return f"+{c:.2f}%"
        elif c < 0: return f"{c:.2f}%"
        return "0.00%"

    now_str  = datetime.now().strftime("%d.%m.%Y  %H:%M:%S")
    bolt_usd = '<tg-emoji emoji-id="5323761960829862762">⚡️</tg-emoji>'
    bolt_rub = '<tg-emoji emoji-id="5323404142809467476">⚡️</tg-emoji>'
    clock    = '<tg-emoji emoji-id="5199457120428249992">🕘</tg-emoji>'

    lines = [
        "<blockquote>"
        '<tg-emoji emoji-id="5429411030960711866">💬</tg-emoji>  Актуальные курсы'
        "</blockquote>",
        "",
        "-   КРИПТА  -",
        "",
        " Bitcoin (BTC)",
        f"├ {bolt_usd} ${fmt(p.get('btc_usd',0))}   {bolt_rub} {fmt(p.get('btc_rub',0))} ₽",
        f"└ 24ч: {chg(p.get('btc_24h',0))}",
        "Toncoin (TON)",
        f"├ {bolt_usd} ${fmt(p.get('ton_usd',0))}   {bolt_rub} {fmt(p.get('ton_rub',0))} ₽",
        f"└ 24ч: {chg(p.get('ton_24h',0))}",
        "Ethereum (ETH)",
        f"├ {bolt_usd} ${fmt(p.get('eth_usd',0))}   {bolt_rub} {fmt(p.get('eth_rub',0))} ₽",
        f"└ 24ч: {chg(p.get('eth_24h',0))}",
        "",
        "-  ФИАТ  -",
        f"USD/RUB → {fmt(p.get('usd_rub',0))} ₽",
        f"EUR/RUB → {fmt(p.get('eur_rub',0))} ₽",
        f"CNY/RUB → {fmt(p.get('cny_rub',0))} ₽",
        "",
        "",
        f"{clock} Обновлено: {now_str}",
        by_line(),
    ]
    return "\n".join(lines)


async def calc_crypto(expr: str) -> str | None:
    m = re.match(
        r"([\d.,]+)\s*(btc|ton|eth|usdt|usdc)(?:\s+(?:в|in|to)\s*(\$|usd|rub|рублях|рубли|₽))?",
        expr.lower().strip()
    )
    if not m:
        return None

    amount = float(m.group(1).replace(",", "."))
    coin   = m.group(2)
    target = (m.group(3) or "").lower()
    p = await fetch_prices()

    coin_map = {
        "btc":  (p.get("btc_usd", 0),  p.get("btc_rub", 0),  "Bitcoin (BTC)"),
        "ton":  (p.get("ton_usd", 0),  p.get("ton_rub", 0),  "Toncoin (TON)"),
        "eth":  (p.get("eth_usd", 0),  p.get("eth_rub", 0),  "Ethereum (ETH)"),
        "usdt": (1.0,                   p.get("usd_rub", 0),  "Tether (USDT)"),
        "usdc": (1.0,                   p.get("usd_rub", 0),  "USDC"),
    }
    if coin not in coin_map:
        return None

    usd_rate, rub_rate, name = coin_map[coin]
    usd_val = amount * usd_rate
    rub_val = amount * rub_rate

    def fmt(n):
        if n >= 1000:  return f"{n:,.2f}".replace(",", " ")
        elif n >= 1:   return f"{n:.4f}"
        else:          return f"{n:.8f}"

    emoji_map = {"btc": "₿", "ton": "💎", "eth": "⟠", "usdt": "💵", "usdc": "💵"}
    em = emoji_map.get(coin, "💱")

    if target in ("$", "usd"):
        return (
            f"{em} <b>{html(str(amount))} {coin.upper()}</b>\n\n"
            f"💵 <b>${fmt(usd_val)}</b>\n\n"
            f"<i>Курс: 1 {coin.upper()} = ${fmt(usd_rate)}</i>\n" + by_line()
        )
    elif target in ("rub", "рублях", "рубли", "₽"):
        return (
            f"{em} <b>{html(str(amount))} {coin.upper()}</b>\n\n"
            f"💴 <b>{fmt(rub_val)} ₽</b>\n\n"
            f"<i>Курс: 1 {coin.upper()} = {fmt(rub_rate)} ₽</i>\n" + by_line()
        )
    else:
        return (
            f"{em} <b>{html(str(amount))} {coin.upper()} ({name})</b>\n\n"
            f"💵 <b>${fmt(usd_val)}</b>\n"
            f"💴 <b>{fmt(rub_val)} ₽</b>\n\n"
            f"<i>1 {coin.upper()} = ${fmt(usd_rate)} / {fmt(rub_rate)} ₽</i>\n" + by_line()
        )
