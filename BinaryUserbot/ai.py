import asyncio
import aiohttp
import state
import settings
from config import OR_TOKEN, OR_MODEL, OR_API_URL, BOT_NAME


async def _or_raw(messages: list, max_tokens: int = 1000, temperature: float = 0.8) -> str:
    async with state.ai_semaphore:
        token = settings.get("or_token") or OR_TOKEN
        model = settings.get("or_model") or OR_MODEL
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://t.me",
            "X-Title":       BOT_NAME,
        }
        payload = {
            "model":       model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(OR_API_URL, json=payload, headers=headers,
                              timeout=aiohttp.ClientTimeout(total=40)) as r:
                if r.status != 200:
                    body = await r.text()
                    raise RuntimeError(f"HTTP {r.status}: {body[:300]}")
                data = await r.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter: пустой ответ")
    content = choices[0].get("message", {}).get("content", "").strip()
    if not content:
        raise RuntimeError("OpenRouter: пустой content")
    return content


async def or_request(system: str, user: str, max_chars: int = 0, max_tokens: int = 500) -> str:
    text = await _or_raw([
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ], max_tokens=max_tokens, temperature=0.8)
    return text[:max_chars] if max_chars else text


async def or_chat(history: list, max_tokens: int = 150) -> str:
    text = await _or_raw(history, max_tokens=max_tokens, temperature=1.0)
    return text[:300]
