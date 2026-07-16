# MODULE_NAME = "AICrypto"
# MODULE_CMD  = ".a <запрос>; .aseed <seed phrase>; .aaddr <slot> <address>"
# MODULE_DESC = "AI ассистент через OpenRouter с рабочими функциями TON кошелька"

import json
import asyncio
import aiohttp
from telethon import events
from bot_client import client
import config
import settings
from utils import html

HAS_PYTONIQ = False
Address = begin_cell = LiteBalancer = WalletV5R1 = WalletV4R2 = None

def _ensure_pytoniq():
    global HAS_PYTONIQ, Address, begin_cell, LiteBalancer, WalletV5R1, WalletV4R2
    if HAS_PYTONIQ:
        return True
    try:
        from pytoniq_core import Address as _Address, begin_cell as _begin_cell
        from pytoniq import LiteBalancer as _LB, WalletV5R1 as _W, WalletV4R2 as _W4
        Address = _Address
        begin_cell = _begin_cell
        LiteBalancer = _LB
        WalletV5R1 = _W
        WalletV4R2 = _W4
        HAS_PYTONIQ = True
        return True
    except ImportError:
        return False

WALLET_SEED_SETTING = "ai_crypto_wallet_seed"
ADDRESS_SETTINGS = {
    "main": "ai_crypto_main_address",
    "osnova": "ai_crypto_osnova_address",
    "antarctic": "ai_crypto_antarctic_address",
    "usdt": "ai_crypto_usdt_master_address",
}
ADDRESS_LABELS = {
    "main": "основной кошелек",
    "osnova": "основа",
    "antarctic": "антарктик",
    "usdt": "USDT master",
}
ADDRESS_ALIASES = {
    "main": {"main", "wallet", "кошелек", "кошелёк", "основной адрес", "мой кошелек", "мой кошелёк", "мой баланс"},
    "osnova": {"osnova", "основа", "burgerbeats", "burgerbeats.t.me"},
    "antarctic": {"antarctic", "антарктик", "антарктика"},
}
ADDRESS_COMMAND_ALIASES = {
    "main": "main",
    "wallet": "main",
    "кошелек": "main",
    "кошелёк": "main",
    "основной": "main",
    "основа": "osnova",
    "osnova": "osnova",
    "burgerbeats": "osnova",
    "антарктик": "antarctic",
    "антарктика": "antarctic",
    "antarctic": "antarctic",
    "usdt": "usdt",
    "юсдт": "usdt",
    "master": "usdt",
}


def _wallet_seed() -> str:
    return (settings.get(WALLET_SEED_SETTING) or getattr(config, "WALLET_SEED", "") or "").strip()


def _setting_str(key: str) -> str:
    return str(settings.get(key) or "").strip()


def _address(slot: str) -> str:
    return _setting_str(ADDRESS_SETTINGS[slot])


def _short_address(address: str) -> str:
    address = address.strip()
    if len(address) <= 14:
        return address
    return f"{address[:6]}...{address[-6:]}"


def _valid_ton_address(address: str) -> bool:
    address = address.strip()
    if not address or len(address) < 24:
        return False
    if _ensure_pytoniq():
        try:
            Address(address)
            return True
        except Exception:
            return False
    return address[:1] in {"E", "U", "k", "0"}


def _slot_by_alias(value: str) -> str | None:
    normalized = value.strip().lower()
    for slot, aliases in ADDRESS_ALIASES.items():
        if normalized in aliases:
            return slot
    return None


def _address_help_text() -> str:
    lines = ["<b>AI Crypto адреса</b>"]
    for slot in ("main", "osnova", "antarctic", "usdt"):
        value = _address(slot)
        status = _short_address(value) if value else "не задан"
        lines.append(f"{ADDRESS_LABELS[slot]}: <code>{html(status)}</code>")
    lines.extend([
        "",
        "<code>.aaddr main EQ...</code> — основной адрес",
        "<code>.aaddr osnova EQ...</code> — адрес основы",
        "<code>.aaddr antarctic EQ...</code> — адрес антарктика",
        "<code>.aaddr usdt EQ...</code> — USDT master contract",
        "<code>.aaddr main off</code> — очистить адрес",
    ])
    return "\n".join(lines)


def _resolve_configured_address(raw_address: str, *, for_balance: bool = False) -> tuple[str | None, str, bool]:
    raw_address = (raw_address or "").strip()
    slot = _slot_by_alias(raw_address)
    if not raw_address:
        slot = "main"

    if slot:
        if slot == "main" and for_balance:
            seed_phrase = _wallet_seed()
            if seed_phrase and _ensure_pytoniq():
                from pytoniq_core.crypto.keys import mnemonic_to_wallet_key
                public_key, _ = mnemonic_to_wallet_key(seed_phrase.split())
                wallet = WalletV4R2(provider=None, public_key=public_key)
                return wallet.address.to_str(is_user_friendly=True), ADDRESS_LABELS[slot], True

        address = _address(slot)
        if address:
            return address, ADDRESS_LABELS[slot], True
        return None, (
            f"❌ Адрес «{ADDRESS_LABELS[slot]}» не задан.\n"
            f"Установите его командой <code>.aaddr {slot} ADDRESS</code>."
        ), False

    return raw_address, f"адреса {raw_address}", False


def _address_prompt_text() -> str:
    lines = []
    main = _address("main")
    osnova = _address("osnova")
    antarctic = _address("antarctic")

    if main:
        lines.append(f"- 'мой баланс'/'мой кошелек' → {main}")
    if osnova:
        lines.append(f"- 'основа'/'burgerbeats' → {osnova}")
    if antarctic:
        lines.append(f"- 'антарктик' → {antarctic} (только USDT, мин. $2)")

    if not lines:
        return (
            "Сохранённых адресов-алиасов нет. Не выдумывай адреса, не подставляй чужие кошельки. "
            "Если нужен перевод или баланс по алиасу, попроси пользователя указать адрес или настроить .aaddr."
        )

    return "АДРЕСА:\n" + "\n".join(lines)


async def get_wallet():
    if not _ensure_pytoniq():
        return None, None
    seed_phrase = _wallet_seed()
    if not seed_phrase:
        return None, None
    provider = LiteBalancer.from_mainnet_config(1)
    await provider.start_up()
    
    seed = seed_phrase.split()
    wallet = await WalletV5R1.from_mnemonic(provider, seed, network_global_id=-239)
    return provider, wallet

async def get_balance(address: str = None) -> str:
    address, addr_text, _ = _resolve_configured_address(address or "", for_balance=True)
    if not address:
        return addr_text

    try:
        ton_balance = 0.0
        usdt_balance = 0.0

        async with aiohttp.ClientSession() as session:
            # Получаем баланс TON
            async with session.get(f"https://tonapi.io/v2/accounts/{address}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ton_balance = data.get('balance', 0) / 1e9

            # Получаем баланс USDT и других токенов
            async with session.get(f"https://tonapi.io/v2/accounts/{address}/jettons") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for balance in data.get('balances', []):
                        jetton = balance.get('jetton', {})
                        if jetton.get('symbol') == 'USDT':
                            decimals = jetton.get('decimals', 6)
                            usdt_balance = int(balance.get('balance', 0)) / (10 ** decimals)
                            break

        return f"Баланс {addr_text}:\nTON: {ton_balance:.4f}\nUSDT: {usdt_balance:.2f}"
    except Exception as e:
        err_msg = str(e)
        explanation = "\n\n💡 <b>Причина:</b> Ошибка при запросе данных из сети TON. Возможно, сервис TonAPI временно недоступен или проблема с интернет-соединением."
        return f"❌ Ошибка при получении баланса:\n<code>{err_msg}</code>{explanation}"

async def send_transaction(amount: str, currency: str, to_address: str) -> str:
    if not _ensure_pytoniq():
        return "Ошибка: не установлена библиотека pytoniq. На сервере выполните: pip install pytoniq"

    if not _wallet_seed():
        return "Ошибка: seed-фраза кошелька не задана. Установите её командой .aseed <seed phrase>."

    to_address, addr_text, _ = _resolve_configured_address(to_address)
    if not to_address:
        return addr_text

    try:
        amount_float = float(amount)
        provider, wallet = await get_wallet()
        if not wallet:
            return "Ошибка инициализации кошелька."

        if currency.lower() in ["ton", "gram"]:
            nano_amount = int(amount_float * 1e9)
            body_cell = begin_cell().store_uint(0, 32).store_string("Sent via AI Bot").end_cell()
            dest_address = to_address
        elif currency.lower() in ["usdt", "$", "usd"]:
            usdt_master = _address("usdt")
            if not usdt_master:
                await provider.close_all()
                return "❌ USDT master contract не задан. Установите его командой .aaddr usdt ADDRESS."
            minter_address = Address(usdt_master)
            stack = await provider.run_get_method(
                address=minter_address,
                method="get_wallet_address",
                stack=[begin_cell().store_address(wallet.address).end_cell().begin_parse()]
            )
            dest_address = stack[0].load_address()
            fwd_payload = begin_cell().store_uint(0, 32).store_string("Sent via AI Bot").end_cell()
            jetton_amount = int(amount_float * 1e6)
            body_cell = (
                begin_cell()
                .store_uint(0xf8a7ea5, 32)
                .store_uint(0, 64)
                .store_coins(jetton_amount)
                .store_address(Address(to_address))
                .store_address(wallet.address)
                .store_bit(0)
                .store_coins(1)
                .store_bit(1)
                .store_ref(fwd_payload)
                .end_cell()
            )
            nano_amount = int(0.05 * 1e9)
        else:
            await provider.close_all()
            return f"❌ Неизвестная валюта: {currency}"

        # Safe transfer handling uninitialized wallets
        try:
            seqno = await wallet.get_seqno()
            is_uninitialized = False
        except Exception as e:
            if "-256" in str(e):
                seqno = 0
                is_uninitialized = True
            else:
                raise e

        if is_uninitialized:
            state_init = wallet.state_init
            wallet_message = wallet.create_wallet_internal_message(
                destination=Address(dest_address),
                value=nano_amount,
                body=body_cell
            )
            transfer_msg = wallet.raw_create_transfer_msg(
                private_key=wallet.private_key,
                seqno=0,
                wallet_id=wallet.wallet_id,
                messages=[wallet_message]
            )
            ext_msg = wallet.create_external_msg(dest=wallet.address, state_init=state_init, body=transfer_msg)
        else:
            wallet_message = wallet.create_wallet_internal_message(
                destination=Address(dest_address),
                value=nano_amount,
                body=body_cell
            )
            transfer_msg = wallet.raw_create_transfer_msg(
                private_key=wallet.private_key,
                seqno=seqno,
                wallet_id=wallet.wallet_id,
                messages=[wallet_message]
            )
            ext_msg = wallet.create_external_msg(dest=wallet.address, body=transfer_msg)

        import urllib.request, json, base64
        boc_b64 = base64.b64encode(ext_msg.serialize().to_boc()).decode()
        req = urllib.request.Request(
            'https://tonapi.io/v2/blockchain/message',
            data=json.dumps({"boc": boc_b64}).encode(),
            headers={'Content-Type': 'application/json'}
        )
        try:
            urllib.request.urlopen(req)
        except Exception as e:
            err_details = e.read().decode() if hasattr(e, 'read') else str(e)
            raise Exception(f"TonAPI rejected transaction: {err_details}")

        await provider.close_all()

        currency_label = "GRAM" if currency.lower() in ["ton", "gram"] else "USDT"
        return f"✅ Успешно отправлено {amount} {currency_label} на {addr_text}"


    except Exception as e:
        err_msg = str(e)
        explanation = ""
        if "-256" in err_msg and "seqno" in err_msg:
            explanation = "\n\n💡 <b>Причина:</b> Кошелек не инициализирован. На нем нет средств, либо контракт кошелька еще не активен в сети TON. Для активации нужно пополнить баланс кошелька (TON)."
        elif "not enough funds" in err_msg.lower() or "balance" in err_msg.lower():
            explanation = "\n\n💡 <b>Причина:</b> Недостаточно TON или USDT на балансе для перевода и оплаты комиссии (газа)."
        elif "timeout" in err_msg.lower():
            explanation = "\n\n💡 <b>Причина:</b> Превышено время ожидания ответа от сети TON. Попробуйте еще раз позже."
        elif "alive peers" in err_msg.lower():
            explanation = "\n\n💡 <b>Причина:</b> Сервера TON (публичные ноды) сейчас перегружены или недоступны. Просто повторите запрос через пару минут."
        else:
            explanation = "\n\n💡 <b>Причина:</b> Неизвестная ошибка блокчейна TON или провайдера. Проверьте правильность адреса получателя и доступность сети."

        return f"❌ Ошибка при отправке транзакции:\n<code>{err_msg}</code>{explanation}"

async def get_exchange_rates() -> str:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://tonapi.io/v2/rates?tokens=ton&currencies=usd,rub') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ton_data = data.get('rates', {}).get('TON', {}).get('prices', {})
                    ton_usd = float(ton_data.get('USD', 0))
                    ton_rub = float(ton_data.get('RUB', 0))
                    if ton_usd > 0:
                        rub_per_usd = ton_rub / ton_usd
                        return (f"Курсы:\n1 GRAM (TON) = {ton_usd:.2f} USD = {ton_rub:.2f} RUB\n"
                                f"1 USDT = 1 USD = {rub_per_usd:.2f} RUB")
                    return "Не удалось получить курсы"
                return "Ошибка получения курсов"
    except Exception as e:
        return f"Ошибка: {e}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_balance",
            "description": "Получить баланс криптовалютного кошелька (TON/GRAM и USDT)",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                    "description": "Адрес кошелька или настроенный через .aaddr алиас. Если не указан - используется свой кошелек, если он задан."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_transaction",
            "description": "Отправить криптовалюту (GRAM или USDT) на указанный адрес. Сумма должна быть уже в целевой валюте (GRAM или USDT).",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {"type": "string", "description": "Сумма перевода в целевой крипте (число)"},
                    "currency": {"type": "string", "description": "Валюта: TON/GRAM или USDT"},
                    "to_address": {"type": "string", "description": "Адрес получателя или настроенный через .aaddr алиас"}
                },
                "required": ["amount", "currency", "to_address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rates",
            "description": "Получить текущие курсы GRAM/TON в USD и RUB. Вызывай ПЕРЕД переводом если пользователь указал сумму в рублях, долларах или другой фиатной валюте.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(?:aseed|seed)(?:\s+([\s\S]+))?$'))
async def ai_crypto_seed_handler(event):
    seed = (event.pattern_match.group(1) or "").strip()
    current_seed = _wallet_seed()

    if not seed:
        status = "задана" if current_seed else "не задана"
        await event.edit(
            "<b>AI Crypto seed</b>\n\n"
            f"Статус: <code>{status}</code>\n\n"
            "<code>.aseed word1 word2 ... word24</code> — сохранить seed-фразу\n"
            "<code>.aseed off</code> — очистить seed-фразу",
            parse_mode="html"
        )
        return

    if seed.lower() in {"off", "clear", "reset", "delete", "выкл", "сброс", "удалить"}:
        settings.set_val(WALLET_SEED_SETTING, None)
        await event.edit("✅ <b>AI Crypto seed очищена.</b>", parse_mode="html")
        return

    words = seed.split()
    if len(words) not in {12, 18, 24}:
        await event.edit(
            "❌ <b>Seed-фраза выглядит неверно.</b>\n\n"
            "Обычно в ней 12, 18 или 24 слова.\n"
            "<code>.aseed word1 word2 ... word24</code>",
            parse_mode="html"
        )
        return

    settings.set_val(WALLET_SEED_SETTING, " ".join(words))
    await event.edit(
        "✅ <b>AI Crypto seed сохранена.</b>\n\n"
        "Теперь модуль <code>.a</code> будет использовать её для кошелька.",
        parse_mode="html"
    )


@client.on(events.NewMessage(outgoing=True, pattern=r'^\.aaddr(?:\s+([\s\S]+))?$'))
async def ai_crypto_address_handler(event):
    args = (event.pattern_match.group(1) or "").strip()
    if not args:
        await event.edit(_address_help_text(), parse_mode="html")
        return

    parts = args.split(maxsplit=1)
    slot = ADDRESS_COMMAND_ALIASES.get(parts[0].lower())
    if not slot:
        await event.edit(
            "❌ Не понял слот адреса.\n\n"
            "Используйте: <code>.aaddr main|osnova|antarctic|usdt ADDRESS</code>",
            parse_mode="html"
        )
        return

    if len(parts) == 1:
        value = _address(slot)
        status = _short_address(value) if value else "не задан"
        await event.edit(
            f"<b>{html(ADDRESS_LABELS[slot])}</b>: <code>{html(status)}</code>",
            parse_mode="html"
        )
        return

    address = parts[1].strip()
    if address.lower() in {"off", "clear", "reset", "delete", "выкл", "сброс", "удалить"}:
        settings.set_val(ADDRESS_SETTINGS[slot], None)
        await event.edit(f"✅ <b>{html(ADDRESS_LABELS[slot])}</b> очищен.", parse_mode="html")
        return

    if not _valid_ton_address(address):
        await event.edit(
            "❌ Адрес выглядит неверно.\n\n"
            "Проверьте TON-адрес и повторите команду.",
            parse_mode="html"
        )
        return

    settings.set_val(ADDRESS_SETTINGS[slot], address)
    await event.edit(
        f"✅ <b>{html(ADDRESS_LABELS[slot])}</b> сохранён: <code>{html(_short_address(address))}</code>",
        parse_mode="html"
    )


@client.on(events.NewMessage(outgoing=True, pattern=r'^\.a (.*)'))
async def ai_crypto_handler(event):
    or_token = settings.get("or_token") or getattr(config, "OR_TOKEN", "")
    if not or_token:
        await event.edit("❌ Не установлен токен для OpenRouter! Установите его через конфиг или настройки менеджера.")
        return

    task = event.pattern_match.group(1)
    await event.edit(getattr(config, "LOADING", "⏳ Загружаю..."), parse_mode="html")

    headers = {
        "Authorization": f"Bearer {or_token}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me",
        "X-Title": getattr(config, "BOT_NAME", "BinaryUserbot")
    }

    address_prompt = _address_prompt_text()
    antarctic_rules = ""
    if _address("antarctic"):
        antarctic_rules = (
            "ПРАВИЛА АНТАРКТИК:\n"
            "- Антарктик принимает ТОЛЬКО USDT (не GRAM!).\n"
            "- Минимум для антарктика: 2 доллара. Если меньше — откажи.\n"
        )

    system_prompt = (
        f"Ты ИИ-ассистент, встроенный в Telegram-юзербота. Твоя задача — помогать пользователю с криптовалютой TON (которую теперь называем GRAM).\n"
        f"{address_prompt}\n"
        f"ПРАВИЛА КОНВЕРТАЦИИ:\n"
        f"- Если сумма в рублях (р, руб, RUB) или долларах ($, USD, баксов) — СНАЧАЛА вызови get_exchange_rates, пересчитай в GRAM или USDT, потом отправь.\n"
        f"- 'тон'/'ton' = GRAM.\n"
        f"{antarctic_rules}"
        f"ОТВЕЧАЙ СТРОГО В HTML (<b>жирный</b>, <i>курсив</i>, <code>код</code>). НИКАКОГО Markdown. "
        f"Используй Telegram Premium эмодзи: <tg-emoji emoji-id=\"ID\">ЭМОДЗИ</tg-emoji>. "
        f"ID: Деньги:5334754169414766749💵, Молния:5388849303982716989⚡️, Внимание:5775887550262546277⚠️, Глаза:5424885441100782420👀, Шестеренка:5258152182150077732⚙️, Кодер:5190458330719461749🧑‍💻."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task}
    ]

    or_model = settings.get("or_model") or getattr(config, "OR_MODEL", "openai/gpt-4o-mini")

    payload = {
        "model": or_model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "max_tokens": 1500
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(getattr(config, "OR_API_URL", "https://openrouter.ai/api/v1/chat/completions"), headers=headers, json=payload) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    explanation = "\n\n💡 <b>Причина:</b> Ошибка на стороне ИИ-провайдера (OpenRouter). Возможно, закончился баланс или сервис временно недоступен."
                    await event.edit(f"❌ Ошибка API ИИ ({resp.status}):\n<code>{err_text[:500]}</code>{explanation}", parse_mode="html")
                    return

                data = await resp.json()
                message = data['choices'][0]['message']

                if "tool_calls" in message and message["tool_calls"]:
                    tool_call = message["tool_calls"][0]
                    func_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"]["arguments"])
                    result = ""
                    await event.edit(f"<blockquote><b><tg-emoji emoji-id=\"5877613700344450910\">⏳</tg-emoji> Выполняю...</b></blockquote>", parse_mode="html")

                    if func_name == "get_balance":
                        result = await get_balance(args.get("address"))
                    elif func_name == "send_transaction":
                        result = await send_transaction(args["amount"], args["currency"], args["to_address"])
                    elif func_name == "get_exchange_rates":
                        result = await get_exchange_rates()

                    # Send result back to AI for follow-up (e.g. convert then send)
                    messages.append(message)
                    messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": str(result)})
                    payload2 = {"model": or_model, "messages": messages, "tools": tools, "tool_choice": "auto", "max_tokens": 1500}

                    async with session.post(getattr(config, "OR_API_URL", "https://openrouter.ai/api/v1/chat/completions"), headers=headers, json=payload2) as resp2:
                        if resp2.status == 200:
                            data2 = await resp2.json()
                            msg2 = data2['choices'][0]['message']

                            if "tool_calls" in msg2 and msg2["tool_calls"]:
                                tc2 = msg2["tool_calls"][0]
                                fn2 = tc2["function"]["name"]
                                args2 = json.loads(tc2["function"]["arguments"])
                                await event.edit(f"<blockquote><b><tg-emoji emoji-id=\"5877613700344450910\">⏳</tg-emoji> Выполняю транзакцию...</b></blockquote>", parse_mode="html")

                                if fn2 == "get_balance":
                                    result2 = await get_balance(args2.get("address"))
                                elif fn2 == "send_transaction":
                                    result2 = await send_transaction(args2["amount"], args2["currency"], args2["to_address"])
                                elif fn2 == "get_exchange_rates":
                                    result2 = await get_exchange_rates()
                                else:
                                    result2 = "Неизвестная функция"

                                messages.append(msg2)
                                messages.append({"role": "tool", "tool_call_id": tc2["id"], "content": str(result2)})
                                payload3 = {"model": or_model, "messages": messages, "max_tokens": 1500}
                                async with session.post(getattr(config, "OR_API_URL", "https://openrouter.ai/api/v1/chat/completions"), headers=headers, json=payload3) as resp3:
                                    if resp3.status == 200:
                                        data3 = await resp3.json()
                                        final_reply = data3['choices'][0]['message'].get('content', str(result2))
                                        await event.edit(final_reply[:4090], parse_mode="html")
                                    else:
                                        await event.edit(f"<b>Результат:</b>\n{result2}"[:4090], parse_mode="html")
                            else:
                                ai_reply = msg2.get('content', str(result))
                                await event.edit(ai_reply[:4090], parse_mode="html")
                        else:
                            final_text = f"<b>Действие:</b> <code>{func_name}</code>\n<b>Результат:</b>\n{result}"
                            await event.edit(final_text[:4090], parse_mode="html")
                else:
                    ai_reply = message.get('content', 'Нет ответа')
                    await event.edit(ai_reply[:4090], parse_mode="html")
    except Exception as e:
        err_msg = str(e)[:1000]
        explanation = "\n\n💡 <b>Причина:</b> Внутренняя ошибка работы модуля ИИ-ассистента."
        await event.edit(f"❌ Произошла системная ошибка:\n<code>{err_msg}</code>{explanation}", parse_mode="html")
