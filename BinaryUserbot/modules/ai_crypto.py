# MODULE_NAME = "AICrypto"
# MODULE_CMD  = ".a <запрос>"
# MODULE_DESC = "AI ассистент через OpenRouter с рабочими функциями TON кошелька"

import json
import asyncio
import aiohttp
from telethon import events
from bot_client import client
import config
import settings

HAS_PYTONIQ = False
Address = begin_cell = LiteBalancer = WalletV5R1 = None

def _ensure_pytoniq():
    global HAS_PYTONIQ, Address, begin_cell, LiteBalancer, WalletV5R1
    if HAS_PYTONIQ:
        return True
    try:
        from pytoniq_core import Address as _Address, begin_cell as _begin_cell
        from pytoniq import LiteBalancer as _LB, WalletV5R1 as _W
        Address = _Address
        begin_cell = _begin_cell
        LiteBalancer = _LB
        WalletV5R1 = _W
        HAS_PYTONIQ = True
        return True
    except ImportError:
        return False

BOT_WALLET_ADDRESS = "UQD5ELNrSgMfKMQ_u3EjLQgJJZLHFIrvxSk18VvSbAu2fRIg"
OSNOVA_ADDRESS = "UQCBo664k7bYKOIDMY57xmHG_BPH2w2-RzFm9p4B9F-NAQKH"
USDT_MASTER_ADDRESS = "EQCxE6mUtQJKFnGfaROTKOt1lZbDiiX1kCixRv7Nw2Id_sDs"
ANTARCTIC_ADDRESS = "UQC2L6utnf70g3d2o88nCgeqVga4zySca1_fO7widDQQ3Qyh"

async def get_wallet():
    if not _ensure_pytoniq():
        return None, None
    if not hasattr(config, "WALLET_SEED") or not config.WALLET_SEED:
        return None, None
    provider = LiteBalancer.from_mainnet_config(1)
    await provider.start_up()

    seed = config.WALLET_SEED.split()
    wallet = await WalletV5R1.from_mnemonic(provider, seed, network_global_id=-239)
    return provider, wallet

async def get_balance(address: str = None) -> str:
    is_main = False
    is_osnova = False

    if not address or address.lower() in ["основной адрес", "мой кошелек"]:
        is_main = True
        if hasattr(config, "WALLET_SEED") and config.WALLET_SEED and _ensure_pytoniq():
            from pytoniq_core.crypto.keys import mnemonic_to_wallet_key
            public_key, _ = mnemonic_to_wallet_key(config.WALLET_SEED.split())
            wallet = WalletV4R2(provider=None, public_key=public_key)
            address = wallet.address.to_str(is_user_friendly=True)
        else:
            address = BOT_WALLET_ADDRESS
    elif address.lower() in ["основа", "burgerbeats.t.me", "burgerbeats"]:
        is_osnova = True
        address = OSNOVA_ADDRESS

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

        if is_main:
            addr_text = "основного кошелька"
        elif is_osnova:
            addr_text = "основы"
        else:
            addr_text = f"адреса {address}"

        return f"Баланс {addr_text}:\nTON: {ton_balance:.4f}\nUSDT: {usdt_balance:.2f}"
    except Exception as e:
        err_msg = str(e)
        explanation = "\n\n💡 <b>Причина:</b> Ошибка при запросе данных из сети TON. Возможно, сервис TonAPI временно недоступен или проблема с интернет-соединением."
        return f"❌ Ошибка при получении баланса:\n<code>{err_msg}</code>{explanation}"

async def send_transaction(amount: str, currency: str, to_address: str) -> str:
    if not _ensure_pytoniq():
        return "Ошибка: не установлена библиотека pytoniq. На сервере выполните: pip install pytoniq"

    if not hasattr(config, "WALLET_SEED") or not config.WALLET_SEED:
        return "Ошибка: в config.py не добавлена или пустая переменная WALLET_SEED."

    to_address_lower = to_address.lower()
    if to_address_lower in ["основной адрес", "мой кошелек"]:
        to_address = BOT_WALLET_ADDRESS
    elif to_address_lower in ["основа", "burgerbeats.t.me", "burgerbeats"]:
        to_address = OSNOVA_ADDRESS
    elif to_address_lower in ["антарктик", "antarctic", "антарктика"]:
        to_address = ANTARCTIC_ADDRESS

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
            minter_address = Address(USDT_MASTER_ADDRESS)
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

        if to_address == BOT_WALLET_ADDRESS:
            addr_text = "основной кошелек (свой)"
        elif to_address == OSNOVA_ADDRESS:
            addr_text = "основу (burgerbeats.t.me)"
        elif to_address == ANTARCTIC_ADDRESS:
            addr_text = "Антарктик"
        else:
            addr_text = f"адрес {to_address}"

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
                        "description": "Адрес кошелька (опционально, если не указан - используется свой)"
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
                    "to_address": {"type": "string", "description": "Адрес получателя или алиас (основа, антарктик)"}
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

    system_prompt = (
        f"Ты ИИ-ассистент, встроенный в Telegram-юзербота. Твоя задача — помогать пользователю с криптовалютой TON (которую теперь называем GRAM).\n"
        f"Кошелек: {BOT_WALLET_ADDRESS}. "
        f"Основа (burgerbeats.t.me): {OSNOVA_ADDRESS}. "
        f"Антарктик: {ANTARCTIC_ADDRESS}.\n"
        f"ПРАВИЛА КОНВЕРТАЦИИ:\n"
        f"- Если сумма в рублях (р, руб, RUB) или долларах ($, USD, баксов) — СНАЧАЛА вызови get_exchange_rates, пересчитай в GRAM или USDT, потом отправь.\n"
        f"- 'тон'/'ton' = GRAM.\n"
        f"ПРАВИЛА АНТАРКТИК:\n"
        f"- Антарктик принимает ТОЛЬКО USDT (не GRAM!).\n"
        f"- Минимум для антарктика: 2 доллара. Если меньше — откажи.\n"
        f"АДРЕСА:\n"
        f"- 'основа'/'burgerbeats' → {OSNOVA_ADDRESS}\n"
        f"- 'антарктик' → {ANTARCTIC_ADDRESS} (только USDT, мин. $2)\n"
        f"- 'мой баланс' → {BOT_WALLET_ADDRESS}\n"
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
                        result = await get_balance(args.get("address", BOT_WALLET_ADDRESS))
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
                                    result2 = await get_balance(args2.get("address", BOT_WALLET_ADDRESS))
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
