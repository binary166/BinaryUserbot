import asyncio
import datetime
import hashlib
import io
import json
import os
import random
import re
import shutil
import string
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import aiohttp
from telethon import Button, TelegramClient, events
from telethon.errors import MessageNotModifiedError, UserAlreadyParticipantError
from telethon.tl import functions, types
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.utils import get_peer_id
import state
import settings
from bot_client import client as user_client, ensure_runtime_permissions
from config import (
    API_HASH, API_ID, BOT_NAME, BOT_VERSION, MY_ID,
    OR_API_URL, OR_MODEL, OR_TOKEN,
    EBALAJ_SYSTEM, TROLL_SYSTEM,
)
from terminal_runner import decode_terminal_output, spawn_terminal_process
from utils import html


BASE_DIR = Path(__file__).parent
ASSETS_DIR = BASE_DIR / "assets"
AVATAR_PATH = ASSETS_DIR / "avatar.jpg"

SITE_URL = "https://userbot.bincore.site/"
GITHUB_ZIP_URL = "https://github.com/binary166/BinaryUserbot/archive/refs/heads/main.zip"
GITHUB_REPO_HINT = "binary166/BinaryUserbot"

BOT_TITLE = "BinaryUB - Manager"
BOT_DESCRIPTION_TEMPLATE = "👨‍💻 Разработчик: @burgerbeats\n💚 Владелец: {owner}"
BOT_USERNAME_PREFIX = "binaryUB_"
BOT_USERNAME_SUFFIX = "_bot"
BOT_USERNAME_RANDOM_LEN = 9

REQUIRED_CHANNELS = ("@binary_news", "@GID_ScamBase", "@binary_ub")
UPDATE_CHANNEL = "@binary_ub"
UPDATE_CHANNEL_ID = -1003713838499
UPDATE_MESSAGE_ID = 3
UPDATE_POLL_SECONDS = 600

manager_client: TelegramClient | None = None
manager_me = None
update_monitor_task: asyncio.Task | None = None
pending_inputs: dict[int, dict] = {}
terminal_jobs: dict[int, dict] = {}
CONFIG_VERSION_RE = re.compile(r"^(\s*BOT_VERSION\s*=\s*['\"])([^'\"]+)(['\"].*)$", re.MULTILINE)


def tg_emoji(emoji_id: str, fallback: str) -> str:
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def _strip_tg_emoji_tags(text: str) -> str:
    return re.sub(r"<tg-emoji\b[^>]*>(.*?)</tg-emoji>", r"\1", text or "", flags=re.IGNORECASE | re.DOTALL)


def _inline_seed_text(text: str) -> str:
    return _strip_tg_emoji_tags(text)


def _inline_safe_buttons(buttons):
    if not buttons:
        return buttons

    if not isinstance(buttons, (list, tuple)):
        buttons = [[buttons]]

    normalized = []
    for row in buttons:
        if not isinstance(row, (list, tuple)):
            row = [row]
        new_row = []
        for button in row:
            if button is None:
                continue
            text = getattr(button, "text", "") or ""
            data = getattr(button, "data", None)
            url = getattr(button, "url", None)
            if data is not None:
                new_row.append(Button.inline(text, data))
            elif url:
                new_row.append(Button.url(text, url))
            else:
                new_row.append(button)
        if new_row:
            normalized.append(new_row)
    return normalized


E_SB = tg_emoji("5895311993555915037", "⚙️")
E_FEATURES = tg_emoji("5909015791088439934", "✨")
E_CREATE = tg_emoji("6008118472066732010", "🤖")
E_LINK = tg_emoji("5924681813149618024", "🔗")
E_OK = tg_emoji("5805532930662996322", "✅")
E_MENU = tg_emoji("5877260593903177342", "⚙️")
E_OR_TOKEN = tg_emoji("5875033614705495771", "🔑")
E_OR_MODEL = tg_emoji("5877485980901971030", "🧠")
E_INPUT = tg_emoji("5875019892284985369", "✍️")
E_RESTART = tg_emoji("5936170807716745162", "🔄")
E_RESTART_Q = tg_emoji("6005843436479975944", "❓")
E_RESTART_OK = tg_emoji("5843908536467198016", "✅")
E_UP_TO_DATE = tg_emoji("5931409969613116639", "✅")
E_UPDATE = tg_emoji("5988023995125993550", "🆕")
E_WARN = tg_emoji("5775887550262546277", "⚠️")
E_INSTALL = tg_emoji("5899757765743615694", "📦")
E_UPDATE_OK = tg_emoji("5967688845397855939", "✅")
E_TERMINAL = tg_emoji("5424753383741346604", "🖥")
E_ATTENTION = tg_emoji("5881702736843511327", "⚠️")
E_WAIT = tg_emoji("5776213190387961618", "⏳")
E_CMD_OK = tg_emoji("5825794181183836432", "✅")
E_MISSING = tg_emoji("5962916891918864588", "❌")


def mask_token(token: str | None) -> str:
    if not token:
        return "не задан"
    token = str(token)
    if len(token) <= 16:
        return token[:4] + "..."
    return f"{token[:10]}...{token[-6:]}"


def current_or_token() -> str:
    return settings.get("or_token") or OR_TOKEN


def current_or_model() -> str:
    return settings.get("or_model") or OR_MODEL


def manager_token() -> str | None:
    return settings.get("manager_bot_token")


def is_manager_running() -> bool:
    return bool(manager_client and manager_client.is_connected() and manager_me)


def build_bot_description(owner: str) -> str:
    owner = (owner or "unknown").strip()
    return BOT_DESCRIPTION_TEMPLATE.format(owner=owner)


async def get_owner_label() -> str:
    me = await user_client.get_me()
    username = getattr(me, "username", None)
    if username:
        return f"@{username}"
    return f"ID {getattr(me, 'id', MY_ID)}"


def _button(text: str, data: str, style=None, icon=None):
    try:
        return Button.inline(text, data.encode("utf-8"), style=style, icon=icon)
    except TypeError:
        return Button.inline(text, data.encode("utf-8"))


def _url_button(text: str, url: str, style=None, icon=None):
    try:
        return Button.url(text, url, style=style, icon=icon)
    except TypeError:
        return Button.url(text, url)


def back_buttons():
    return [[_button("Назад", "back_main")]]


def main_buttons():
    return [
        [_button("Проверить обновления", "check_updates", style="primary")],
        [_button("Управление OpenRouter", "openrouter", style="primary")],
        [_button("Режимы и антивирус", "modes", style="primary")],
        [_button("Выгрузить чаты", "export_chats", style="primary")],
        [_button("Перезапустить юзербота", "restart_ask", style="danger")],
        [_button("Открыть терминал", "terminal", style="primary")],
        [_url_button("Сайт юзербота", SITE_URL)],
    ]


def openrouter_buttons():
    return [
        [_button("Сменить токен", "or_change_token", style="primary")],
        [_button("Сменить модель", "or_change_model", style="primary")],
        [_button("Назад", "back_main")],
    ]


def modes_buttons():
    antivirus = bool(settings.get("antivirus_enabled", False))
    antivirus_label = "Антивирус: вкл" if antivirus else "Антивирус: выкл"
    antivirus_style = "success" if antivirus else "danger"
    return [
        [_button("Ебалай промпт", "mode_ebalaj_prompt", style="primary")],
        [_button("Тролль промпт", "mode_troll_prompt", style="primary")],
        [_button(antivirus_label, "antivirus_toggle", style=antivirus_style)],
        [_button("Назад", "back_main")],
    ]


def restart_confirm_buttons():
    return [[_button("Да", "restart_yes", style="danger"), _button("Нет", "back_main")]]


def update_buttons():
    return [[_button("Установить обновление", "install_update", style="success")], [_button("Назад", "back_main")]]


def terminal_wait_buttons():
    return [[_button("Отмена", "terminal_cancel", style="danger")]]


def terminal_done_buttons():
    return [[_button("Вернутся в меню", "back_main")], [_button("Отправить ещё команду", "terminal")]]


def help_site_buttons():
    return [[_url_button("Сайт юзербота", SITE_URL)]]


def main_buttons_inline():
    return [
        [Button.inline("Проверить обновления", b"check_updates")],
        [Button.inline("Управление OpenRouter", b"openrouter")],
        [Button.inline("Режимы и антивирус", b"modes")],
        [Button.inline("Выгрузить чаты", b"export_chats")],
        [Button.inline("Перезапустить юзербота", b"restart_ask")],
        [Button.inline("Открыть терминал", b"terminal")],
        [Button.url("Сайт юзербота", SITE_URL)],
    ]


async def _inline_text_article(builder, title: str, description: str, text: str, buttons=None, prefix: str = "result"):
    result_id = f"{prefix}-{random.getrandbits(64):016x}"
    return await builder.article(
        title=title,
        description=description,
        text=_inline_seed_text(text),
        parse_mode="html",
        buttons=_inline_safe_buttons(buttons),
        id=result_id,
    )


def _inline_message_id_from_event(event):
    query = getattr(event, "query", None)
    inline_id = getattr(query, "msg_id", None)
    if isinstance(inline_id, (types.InputBotInlineMessageID, types.InputBotInlineMessageID64)):
        return inline_id
    return None


async def _raw_edit_inline_message(inline_msg_id, text: str, buttons=None, *, link_preview: bool = False) -> bool:
    reply_markup = manager_client.build_reply_markup(_inline_safe_buttons(buttons))
    try:
        parsed_text, entities = await manager_client._parse_message_text(text, "html")
        await manager_client(
            functions.messages.EditInlineBotMessageRequest(
                id=inline_msg_id,
                message=parsed_text,
                no_webpage=not link_preview,
                entities=entities,
                reply_markup=reply_markup,
            )
        )
    except Exception:
        simplified_text = _inline_seed_text(text)
        parsed_text, entities = await manager_client._parse_message_text(simplified_text, "html")
        await manager_client(
            functions.messages.EditInlineBotMessageRequest(
                id=inline_msg_id,
                message=parsed_text,
                no_webpage=not link_preview,
                entities=entities,
                reply_markup=reply_markup,
            )
        )
    return True


async def _safe_event_edit(event, text: str, *, buttons=None, link_preview: bool = False):
    inline_msg_id = _inline_message_id_from_event(event)
    if inline_msg_id is not None:
        try:
            return await _raw_edit_inline_message(inline_msg_id, text, buttons, link_preview=link_preview)
        except MessageNotModifiedError:
            return True
        except Exception as e:
            print(f"[manager_bot inline edit] {e}")
            try:
                return await event.edit(_inline_seed_text(text), parse_mode="html", buttons=_inline_safe_buttons(buttons), link_preview=link_preview)
            except Exception as inner:
                print(f"[manager_bot inline edit fallback] {inner}")
                return False

    try:
        return await event.edit(text, parse_mode="html", buttons=buttons, link_preview=link_preview)
    except MessageNotModifiedError:
        return True
    except TypeError:
        return await event.edit(text, parse_mode="html", buttons=buttons)
    except Exception as e:
        print(f"[manager_bot event edit] {e}")
        return False


def main_menu_text() -> str:
    return (
        f"{E_MENU} <b>Настройки Binary Userbot {BOT_VERSION}</b>\n\n"
        f"<blockquote>{E_FEATURES} Другие настройки - .setting</blockquote>"
    )


def _prompt_preview(value: str | None, limit: int = 120) -> str:
    text = " ".join((value or "").split())
    if not text:
        return "не задан"
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return html(text)


def current_ebalaj_prompt() -> str:
    value = settings.get("ebalaj_system_prompt")
    value = str(value).strip() if value else ""
    return value or EBALAJ_SYSTEM


def current_troll_prompt() -> str:
    value = settings.get("troll_system_prompt")
    value = str(value).strip() if value else ""
    return value or TROLL_SYSTEM


def modes_menu_text() -> str:
    antivirus = "включен" if settings.get("antivirus_enabled", False) else "выключен"
    return (
        f"<blockquote><b>Режимы Binary Userbot</b></blockquote>\n\n"
        f"Ебалай промпт: <code>{_prompt_preview(current_ebalaj_prompt())}</code>\n"
        f"Тролль промпт: <code>{_prompt_preview(current_troll_prompt())}</code>\n"
        f"Антивирус: <b>{antivirus}</b>\n\n"
        f"Нажмите кнопку и ответьте на это сообщение новым промптом."
    )


def subscription_required_text() -> str:
    return (
        f"{E_WARN} Для работы функций Binary Userbot нужно обязательно быть подписчиком следующих каналов:\n\n"
        "@binary_news\n"
        "@GID_ScamBase\n"
        "@binary_ub\n\n"
        f"{E_MISSING} У вас отсутствует подписка на один из этих ресурсов."
    )


def sb_status_text() -> str:
    token = manager_token()
    username = settings.get("manager_bot_username") or "не задан"
    status = "подключен" if is_manager_running() else "не подключен"
    return (
        f"<blockquote><b>{E_FEATURES} Добавьте множество новых функций в своего юзербота!</b></blockquote>\n\n"
        f"Текущий токен бота: <code>{html(mask_token(token))}</code>\n"
        f"Статус вашего бота: <b>{status}</b>\n"
        f"Юзернейм вашего бота: <code>{html(username)}</code>\n\n"
        f"{E_CREATE} Чтобы юзербот <b>автоматически</b> создал вам бота напишите команду: <b>.sbc</b>\n\n"
        f"{E_LINK} Чтобы <b>привязать/перепривязать</b> бота по токену напишите команду: <b>.sbt токен бота</b>"
    )


def bot_created_text(username: str) -> str:
    return f"<blockquote><b>{E_OK} Бот успешно создан!</b></blockquote>\n\nЮзернейм вашего бота: {html(username)}"


def bot_linked_text(username: str) -> str:
    return f"<blockquote><b>{E_OK} Бот успешно привязан!</b></blockquote>\n\nЮзернейм вашего бота: {html(username)}"


def openrouter_menu_text() -> str:
    return (
        f"<blockquote>"
        f"{E_OR_TOKEN} <b>Токен OpenRouter:</b> <code>{html(mask_token(current_or_token()))}</code>\n\n"
        f"{E_OR_MODEL} <b>Модель:</b> <code>{html(current_or_model())}</code>"
        f"</blockquote>"
    )


def input_prompt_text(kind: str, invalid: str | None = None) -> str:
    if kind == "or_token":
        prompt = "Ответьте на это сообщение вашим новым OpenRouter токеном:"
    elif kind == "or_model":
        prompt = "Ответьте на это сообщение новым названием OpenRouter ИИ модели:"
    elif kind == "mode_ebalaj_prompt":
        prompt = "Ответьте на это сообщение новым системным промптом для режима Ебалай:"
    elif kind == "mode_troll_prompt":
        prompt = "Ответьте на это сообщение новым системным промптом для режима Тролль:"
    else:
        prompt = "Ответьте на это сообщение нужным значением:"
    prefix = f"{html(invalid)}\n\n" if invalid else ""
    return f"<blockquote><b>{prefix}{E_INPUT} {prompt}</b></blockquote>"


def mode_input_buttons():
    return [[_button("Назад", "back_modes")]]


def restart_question_text() -> str:
    return f"<blockquote><b>{E_RESTART_Q} Точно перезапустить?</b></blockquote>"


def restarting_text() -> str:
    return f"<blockquote><b>{E_RESTART} Перезапускаю юзербота...</b></blockquote>"


def restarted_success_text() -> str:
    return f"<blockquote><b>{E_RESTART_OK} Binary Userbot успешно перезагружен!</b></blockquote>"


def up_to_date_text() -> str:
    return f"<blockquote><b>{E_UP_TO_DATE} У вас установлена последняя версия.</b></blockquote>"


def update_available_text(latest_version: str, changelog: str | None = None) -> str:
    changelog_block = ""
    changelog = (changelog or "").strip("\r\n")
    if changelog:
        changelog_block = f"\n\n<blockquote expandable>{html(changelog)}</blockquote>"
    return (
        f"<blockquote><b>{E_UPDATE} Доступно обновление!</b></blockquote>\n\n"
        f"Вышла новая версия Binary Userbot: <b>{html(latest_version)}</b>"
        f"{changelog_block}\n\n"
        f"{E_WARN} <b>Советуем скорее обновить своего юзербота по кнопке ниже, так как с каждым обновлением "
        f"мы улучшаем его, добавляя новых функций.</b>"
    )


def installing_update_text() -> str:
    return f"<blockquote><b>{E_INSTALL} Устанавливаю обновление, ждите...</b></blockquote>"


def updated_success_text() -> str:
    return f"<blockquote><b>{E_UPDATE_OK} Ваш юзербот обновлён до последней версии, приятного пользования!</b></blockquote>"


def terminal_prompt_text() -> str:
    history = list(settings.get("manager_terminal_history", []) or [])[-5:]
    history_text = "\n".join(f"{i + 1}. {html(cmd)}" for i, cmd in enumerate(history)) or "нет команд"
    return (
        f"{E_TERMINAL} <b>Terminal</b>\n\n"
        f"<b>Последние 5 команд:</b>\n<blockquote><code>{history_text}</code></blockquote>\n\n"
        f"{E_ATTENTION} <b>Внимание!</b> Ни в коем случае не пишите незнакомых команд и не запускайте незнакомый код.\n\n"
        f"<b>Ответьте на это сообщение вашей командой:</b>"
    )


def terminal_wait_text() -> str:
    return f"<blockquote><b>{E_WAIT} Жду ответа от сервера...</b></blockquote>"


def terminal_done_text(command: str, output: str) -> str:
    if len(output) > 2800:
        output = output[:2800] + "\n...(обрезано)"
    return (
        f"<blockquote><b>{E_CMD_OK} Команда успешно выполнена!</b></blockquote>\n\n"
        f"<b>Ваша команда:</b> <code>{html(command)}</code>\n\n"
        f"<b>Ответ от сервера:</b>\n\n"
        f"<blockquote><code>{html(output or '(нет вывода)')}</code></blockquote>"
    )


def _version_tuple(version: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", version or "")
    return tuple(int(x) for x in nums) if nums else (0,)


def _is_newer(latest: str, current: str = BOT_VERSION) -> bool:
    return _version_tuple(latest) > _version_tuple(current)


def _random_bot_username() -> str:
    alphabet = string.ascii_lowercase + string.digits
    tail = "".join(random.choice(alphabet) for _ in range(BOT_USERNAME_RANDOM_LEN))
    return f"{BOT_USERNAME_PREFIX}{tail}{BOT_USERNAME_SUFFIX}"


def _parse_bot_token(text: str) -> str | None:
    match = re.search(r"\b\d{6,}:[A-Za-z0-9_-]{25,}\b", text or "")
    return match.group(0) if match else None


def _session_name_for_token(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]
    return str(BASE_DIR / f"manager_bot_{digest}")


import time
_last_channel_check = 0
_channel_check_result = (False, [])

async def ensure_required_channels() -> tuple[bool, list[str]]:
    global _last_channel_check, _channel_check_result
    now = time.time()
    if now - _last_channel_check < 3600 and _channel_check_result[0]:
        return _channel_check_result

    missing: list[str] = []
    for channel in REQUIRED_CHANNELS:
        try:
            entity = await user_client.get_entity(channel)
            if getattr(entity, "left", False):
                await user_client(JoinChannelRequest(channel))
        except Exception:
            try:
                await user_client(JoinChannelRequest(channel))
            except Exception:
                missing.append(channel)
                
    _channel_check_result = (not missing, missing)
    if _channel_check_result[0]:
        _last_channel_check = now
    return _channel_check_result


async def _guard_event(event) -> bool:
    sender_id = getattr(event, "sender_id", None)
    if int(sender_id or 0) != int(MY_ID):
        try:
            await event.answer("Нет доступа", alert=True)
        except Exception:
            pass
        return False

    ok, _missing = await ensure_required_channels()
    if not ok:
        try:
            await _safe_event_edit(event, subscription_required_text(), buttons=None, link_preview=False)
        except Exception:
            await event.respond(subscription_required_text(), parse_mode="html", link_preview=False)
        return False
    return True


async def _show_main(event) -> None:
    pending_inputs.pop(MY_ID, None)
    try:
        await _safe_event_edit(event, main_menu_text(), buttons=main_buttons(), link_preview=False)
    except Exception as e:
        print(f"[manager_bot show main] {e}")
        if _inline_message_id_from_event(event) is None:
            await event.respond(main_menu_text(), parse_mode="html", buttons=main_buttons(), link_preview=False)
        else:
            try:
                await event.answer("Не удалось открыть меню", alert=True)
            except Exception:
                pass


async def _show_modes(event) -> None:
    pending_inputs.pop(MY_ID, None)
    try:
        await _safe_event_edit(event, modes_menu_text(), buttons=modes_buttons(), link_preview=False)
    except Exception as e:
        print(f"[manager_bot show modes] {e}")
        if _inline_message_id_from_event(event) is None:
            await event.respond(modes_menu_text(), parse_mode="html", buttons=modes_buttons(), link_preview=False)
        else:
            try:
                await event.answer("Не удалось открыть режимы", alert=True)
            except Exception:
                pass


async def _send_main_menu(chat_id: int) -> None:
    if manager_client is None:
        return
    await manager_client.send_message(
        chat_id,
        main_menu_text(),
        parse_mode="html",
        buttons=main_buttons(),
        link_preview=False,
    )


async def _handle_start(event) -> None:
    if int(event.sender_id or 0) != int(MY_ID):
        return
    ok, _missing = await ensure_required_channels()
    if not ok:
        await event.respond(subscription_required_text(), parse_mode="html", link_preview=False)
        return
    await _send_main_menu(event.chat_id)


async def validate_bot_token(token: str) -> tuple[bool, str | None, str | None, int | None]:
    temp_client = TelegramClient(_session_name_for_token(token), API_ID, API_HASH)
    try:
        await temp_client.start(bot_token=token)
        me = await temp_client.get_me()
        username = f"@{me.username}" if getattr(me, "username", None) else None
        return True, username, None, getattr(me, "id", None)
    except Exception as e:
        return False, None, str(e), None
    finally:
        try:
            await temp_client.disconnect()
        except Exception:
            pass


async def start_manager_bot(token: str | None = None) -> bool:
    global manager_client, manager_me

    token = token or manager_token()
    if not token:
        return False

    if manager_client:
        try:
            await manager_client.disconnect()
        except Exception:
            pass

    bot = TelegramClient(_session_name_for_token(token), API_ID, API_HASH)
    bot.parse_mode = "html"
    bot.session.save_entities = False
    _register_handlers(bot)
    try:
        await bot.start(bot_token=token)
        manager_client = bot
        manager_me = await bot.get_me()
        settings.set_val("manager_bot_username", f"@{manager_me.username}" if manager_me.username else None)
        settings.set_val("manager_bot_id", getattr(manager_me, "id", None))
        asyncio.create_task(ensure_manager_bot_configured())
        return True
    except Exception as e:
        print(f"[manager_bot] start failed: {e}")
        manager_client = None
        manager_me = None
        try:
            await bot.disconnect()
        except Exception:
            pass
        return False


async def start_update_monitor() -> None:
    global update_monitor_task
    if update_monitor_task and not update_monitor_task.done():
        return
    update_monitor_task = asyncio.create_task(_update_monitor_loop())


async def _update_monitor_loop() -> None:
    await asyncio.sleep(30)
    while True:
        try:
            latest, changelog = await get_latest_update_info()
            if latest and _is_newer(latest) and settings.get("last_notified_update") != latest:
                settings.set_val("last_notified_update", latest)
                if is_manager_running() and manager_client:
                    await manager_client.send_message(
                        MY_ID,
                        update_available_text(latest, changelog),
                        parse_mode="html",
                        buttons=update_buttons(),
                        link_preview=False,
                    )
        except Exception as e:
            print(f"[manager_bot update monitor] {e}")
        await asyncio.sleep(UPDATE_POLL_SECONDS)


async def send_help_via_manager(chat_id: int, caption: str) -> bool:
    try:
        from help_faq import get_help_text
        caption = get_help_text(force_premium=True)
    except Exception:
        pass
    if is_manager_running() and manager_client:
        try:
            await manager_client.send_message(
                chat_id,
                caption,
                parse_mode="html",
                buttons=help_site_buttons(),
                link_preview=False,
            )
            return True
        except Exception as e:
            print(f"[manager_bot help fallback] {e}")

    try:
        await user_client.send_message(chat_id, caption, parse_mode="html", link_preview=False)
        return True
    except Exception as e:
        print(f"[help send error] {e}")
        return False


async def send_help_via_inline(chat_id: int) -> bool:
    username = settings.get("manager_bot_username")
    if not (is_manager_running() and username):
        return False
    try:
        results = await user_client.inline_query(username.lstrip("@"), "help")
        if not results:
            return False
        await results[0].click(chat_id)
        return True
    except Exception as e:
        print(f"[manager_bot inline help fallback] {e}")
        return False


async def cmd_sb(event) -> None:
    await event.message.edit(sb_status_text(), parse_mode="html", link_preview=False)


async def cmd_sbt(event, token: str) -> None:
    token = (token or "").strip()
    if not token or not re.match(r"^\d{9,10}:[a-zA-Z0-9_-]{35}$", token):
        await event.message.edit(
            f"{E_LINK} Укажите правильный токен бота: <code>.sbt 123456:ABC...</code>",
            parse_mode="html",
        )
        return

    await event.message.edit(f"{E_WAIT} <b>Проверяю токен бота...</b>", parse_mode="html")
    ok, username, error, bot_id = await validate_bot_token(token)
    if not ok or not username:
        await event.message.edit(
            f"❌ <b>Токен бота недействителен или бот не запускается.</b>\n\n"
            f"<code>{html((error or 'unknown error')[:500])}</code>",
            parse_mode="html",
        )
        return

    settings.set_val("manager_bot_token", token)
    settings.set_val("manager_bot_username", username)
    settings.set_val("manager_bot_id", bot_id)
    settings.set_val("manager_bot_configured_username", username)
    settings.set_val("manager_bot_feedback_username", username)
    await start_manager_bot(token)
    await event.message.edit(bot_linked_text(username), parse_mode="html")


async def cmd_sbc(event) -> None:
    await event.message.edit(f"{E_CREATE} <b>Создаю менеджер-бота через BotFather...</b>", parse_mode="html")
    try:
        username, token = await create_bot_with_botfather()
    except Exception as e:
        await event.message.edit(
            f"❌ <b>Не удалось создать бота.</b>\n\n<code>{html(str(e)[:800])}</code>",
            parse_mode="html",
        )
        return

    settings.set_val("manager_bot_token", token)
    settings.set_val("manager_bot_username", username)
    settings.set_val("manager_bot_configured_username", username)
    ok, _username, _error, bot_id = await validate_bot_token(token)
    if ok:
        settings.set_val("manager_bot_id", bot_id)
    await start_manager_bot(token)
    await event.message.edit(bot_created_text(username), parse_mode="html")


async def create_bot_with_botfather() -> tuple[str, str]:
    botfather = await user_client.get_entity("BotFather")
    token = None
    username = None

    async with user_client.conversation(botfather, timeout=120, exclusive=False) as conv:
        await conv.send_message("/cancel")
        try:
            await conv.get_response(timeout=5)
        except Exception:
            pass

        await conv.send_message("/newbot")
        await conv.get_response()
        await conv.send_message(BOT_TITLE)
        await conv.get_response()

        for _ in range(8):
            candidate = _random_bot_username()
            await conv.send_message(candidate)
            response = await conv.get_response()
            text = response.raw_text or ""
            parsed = _parse_bot_token(text)
            if parsed:
                token = parsed
                username = f"@{candidate}"
                break

        if not token or not username:
            raise RuntimeError("BotFather не выдал токен. Возможно, лимит ботов исчерпан или все username заняты.")

        description = build_bot_description(await get_owner_label())
        await _botfather_set_inline(conv, username)
        await _botfather_set_inline_feedback(conv, username)
        await _botfather_set_description(conv, username, description)
        await _botfather_set_about(conv, username, description)
        await _botfather_set_userpic(conv, botfather, username)

    return username, token


async def ensure_manager_bot_configured() -> None:
    username = settings.get("manager_bot_username")
    if not username:
        return
    if (
        settings.get("manager_bot_configured_username") == username
        and settings.get("manager_bot_feedback_username") == username
    ):
        return
    await asyncio.sleep(3)
    try:
        await configure_botfather_bot(username)
        settings.set_val("manager_bot_configured_username", username)
        settings.set_val("manager_bot_feedback_username", username)
    except Exception as e:
        print(f"[manager_bot configure] {e}")


async def configure_botfather_bot(username: str) -> None:
    botfather = await user_client.get_entity("BotFather")
    description = build_bot_description(await get_owner_label())
    async with user_client.conversation(botfather, timeout=120, exclusive=False) as conv:
        await conv.send_message("/cancel")
        try:
            await conv.get_response(timeout=5)
        except Exception:
            pass
        await _botfather_set_inline(conv, username)
        await _botfather_set_inline_feedback(conv, username)
        await _botfather_set_description(conv, username, description)
        await _botfather_set_about(conv, username, description)
        await _botfather_set_userpic(conv, botfather, username)


async def _botfather_set_inline(conv, username: str) -> None:
    await conv.send_message("/setinline")
    await conv.get_response()
    await conv.send_message(username)
    await conv.get_response()
    await conv.send_message("Управление Binary Userbot")
    await conv.get_response()


async def _botfather_set_inline_feedback(conv, username: str) -> None:
    await conv.send_message("/setinlinefeedback")
    await conv.get_response()
    await conv.send_message(username)
    await conv.get_response()
    await conv.send_message("100%")
    await conv.get_response()


async def _botfather_set_description(conv, username: str, description: str) -> None:
    await conv.send_message("/setdescription")
    await conv.get_response()
    await conv.send_message(username)
    await conv.get_response()
    await conv.send_message(description)
    await conv.get_response()


async def _botfather_set_about(conv, username: str, description: str) -> None:
    await conv.send_message("/setabouttext")
    await conv.get_response()
    await conv.send_message(username)
    await conv.get_response()
    await conv.send_message(description)
    await conv.get_response()


async def _botfather_set_userpic(conv, botfather, username: str) -> None:
    if not AVATAR_PATH.exists():
        return
    await conv.send_message("/setuserpic")
    await conv.get_response()
    await conv.send_message(username)
    await conv.get_response()
    await user_client.send_file(botfather, AVATAR_PATH)
    await conv.get_response()


def _extract_update_changelog(text: str, version_match: re.Match | None = None) -> str | None:
    if not text:
        return None
    version_match = version_match or re.search(r"v\s*\d+(?:\.\d+)+", text, flags=re.IGNORECASE)
    if not version_match:
        return None
    download_match = re.search(
        r"(?im)^\s*(?:\[)?Скачать актуальную версию(?:\])?.*$",
        text,
    )
    start = version_match.end()
    end = download_match.start() if download_match and download_match.start() > start else len(text)
    changelog = text[start:end].strip("\r\n")
    return changelog if changelog.strip() else None


async def get_latest_update_info() -> tuple[str | None, str | None]:
    try:
        await user_client(JoinChannelRequest(UPDATE_CHANNEL))
    except UserAlreadyParticipantError:
        pass
    except Exception:
        pass

    entity = None
    for ref in (UPDATE_CHANNEL_ID, UPDATE_CHANNEL):
        try:
            entity = await user_client.get_entity(ref)
            break
        except Exception:
            continue
    if not entity:
        return None, None

    msg = await user_client.get_messages(entity, ids=UPDATE_MESSAGE_ID)
    text = getattr(msg, "raw_text", None) or getattr(msg, "message", "") or ""
    version_match = re.search(r"v\s*\d+(?:\.\d+)+", text, flags=re.IGNORECASE)
    version = version_match.group(0).replace(" ", "") if version_match else None
    changelog = _extract_update_changelog(text, version_match)
    return version, changelog


async def get_latest_version() -> str | None:
    version, _changelog = await get_latest_update_info()
    return version


async def validate_openrouter_token(token: str) -> tuple[bool, str | None]:
    if not token:
        return False, "Пустой токен."
    try:
        headers = {"Authorization": f"Bearer {token}"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://openrouter.ai/api/v1/key",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 200:
                    return True, None
                body = await response.text()
                return False, f"OpenRouter ответил HTTP {response.status}: {body[:120]}"
    except Exception as e:
        return False, str(e)


async def validate_openrouter_model(model: str) -> tuple[bool, str | None]:
    model = (model or "").strip()
    if not model:
        return False, "Пустое название модели."
    try:
        headers = {"Authorization": f"Bearer {current_or_token()}"} if current_or_token() else {}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    return False, f"OpenRouter ответил HTTP {response.status}: {body[:120]}"
                data = await response.json(content_type=None)
        models = {item.get("id") for item in data.get("data", []) if isinstance(item, dict)}
        if model in models:
            return True, None
        return False, "Такой модели нет в списке OpenRouter."
    except Exception as e:
        return False, str(e)


def _refresh_mode_histories(store: dict, prompt: str) -> None:
    for chat_id, history in list(store.items()):
        if isinstance(history, list) and history:
            history[0] = {"role": "system", "content": prompt}
        else:
            store[chat_id] = [{"role": "system", "content": prompt}]


async def _handle_mode_prompt_input(chat_id: int, kind: str, prompt_message_id: int, value: str) -> None:
    value = (value or "").strip()
    if len(value) < 10:
        await manager_client.edit_message(
            chat_id,
            prompt_message_id,
            input_prompt_text(kind, "Промпт слишком короткий. Напишите хотя бы 10 символов."),
            parse_mode="html",
            buttons=mode_input_buttons(),
            link_preview=False,
        )
        return

    if kind == "mode_ebalaj_prompt":
        settings.set_val("ebalaj_system_prompt", value)
        _refresh_mode_histories(state.ebalaj_history, value)
    else:
        settings.set_val("troll_system_prompt", value)
        _refresh_mode_histories(state.troll_history, value)

    pending_inputs.pop(MY_ID, None)
    await manager_client.edit_message(
        chat_id,
        prompt_message_id,
        modes_menu_text(),
        parse_mode="html",
        buttons=modes_buttons(),
        link_preview=False,
    )


async def _handle_openrouter_input(chat_id: int, kind: str, prompt_message_id: int, value: str) -> None:
    if kind == "or_token":
        ok, error = await validate_openrouter_token(value)
        if not ok:
            await manager_client.edit_message(
                chat_id,
                prompt_message_id,
                input_prompt_text(kind, f"Токен недействителен: {error}"),
                parse_mode="html",
                buttons=back_buttons(),
                link_preview=False,
            )
            return
        settings.set_val("or_token", value)
    else:
        ok, error = await validate_openrouter_model(value)
        if not ok:
            await manager_client.edit_message(
                chat_id,
                prompt_message_id,
                input_prompt_text(kind, f"Модель недействительна: {error}"),
                parse_mode="html",
                buttons=back_buttons(),
                link_preview=False,
            )
            return
        settings.set_val("or_model", value)

    pending_inputs.pop(MY_ID, None)
    await manager_client.edit_message(
        chat_id,
        prompt_message_id,
        openrouter_menu_text(),
        parse_mode="html",
        buttons=openrouter_buttons(),
        link_preview=False,
    )


async def _handle_terminal_input(chat_id: int, prompt_message_id: int, command: str) -> None:
    pending_inputs.pop(MY_ID, None)
    history = list(settings.get("manager_terminal_history", []) or [])
    history.append(command)
    settings.set_val("manager_terminal_history", history[-5:])

    await manager_client.edit_message(
        chat_id,
        prompt_message_id,
        terminal_wait_text(),
        parse_mode="html",
        buttons=terminal_wait_buttons(),
        link_preview=False,
    )
    task = asyncio.create_task(_run_terminal_command(chat_id, prompt_message_id, command))
    terminal_jobs[MY_ID] = {"task": task, "proc": None, "message_id": prompt_message_id}


async def _run_terminal_command(chat_id: int, message_id: int, command: str) -> None:
    try:
        proc = await spawn_terminal_process(command, cwd=BASE_DIR)
        if MY_ID in terminal_jobs:
            terminal_jobs[MY_ID]["proc"] = proc
        stdout, stderr = await proc.communicate()
        output = (
            decode_terminal_output(stdout)
            + decode_terminal_output(stderr)
        ).strip()
        await manager_client.edit_message(
            chat_id,
            message_id,
            terminal_done_text(command, output),
            parse_mode="html",
            buttons=terminal_done_buttons(),
            link_preview=False,
        )
    except asyncio.CancelledError:
        raise
    except Exception as e:
        await manager_client.edit_message(
            chat_id,
            message_id,
            terminal_done_text(command, f"Ошибка: {e}"),
            parse_mode="html",
            buttons=terminal_done_buttons(),
            link_preview=False,
        )
    finally:
        terminal_jobs.pop(MY_ID, None)


async def _cancel_terminal_job() -> None:
    job = terminal_jobs.pop(MY_ID, None)
    if not job:
        return
    proc = job.get("proc")
    task = job.get("task")
    if proc and proc.returncode is None:
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    if task and not task.done():
        task.cancel()


def _serialize_inline_message_id(inline_msg_id) -> dict | None:
    if isinstance(inline_msg_id, types.InputBotInlineMessageID64):
        return {
            "kind": "64",
            "dc_id": inline_msg_id.dc_id,
            "owner_id": inline_msg_id.owner_id,
            "id": inline_msg_id.id,
            "access_hash": inline_msg_id.access_hash,
        }
    if isinstance(inline_msg_id, types.InputBotInlineMessageID):
        return {
            "kind": "32",
            "dc_id": inline_msg_id.dc_id,
            "id": inline_msg_id.id,
            "access_hash": inline_msg_id.access_hash,
        }
    return None


def _deserialize_inline_message_id(data: dict | None):
    if not isinstance(data, dict):
        return None
    try:
        if data.get("kind") == "64":
            return types.InputBotInlineMessageID64(
                dc_id=int(data["dc_id"]),
                owner_id=int(data["owner_id"]),
                id=int(data["id"]),
                access_hash=int(data["access_hash"]),
            )
        return types.InputBotInlineMessageID(
            dc_id=int(data["dc_id"]),
            id=int(data["id"]),
            access_hash=int(data["access_hash"]),
        )
    except Exception:
        return None


def _post_restart_notice_payload(kind: str, *, event=None, chat_id=None, message_id=None) -> dict | None:
    inline_msg_id = _inline_message_id_from_event(event) if event is not None else None
    if inline_msg_id is not None:
        payload = {
            "target": "manager_inline",
            "kind": kind,
            "inline_message_id": _serialize_inline_message_id(inline_msg_id),
        }
        event_chat_id = getattr(event, "chat_id", None)
        if event_chat_id is not None:
            payload["chat_id"] = int(event_chat_id)
        return payload

    if event is not None:
        chat_id = getattr(event, "chat_id", chat_id)
        message_id = getattr(event, "message_id", message_id)

    if chat_id is None or message_id is None:
        return None

    return {
        "target": "manager_message",
        "kind": kind,
        "chat_id": int(chat_id),
        "message_id": int(message_id),
    }


def post_restart_notice_for_user_message(kind: str, chat_id: int, message_id: int) -> dict:
    return {
        "target": "user_message",
        "kind": kind,
        "chat_id": int(chat_id),
        "message_id": int(message_id),
    }


def remember_post_restart_notice(payload: dict | None) -> None:
    if payload:
        settings.set_val("pending_post_restart_notice", payload)


async def flush_pending_post_restart_notice() -> None:
    notice = settings.get("pending_post_restart_notice")
    if not isinstance(notice, dict):
        return

    text = updated_success_text() if notice.get("kind") == "update" else restarted_success_text()
    target = notice.get("target")

    try:
        if target == "user_message":
            await user_client.edit_message(
                int(notice["chat_id"]),
                int(notice["message_id"]),
                text,
                parse_mode="html",
                link_preview=False,
            )
        elif target == "manager_message":
            if not manager_client:
                return
            await manager_client.edit_message(
                int(notice["chat_id"]),
                int(notice["message_id"]),
                text,
                parse_mode="html",
                buttons=None,
                link_preview=False,
            )
        elif target == "manager_inline":
            if not manager_client:
                return
            inline_msg_id = _deserialize_inline_message_id(notice.get("inline_message_id"))
            if inline_msg_id is None:
                return
            await _raw_edit_inline_message(inline_msg_id, text, None, link_preview=False)
        else:
            return
    except Exception as e:
        print(f"[manager_bot post-restart notice] {e}")
        fallback_chat_id = notice.get("chat_id")
        if fallback_chat_id and manager_client and isinstance(target, str) and target.startswith("manager"):
            try:
                await manager_client.send_message(int(fallback_chat_id), text, parse_mode="html", link_preview=False)
            except Exception as inner:
                print(f"[manager_bot post-restart fallback] {inner}")
        elif fallback_chat_id and target == "user_message":
            try:
                await user_client.send_message(int(fallback_chat_id), text, parse_mode="html", link_preview=False)
            except Exception as inner:
                print(f"[userbot post-restart fallback] {inner}")
    finally:
        settings.set_val("pending_post_restart_notice", None)


def schedule_restart(delay: float = 1.0, notice: dict | None = None) -> None:
    remember_post_restart_notice(notice)
    asyncio.create_task(_restart_later(delay))


async def _restart_later(delay: float) -> None:
    await asyncio.sleep(delay)
    import sys
    import os
    try:
        from bot_client import client
        if client:
            client.session.close()
    except Exception:
        pass
    os.execv(sys.executable, [sys.executable] + sys.argv)


async def _handle_check_updates(event) -> None:
    latest, changelog = await get_latest_update_info()
    if not latest:
        await event.edit(
            "❌ <b>Не удалось прочитать сообщение с актуальной версией.</b>",
            parse_mode="html",
            buttons=back_buttons(),
        )
        return
    if _is_newer(latest):
        await _safe_event_edit(event, update_available_text(latest, changelog), buttons=update_buttons(), link_preview=False)
    else:
        await _safe_event_edit(event, up_to_date_text(), buttons=back_buttons(), link_preview=False)


def _dialog_link(entity, peer_id: int | None) -> str | None:
    username = getattr(entity, "username", None)
    if username:
        return f"https://t.me/{username}"
    if isinstance(entity, types.User):
        user_id = getattr(entity, "id", None)
        return f"tg://user?id={user_id}" if user_id else None
    if peer_id is not None and str(peer_id).startswith("-100"):
        internal_id = str(abs(peer_id))[3:]
        return f"https://t.me/c/{internal_id}"
    return None


async def _build_chats_report() -> dict:
    chats = []
    async for dialog in user_client.iter_dialogs():
        entity = dialog.entity
        try:
            peer_id = get_peer_id(entity)
        except Exception:
            peer_id = getattr(entity, "id", None)
        name = (
            getattr(dialog, "name", None)
            or getattr(entity, "title", None)
            or " ".join(filter(None, [getattr(entity, "first_name", None), getattr(entity, "last_name", None)]))
            or getattr(entity, "username", None)
            or str(peer_id)
        )
        chats.append({
            "name": name,
            "id": peer_id,
            "link": _dialog_link(entity, peer_id),
        })

    chats.sort(key=lambda item: (str(item.get("name") or "").lower(), str(item.get("id") or "")))
    return {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "count": len(chats),
        "chats": chats,
    }


async def _handle_export_chats(event) -> None:
    await event.edit(
        f"<blockquote><b>{E_WAIT} Формирую JSON-отчёт по чатам...</b></blockquote>",
        parse_mode="html",
        buttons=None,
        link_preview=False,
    )
    try:
        report = await _build_chats_report()
        payload = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
        buf = io.BytesIO(payload)
        buf.name = "binary_chats_report.json"
        await manager_client.send_file(
            event.chat_id,
            buf,
            caption=f"{E_CMD_OK} <b>Чаты выгружены:</b> <code>{report['count']}</code>",
            parse_mode="html",
        )
        await event.edit(
            f"<blockquote><b>{E_CMD_OK} JSON-отчёт по чатам сформирован.</b></blockquote>",
            parse_mode="html",
            buttons=back_buttons(),
            link_preview=False,
        )
    except Exception as e:
        await event.edit(
            f"❌ <b>Не удалось выгрузить чаты.</b>\n\n<code>{html(str(e)[:800])}</code>",
            parse_mode="html",
            buttons=back_buttons(),
        )


async def _handle_install_update(event) -> None:
    await event.edit(installing_update_text(), parse_mode="html", buttons=None, link_preview=False)
    try:
        await asyncio.to_thread(_install_update_sync)
    except Exception as e:
        await event.edit(
            f"❌ <b>Не удалось установить обновление.</b>\n\n<code>{html(str(e)[:1200])}</code>",
            parse_mode="html",
            buttons=back_buttons(),
        )
        return
    schedule_restart(1.0, notice=_post_restart_notice_payload("update", event=event))


def _preserved_update_paths() -> list[Path]:
    file_patterns = (
        "config.py",
        "settings.json",
        "notes.json",
        "*.session",
        "*.session-journal",
        "*.session-wal",
        "*.session-shm",
    )
    directory_names = ("modules",)
    paths: list[Path] = []
    seen: set[str] = set()
    for pattern in file_patterns:
        for path in BASE_DIR.glob(pattern):
            if not path.is_file():
                continue
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
    for dirname in directory_names:
        path = BASE_DIR / dirname
        if not path.exists():
            continue
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def _copy_preserved_file(src: Path, dest: Path) -> None:
    try:
        if not src.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    except FileNotFoundError:
        # SQLite sidecar files like .session-journal/.session-wal can vanish
        # between globbing and copying while the client is still running.
        return


def _extract_config_version_line(config_path: Path) -> str | None:
    try:
        text = config_path.read_text(encoding="utf-8")
    except Exception:
        return None
    match = CONFIG_VERSION_RE.search(text)
    return match.group(0) if match else None


def _apply_config_version_line(config_path: Path, version_line: str | None) -> None:
    if not version_line:
        return
    try:
        text = config_path.read_text(encoding="utf-8")
    except Exception:
        return

    if CONFIG_VERSION_RE.search(text):
        new_text = CONFIG_VERSION_RE.sub(version_line, text, count=1)
    else:
        suffix = "" if not text or text.endswith("\n") else "\n"
        new_text = f"{text}{suffix}{version_line}\n"

    if new_text == text:
        return
    config_path.write_text(new_text, encoding="utf-8")


def _backup_preserved_files() -> Path:
    backup_dir = Path(tempfile.mkdtemp(prefix="binary_update_backup_"))
    for src in _preserved_update_paths():
        if not src.exists():
            continue
        rel = src.relative_to(BASE_DIR)
        dest = backup_dir / rel
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            _copy_preserved_file(src, dest)
    return backup_dir


def _restore_preserved_files(backup_dir: Path) -> None:
    for src in backup_dir.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(backup_dir)
        
        # Don't manually copy files from modules directory here, handled below
        if len(rel.parts) > 0 and rel.parts[0] == "modules":
            continue
            
        dest = BASE_DIR / rel
        _copy_preserved_file(src, dest)
        
    # Merge modules folder without deleting existing ones
    for dirname in ("modules",):
        src_dir = backup_dir / dirname
        dest_dir = BASE_DIR / dirname
        if not src_dir.exists():
            continue
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
        
    ensure_runtime_permissions()


def _install_update_sync() -> None:
    backup_dir = _backup_preserved_files()
    updated_version_line: str | None = None
    try:
        if _try_git_pull():
            updated_version_line = _extract_config_version_line(BASE_DIR / "config.py")
        else:
            temp_dir = Path(tempfile.mkdtemp(prefix="binary_update_"))
            try:
                zip_path = temp_dir / "source.zip"
                urllib.request.urlretrieve(GITHUB_ZIP_URL, zip_path)
                with zipfile.ZipFile(zip_path, "r") as archive:
                    archive.extractall(temp_dir)

                candidates = list(temp_dir.glob("BinaryUserbot-*/BinaryUserbot")) + list(temp_dir.glob("BinaryUserbot-*"))
                source_dir = next((p for p in candidates if (p / "main.py").exists()), None)
                if not source_dir:
                    raise RuntimeError("В архиве GitHub не найдена папка BinaryUserbot с main.py.")

                updated_version_line = _extract_config_version_line(source_dir / "config.py")
                for src in source_dir.rglob("*"):
                    rel = src.relative_to(source_dir)
                    if _skip_update_path(rel):
                        continue
                    dest = BASE_DIR / rel
                    if src.is_dir():
                        dest.mkdir(parents=True, exist_ok=True)
                    else:
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dest)
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
    finally:
        try:
            _restore_preserved_files(backup_dir)
            _apply_config_version_line(BASE_DIR / "config.py", updated_version_line)
            ensure_runtime_permissions()
        finally:
            shutil.rmtree(backup_dir, ignore_errors=True)


def _try_git_pull() -> bool:
    try:
        root = subprocess.check_output(
            ["git", "-C", str(BASE_DIR), "rev-parse", "--show-toplevel"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        remotes = subprocess.check_output(
            ["git", "-C", str(BASE_DIR), "remote", "-v"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        if GITHUB_REPO_HINT.lower() not in remotes.lower():
            return False
        if Path(root).resolve() != BASE_DIR.resolve() and not (Path(root) / "BinaryUserbot").exists():
            return False
        branch = subprocess.check_output(
            ["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if not branch or branch == "HEAD":
            return False
        subprocess.check_call(["git", "-C", root, "fetch", "--all", "--prune"])
        try:
            target = subprocess.check_output(
                ["git", "-C", root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            target = f"origin/{branch}"
        subprocess.check_call(["git", "-C", root, "reset", "--hard", target])
        return True
    except Exception:
        return False


def _skip_update_path(rel: Path) -> bool:
    parts = set(rel.parts)
    name = rel.name
    if parts & {"modules", "builtin_modules", "__pycache__", ".git", ".venv", "venv"}:
        return True
    if name in {"config.py", "settings.json", "notes.json"}:
        return True
    if name.endswith((".session", ".session-journal", ".session-wal", ".session-shm", ".pyc")):
        return True
    if name.startswith("manager_bot_") and (name.endswith(".session") or ".session-" in name):
        return True
    return False


async def handle_pending_reply(chat_id: int, reply_to_msg_id: int | None, value: str, source_message=None) -> bool:
    pending = pending_inputs.get(MY_ID)
    if not pending:
        return False
    if int(chat_id) != int(pending["chat_id"]):
        return False
    if int(reply_to_msg_id or 0) != int(pending["message_id"]):
        return False

    source_id = getattr(source_message, "id", None)
    seen_ids = pending.setdefault("seen_source_ids", set())
    if source_id is not None:
        if source_id in seen_ids:
            return True
        seen_ids.add(source_id)

    value = (value or "").strip()
    if not value:
        return True

    ok, _missing = await ensure_required_channels()
    if not ok:
        await manager_client.edit_message(
            pending["chat_id"],
            pending["message_id"],
            subscription_required_text(),
            parse_mode="html",
            link_preview=False,
        )
        return True

    if source_message is not None:
        try:
            await source_message.delete()
        except Exception:
            pass

    if pending["kind"] in {"or_token", "or_model"}:
        await _handle_openrouter_input(pending["chat_id"], pending["kind"], pending["message_id"], value)
    elif pending["kind"] in {"mode_ebalaj_prompt", "mode_troll_prompt"}:
        await _handle_mode_prompt_input(pending["chat_id"], pending["kind"], pending["message_id"], value)
    elif pending["kind"] == "terminal":
        await _handle_terminal_input(pending["chat_id"], pending["message_id"], value)
    return True


async def _handle_pending_message(event) -> None:
    if int(event.sender_id or 0) != int(MY_ID):
        return
    await handle_pending_reply(
        event.chat_id,
        getattr(event.message, "reply_to_msg_id", None),
        event.raw_text or "",
        source_message=event.message,
    )


async def _handle_callback(event) -> None:
    if not await _guard_event(event):
        return

    data = (event.data or b"").decode("utf-8", errors="ignore")
    try:
        await event.answer()
    except Exception:
        pass

    import loader
    if getattr(loader, "inline_manager", None) and data in loader.inline_manager.forms:
        cb_data = loader.inline_manager.forms[data]
        action = cb_data["action"]
        args = cb_data["args"]
        kwargs = cb_data["kwargs"]

        if cb_data.get("input_prompt"):
            prompt = cb_data["input_prompt"]
            action = cb_data["handler"]
            try:
                await event.answer("Ответьте боту в личных сообщениях!", alert=True)
            except Exception:
                pass
            try:
                async with manager_client.conversation(event.sender_id, timeout=60) as conv:
                    await conv.send_message(prompt)
                    msg = await conv.get_response()
                    input_text = msg.text
                args = (input_text,) + args
            except Exception as e:
                print(f"Conversation error: {e}")
                return

        class CallMock:
            def __init__(self, e):
                self.event = e
                self.data = e.data
                self.sender_id = e.sender_id
            async def answer(self, *a, **kw):
                await self.event.answer(*a, **kw)
            async def edit(self, *a, **kw):
                if "reply_markup" in kw:
                    from telethon import Button
                    import uuid
                    reply_markup = kw.pop("reply_markup")
                    telethon_buttons = []
                    for row in reply_markup:
                        btn_row = []
                        for btn in row:
                            cb_id = str(uuid.uuid4())[:16]
                            loader.inline_manager.forms[cb_id] = {
                                "action": btn.get("callback"),
                                "input_prompt": btn.get("input"),
                                "handler": btn.get("handler"),
                                "args": btn.get("args", ()),
                                "kwargs": btn.get("kwargs", {})
                            }
                            btn_row.append(Button.inline(btn["text"], cb_id.encode('utf-8')))
                        telethon_buttons.append(btn_row)
                    kw["buttons"] = telethon_buttons
                kw["parse_mode"] = "html"
                await self.event.edit(*a, **kw)
            async def delete(self):
                await self.event.delete()
        try:
            await action(CallMock(event), *args, **kwargs)
        except Exception as e:
            print(f"Inline callback error: {e}")
        return

    if data == "back_main":
        await _cancel_terminal_job()
        await _show_main(event)
    elif data == "back_modes":
        await _show_modes(event)
    elif data == "check_updates":
        await _handle_check_updates(event)
    elif data == "openrouter":
        pending_inputs.pop(MY_ID, None)
        await _safe_event_edit(event, openrouter_menu_text(), buttons=openrouter_buttons(), link_preview=False)
    elif data == "or_change_token":
        pending_inputs[MY_ID] = {"kind": "or_token", "chat_id": event.chat_id, "message_id": event.message_id, "seen_source_ids": set()}
        await _safe_event_edit(event, input_prompt_text("or_token"), buttons=back_buttons(), link_preview=False)
    elif data == "or_change_model":
        pending_inputs[MY_ID] = {"kind": "or_model", "chat_id": event.chat_id, "message_id": event.message_id, "seen_source_ids": set()}
        await _safe_event_edit(event, input_prompt_text("or_model"), buttons=back_buttons(), link_preview=False)
    elif data == "modes":
        await _show_modes(event)
    elif data == "export_chats":
        await _handle_export_chats(event)
    elif data == "mode_ebalaj_prompt":
        pending_inputs[MY_ID] = {"kind": "mode_ebalaj_prompt", "chat_id": event.chat_id, "message_id": event.message_id, "seen_source_ids": set()}
        await _safe_event_edit(event, input_prompt_text("mode_ebalaj_prompt"), buttons=mode_input_buttons(), link_preview=False)
    elif data == "mode_troll_prompt":
        pending_inputs[MY_ID] = {"kind": "mode_troll_prompt", "chat_id": event.chat_id, "message_id": event.message_id, "seen_source_ids": set()}
        await _safe_event_edit(event, input_prompt_text("mode_troll_prompt"), buttons=mode_input_buttons(), link_preview=False)
    elif data == "antivirus_toggle":
        settings.set_val("antivirus_enabled", not bool(settings.get("antivirus_enabled", False)))
        await _safe_event_edit(event, modes_menu_text(), buttons=modes_buttons(), link_preview=False)
    elif data == "restart_ask":
        await _safe_event_edit(event, restart_question_text(), buttons=restart_confirm_buttons(), link_preview=False)
    elif data == "restart_yes":
        await _safe_event_edit(event, restarting_text(), buttons=None, link_preview=False)
        schedule_restart(1.0, notice=_post_restart_notice_payload("restart", event=event))
    elif data == "terminal":
        pending_inputs[MY_ID] = {"kind": "terminal", "chat_id": event.chat_id, "message_id": event.message_id, "seen_source_ids": set()}
        await _safe_event_edit(event, terminal_prompt_text(), buttons=back_buttons(), link_preview=False)
    elif data == "terminal_cancel":
        await _cancel_terminal_job()
        await _show_main(event)
    elif data == "install_update":
        await _handle_install_update(event)


async def _handle_inline(event) -> None:
    if int(event.sender_id or 0) != int(MY_ID):
        await event.answer([], cache_time=0)
        return
    builder = event.builder
    query = (event.text or "").strip().lower()
    results = []

    if query.startswith("form:"):
        form_id = query.split(":")[1]
        if form_id in INLINE_FORMS:
            form = INLINE_FORMS[form_id]
            results.append(
                await builder.article(
                    title="Form",
                    text=form["text"],
                    parse_mode="html",
                    buttons=form["buttons"]
                )
            )

    if not query or "menu".startswith(query) or "меню".startswith(query) or "panel".startswith(query):
        results.append(
            await _inline_text_article(
                builder,
                title="Binary Userbot",
                description="Панель управления юзерботом",
                text=main_menu_text(),
                buttons=main_buttons_inline(),
                prefix="menu",
            )
        )

    if not query or "help".startswith(query) or "хелп".startswith(query) or "помощь".startswith(query):
        from help_faq import get_help_text

        results.append(
            await _inline_text_article(
                builder,
                title="Help Binary Userbot",
                description="Список команд и ссылка на сайт",
                text=get_help_text(force_premium=True),
                buttons=help_site_buttons(),
                prefix="help",
            )
        )

    if not results:
        from help_faq import get_help_text

        results = [
            await _inline_text_article(
                builder,
                title="Help Binary Userbot",
                description="Список команд и ссылка на сайт",
                text=get_help_text(force_premium=True),
                buttons=help_site_buttons(),
                prefix="help",
            )
        ]

    try:
        await event.answer(results, cache_time=0, gallery=False)
    except Exception as e:
        print(f"[manager_bot inline answer] {e}")
        fallback = [
            await builder.article(
                title="Binary Userbot",
                description="Панель управления юзерботом",
                text="Binary Userbot",
                parse_mode="html",
                buttons=main_buttons_inline(),
                id=f"menu-fallback-{random.getrandbits(64):016x}",
            )
        ]
        await event.answer(fallback, cache_time=0, gallery=False)


async def _handle_inline_send(update) -> None:
    if int(getattr(update, "user_id", 0) or 0) != int(MY_ID):
        return
    inline_msg_id = getattr(update, "msg_id", None)
    result_id = str(getattr(update, "id", "") or "")
    if not inline_msg_id:
        return

    if result_id.startswith("menu-"):
        text = main_menu_text()
        buttons = main_buttons()
    elif result_id.startswith("help-"):
        from help_faq import get_help_text

        text = get_help_text(force_premium=True)
        buttons = help_site_buttons()
    else:
        return

    try:
        parsed_text, entities = await manager_client._parse_message_text(text, "html")
        await manager_client(
            functions.messages.EditInlineBotMessageRequest(
                id=inline_msg_id,
                message=parsed_text,
                no_webpage=True,
                entities=entities,
                reply_markup=manager_client.build_reply_markup(buttons),
            )
        )
    except Exception as e:
        print(f"[manager_bot inline send edit] {e}")


def _register_handlers(bot: TelegramClient) -> None:
    bot.add_event_handler(_handle_start, events.NewMessage(pattern=r"^/start$"))
    bot.add_event_handler(_handle_pending_message, events.NewMessage(incoming=True))
    bot.add_event_handler(_handle_callback, events.CallbackQuery)
    bot.add_event_handler(_handle_inline, events.InlineQuery)
    bot.add_event_handler(_handle_inline_send, events.Raw(types.UpdateBotInlineSend))
