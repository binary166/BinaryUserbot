import asyncio
import re
from datetime import datetime

import aiohttp

from premium_emoji import by_line
from utils import html

_price_cache: dict = {}
_price_cache_ts: float = 0

CALC_AMOUNT_RE = re.compile(r"^\s*([0-9][0-9\s.,]*)\s*(.+?)\s*$", re.IGNORECASE | re.DOTALL)
CALC_CONVERT_RE = re.compile(r"^(.+?)\s+(?:в|in|to)\s+(.+)$", re.IGNORECASE | re.DOTALL)

ASSET_ALIASES = {
    "btc": {"btc", "bitcoin", "биткоин", "биток"},
    "ton": {"ton", "toncoin", "тон", "тонкоин"},
    "eth": {"eth", "ethereum", "эфир", "эфириум"},
    "usdt": {"usdt", "tether", "тезер", "тезерusd"},
    "usdc": {"usdc", "usdcoin"},
    "usd": {"usd", "$", "доллар", "доллара", "долларов", "доллары", "бакс", "бакса", "баксов", "баксы"},
    "rub": {"rub", "₽", "руб", "р", "рубль", "рубля", "рублей", "рубли", "рублях"},
}

DISPLAY_ASSET = {
    "btc": "BTC",
    "ton": "TON",
    "eth": "ETH",
    "usdt": "USDT",
    "usdc": "USDC",
    "usd": "USD",
    "rub": "₽",
}

ASSET_TITLES = {
    "btc": "Bitcoin (BTC)",
    "ton": "Toncoin (TON)",
    "eth": "Ethereum (ETH)",
    "usdt": "Tether (USDT)",
    "usdc": "USDC",
    "usd": "US Dollar (USD)",
    "rub": "Российский рубль (RUB)",
}

CALC_ASSET_EMOJI = '<tg-emoji emoji-id="5778546023349621090">💎</tg-emoji>'
CALC_MONEY_EMOJI = '<tg-emoji emoji-id="5987661379627128559">💴</tg-emoji>'


async def fetch_prices() -> dict:
    global _price_cache, _price_cache_ts
    now = asyncio.get_event_loop().time()
    if now - _price_cache_ts < 60 and _price_cache:
        return _price_cache

    data = {}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={
                    "ids": "bitcoin,the-open-network,ethereum,tether",
                    "vs_currencies": "usd,rub",
                    "include_24hr_change": "true",
                },
                timeout=aiohttp.ClientTimeout(total=12),
            ) as response:
                crypto = await response.json()
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
    except Exception as exc:
        print(f"[prices crypto] {exc}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.exchangerate-api.com/v4/latest/USD",
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                fx = await response.json()
        rates = fx.get("rates", {})
        data["usd_rub"] = rates.get("RUB", data.get("btc_rub", 90) / max(data.get("btc_usd", 1), 1))
        data["eur_rub"] = data["usd_rub"] / rates.get("EUR", 0.9) if rates.get("EUR") else 0
        data["cny_rub"] = data["usd_rub"] / rates.get("CNY", 7.0) if rates.get("CNY") else 0
    except Exception as exc:
        print(f"[prices fiat] {exc}")

    _price_cache = data
    _price_cache_ts = now
    return data


async def get_prices() -> str:
    prices = await fetch_prices()

    def fmt(number, digits=2):
        return f"{number:,.{digits}f}".replace(",", " ")

    def chg(change: float) -> str:
        if change > 0:
            return f"+{change:.2f}%"
        if change < 0:
            return f"{change:.2f}%"
        return "0.00%"

    now_str = datetime.now().strftime("%d.%m.%Y  %H:%M:%S")
    bolt_usd = '<tg-emoji emoji-id="5323761960829862762">⚡️</tg-emoji>'
    bolt_rub = '<tg-emoji emoji-id="5323404142809467476">⚡️</tg-emoji>'
    clock = '<tg-emoji emoji-id="5199457120428249992">🕘</tg-emoji>'

    lines = [
        "<blockquote>",
        '<tg-emoji emoji-id="5429411030960711866">💬</tg-emoji>  Актуальные курсы',
        "</blockquote>",
        "",
        "-   КРИПТА  -",
        "",
        " Bitcoin (BTC)",
        f"├ {bolt_usd} ${fmt(prices.get('btc_usd', 0))}   {bolt_rub} {fmt(prices.get('btc_rub', 0))} ₽",
        f"└ 24ч: {chg(prices.get('btc_24h', 0))}",
        "Toncoin (TON)",
        f"├ {bolt_usd} ${fmt(prices.get('ton_usd', 0))}   {bolt_rub} {fmt(prices.get('ton_rub', 0))} ₽",
        f"└ 24ч: {chg(prices.get('ton_24h', 0))}",
        "Ethereum (ETH)",
        f"├ {bolt_usd} ${fmt(prices.get('eth_usd', 0))}   {bolt_rub} {fmt(prices.get('eth_rub', 0))} ₽",
        f"└ 24ч: {chg(prices.get('eth_24h', 0))}",
        "",
        "-  ФИАТ  -",
        f"USD/RUB → {fmt(prices.get('usd_rub', 0))} ₽",
        f"EUR/RUB → {fmt(prices.get('eur_rub', 0))} ₽",
        f"CNY/RUB → {fmt(prices.get('cny_rub', 0))} ₽",
        "",
        "",
        f"{clock} Обновлено: {now_str}",
        by_line(),
    ]
    return "\n".join(lines)


def _normalize_asset_name(text: str) -> str:
    normalized = (text or "").lower().replace("ё", "е").strip()
    normalized = normalized.replace("₽", " ₽ ").replace("$", " $ ")
    normalized = re.sub(r"[.,!?:;()[\]{}]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _resolve_asset(text: str | None) -> str | None:
    normalized = _normalize_asset_name(text or "")
    for code, aliases in ASSET_ALIASES.items():
        if normalized in aliases:
            return code
    return None


def _parse_amount(amount_text: str) -> float:
    return float(amount_text.replace(" ", "").replace(",", "."))


def _format_calc_number(value: float) -> str:
    if value >= 1000:
        return f"{value:,.2f}".replace(",", " ")
    if value >= 1:
        return f"{value:.4f}"
    return f"{value:.8f}"


def _format_asset_value(value: float, asset_code: str) -> str:
    if asset_code == "usd":
        return f"${_format_calc_number(value)}"
    if asset_code == "rub":
        return f"{_format_calc_number(value)} ₽"
    return f"{_format_calc_number(value)} {DISPLAY_ASSET[asset_code]}"


def _asset_rates(prices: dict) -> dict[str, tuple[float, float, str]]:
    usd_rub = prices.get("usd_rub", 0) or 0
    rub_usd = (1 / usd_rub) if usd_rub else 0
    return {
        "btc": (prices.get("btc_usd", 0) or 0, prices.get("btc_rub", 0) or 0, ASSET_TITLES["btc"]),
        "ton": (prices.get("ton_usd", 0) or 0, prices.get("ton_rub", 0) or 0, ASSET_TITLES["ton"]),
        "eth": (prices.get("eth_usd", 0) or 0, prices.get("eth_rub", 0) or 0, ASSET_TITLES["eth"]),
        "usdt": (1.0, usd_rub, ASSET_TITLES["usdt"]),
        "usdc": (1.0, usd_rub, ASSET_TITLES["usdc"]),
        "usd": (1.0, usd_rub, ASSET_TITLES["usd"]),
        "rub": (rub_usd, 1.0, ASSET_TITLES["rub"]),
    }


async def calc_crypto(expr: str) -> str | None:
    match = CALC_AMOUNT_RE.match(expr or "")
    if not match:
        return None

    try:
        amount = _parse_amount(match.group(1))
    except ValueError:
        return None

    rest = match.group(2).strip()
    convert_match = CALC_CONVERT_RE.match(rest)
    source_text = convert_match.group(1).strip() if convert_match else rest
    target_text = convert_match.group(2).strip() if convert_match else None

    source = _resolve_asset(source_text)
    target = _resolve_asset(target_text) if target_text else None
    if not source:
        return None

    prices = await fetch_prices()
    asset_map = _asset_rates(prices)
    if source not in asset_map or (target and target not in asset_map):
        return None

    source_usd_rate, source_rub_rate, source_name = asset_map[source]
    if source_rub_rate <= 0:
        return None

    if target:
        _target_usd_rate, target_rub_rate, _target_name = asset_map[target]
        if target_rub_rate <= 0:
            return None
        source_value_rub = amount * source_rub_rate
        converted_value = source_value_rub / target_rub_rate
        rate_value = source_rub_rate / target_rub_rate
        value_emoji = CALC_MONEY_EMOJI if target in {"rub", "usd"} else CALC_ASSET_EMOJI
        return (
            f"{CALC_ASSET_EMOJI} <b>{html(str(amount))} {DISPLAY_ASSET[source]}</b>\n\n"
            f"{value_emoji} <b>{_format_asset_value(converted_value, target)}</b>\n\n"
            f"<i>Курс: 1 {DISPLAY_ASSET[source]} = {_format_asset_value(rate_value, target)}</i>\n" + by_line()
        )

    usd_value = amount * source_usd_rate
    rub_value = amount * source_rub_rate
    return (
        f"{CALC_ASSET_EMOJI} <b>{html(str(amount))} {DISPLAY_ASSET[source]} ({source_name})</b>\n\n"
        f"{CALC_MONEY_EMOJI} <b>${_format_calc_number(usd_value)}</b>\n"
        f"{CALC_MONEY_EMOJI} <b>{_format_calc_number(rub_value)} ₽</b>\n\n"
        f"<i>1 {DISPLAY_ASSET[source]} = ${_format_calc_number(source_usd_rate)} / {_format_calc_number(source_rub_rate)} ₽</i>\n" + by_line()
    )
