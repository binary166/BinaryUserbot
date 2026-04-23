import asyncio
import io
import os
from datetime import datetime

from telethon import events
from telethon.tl.types import User

import state
from bot_client import client
from config import (
    LOADING, BOT_NAME, BOT_VERSION, PROXY_TEXT,
    CHECK_PING, CHECK_PONG,
)
import settings
from utils import html, get_username, is_private_chat, resolve_sender, send_me, extract_formatted_body
from premium_emoji import pe, by_line
from ai import or_request
from weather import get_weather
from prices import get_prices, calc_crypto
from calc import safe_calc
from downloader import download_youtube, download_tiktok
from notes import load_notes, save_notes
from news import get_last_news
from user_info import get_user_info, cmd_me, cmd_stat
from scam import check_scam_base, cmd_scam, cmd_lol
from autochat import handle_ac
from ebalaj import handle_ebalaj, handle_troll
from prank import run_prank
from animations import run_animation, CAT_FRAMES, ROCKET_FRAMES, POKEMON_FRAMES
from help_faq import get_help_text, cmd_setting, FAQ_DATA


@client.on(events.NewMessage)
async def on_new_message(event):
    msg  = event.message
    priv = is_private_chat(event)

    if not msg.out and priv and msg.text:
        if msg.text.strip() == CHECK_PING:
            await asyncio.sleep(0.3)
            await client.send_message(
                msg.chat_id,
                f"{CHECK_PONG}{BOT_VERSION}\n{pe('alien')} {BOT_NAME}"
            )
            return
        if msg.text.startswith(CHECK_PONG):
            uid = msg.sender_id
            if uid and uid in state.check_events:
                state.check_results[uid] = msg.text
                state.check_events[uid].set()
            return

    if not msg.out:
        sid = msg.sender_id
        if sid and sid in state.muted_users.get(msg.chat_id, set()):
            try:
                await msg.delete()
            except Exception as e:
                print(f"[MUTE] {e}")
            return

        return

    if not msg.out and priv and msg.chat_id in state.ebalaj_active:
        await handle_ebalaj(event)
        return
    if not msg.out and priv and msg.chat_id in state.troll_active:
        await handle_troll(event)
        return
    if not msg.out and priv and state.ac_active.get(msg.chat_id):
        await handle_ac(event)
        return

    if priv:
        sender = await resolve_sender(msg)
        state.message_store[msg.id] = {
            "text": msg.text or "",
            "sender": sender,
            "chat_id": msg.chat_id,
        }
        if not msg.out and msg.media and getattr(msg.media, "ttl_seconds", None) is not None:
            await send_me(
                f"⚠️ <b>Одноразовый медиафайл</b>\n\n"
                f"👤 <b>От:</b> {html(get_username(sender))}\n"
                f"🕐 {datetime.now().strftime('%H:%M  %d.%m.%Y')}",
                file=msg.media
            )
        if not msg.out and isinstance(sender, User) and sender.id not in state.known_users:
            state.known_users.add(sender.id)
            uname_raw = getattr(sender, "username", None)
            if uname_raw and await check_scam_base(uname_raw):
                await send_me(
                    f"🛑 <b>Binary Userbot обнаружил юзера</b> @{html(uname_raw)} <b>в скам базе.</b>"
                )

    if msg.out and msg.text and state.eng_mode_active and not msg.text.strip().lower().startswith("."):
        try:
            translated = await or_request(
                "You are a translator. Translate to English. Return ONLY the translation.",
                msg.text.strip(), max_tokens=500
            )
            await event.message.edit(translated)
        except Exception as e:
            print(f"[ENG] {e}")
        return

    if not (msg.out and msg.text):
        return

    raw = msg.text.strip()
    cmd = raw.lower()

    async def _send_video(filepath, title, quality_label):
        size_mb = os.path.getsize(filepath) / 1024 / 1024
        await event.message.edit(
            f"📤 <i>Загружаю ({size_mb:.1f} МБ)...</i>", parse_mode="html"
        )
        try:
            buf = io.BytesIO(open(filepath, "rb").read())
            buf.name = os.path.basename(filepath)
            await client.send_file(
                event.chat_id, buf,
                caption=(
                    f"🎬 <b>{html(title)}</b>\n\n"
                    f"📥 {quality_label} · {size_mb:.1f} МБ\n\n" + by_line()
                ),
                parse_mode="html", supports_streaming=True
            )
            await event.message.delete()
        except Exception as e:
            await event.message.edit(
                f"❌ <b>Ошибка TG:</b>\n<code>{html(str(e)[:200])}</code>",
                parse_mode="html"
            )
        finally:
            try:
                os.remove(filepath)
                os.rmdir(os.path.dirname(filepath))
            except Exception:
                pass

    if cmd == ".help":
        await event.message.edit(get_help_text(), parse_mode="html")

    elif cmd == ".цена":
        await event.message.edit(LOADING, parse_mode="html")
        await event.message.edit(await get_prices(), parse_mode="html")

    elif cmd.startswith(".calc "):
        expr = raw[6:].strip()
        crypto_result = await calc_crypto(expr)
        if crypto_result:
            await event.message.edit(crypto_result, parse_mode="html")
        else:
            result = safe_calc(expr)
            await event.message.edit(
                f"🧮 <b>Калькулятор</b>\n\n"
                f"<b>Выражение:</b>\n<code>{html(expr)}</code>\n\n"
                f"<b>Результат:</b>\n<code>{html(result)}</code>\n\n" + by_line(),
                parse_mode="html"
            )

    elif cmd.startswith(".gpt "):
        query = raw[5:].strip()
        if not query:
            return
        await event.message.edit(LOADING, parse_mode="html")
        try:
            ans = await or_request(
                "Ты умный и интересный ИИ-помощник. Отвечай полно, по делу, "
                "без лишней воды. Используй HTML-форматирование где уместно.",
                query, max_tokens=2000
            )
            await event.message.edit(
                f"🐓 <b>Ответ Нейросети:</b>\n\n{ans}\n\n" + by_line(),
                parse_mode="html"
            )
        except Exception as e:
            await event.message.edit(
                f"❌ <b>AI ошибка:</b>\n<code>{html(str(e)[:200])}</code>",
                parse_mode="html"
            )

    elif cmd.startswith(".погода "):
        city = raw[8:].strip()
        if not city:
            return
        await event.message.edit(LOADING, parse_mode="html")
        try:
            caption, img = await get_weather(city)
            await event.message.delete()
            if img:
                buf = io.BytesIO(img)
                buf.name = "weather.jpg"
                await client.send_file(event.chat_id, buf, caption=caption, parse_mode="html")
            else:
                await client.send_message(event.chat_id, caption, parse_mode="html")
        except Exception as e:
            try:
                await client.send_message(
                    event.chat_id,
                    f"❌ <b>Ошибка:</b>\n<code>{html(str(e)[:200])}</code>",
                    parse_mode="html"
                )
            except Exception:
                pass

    elif cmd.startswith(".скачать "):
        rest = raw[9:].strip()
        quality = 720
        if rest.startswith("1080 "):
            quality = 1080
            yt_url = rest[5:].strip()
        elif rest.startswith("720 "):
            quality = 720
            yt_url = rest[4:].strip()
        else:
            yt_url = rest
        if not yt_url:
            return
        await event.message.edit(LOADING, parse_mode="html")
        filepath, result = await download_youtube(yt_url, quality)
        if filepath and os.path.exists(filepath):
            await _send_video(filepath, result, f"{quality}p")
        else:
            await event.message.edit(result or "❌", parse_mode="html")

    elif cmd.startswith(".tt "):
        tt_url = raw[4:].strip()
        if not tt_url:
            return
        await event.message.edit(LOADING, parse_mode="html")
        filepath, result = await download_tiktok(tt_url)
        if filepath and os.path.exists(filepath):
            await _send_video(filepath, result, "TikTok")
        else:
            await event.message.edit(result or "❌", parse_mode="html")

    elif cmd == ".scam":
        await cmd_scam(event)

    elif cmd == ".lol":
        await cmd_lol(event)

    elif cmd == ".info":
        await event.message.edit(LOADING, parse_mode="html")
        try:
            await event.message.edit(await get_user_info(event), parse_mode="html")
        except Exception as e:
            await event.message.edit(
                f"❌ <b>Ошибка:</b> <code>{html(str(e)[:200])}</code>",
                parse_mode="html"
            )

    elif cmd == ".me":
        await event.message.edit(LOADING, parse_mode="html")
        try:
            text, photo = await cmd_me(event)
            await event.message.delete()
            if photo:
                buf = io.BytesIO(photo)
                buf.name = "avatar.jpg"
                await client.send_file(event.chat_id, buf, caption=text, parse_mode="html")
            else:
                await client.send_message(event.chat_id, text, parse_mode="html")
        except Exception as e:
            await event.message.edit(
                f"❌ <b>Ошибка:</b> <code>{html(str(e)[:200])}</code>",
                parse_mode="html"
            )

    elif cmd.startswith(".editme "):
        prefix_len = len(".editme ")
        custom_html = extract_formatted_body(msg.raw_text, msg.entities, prefix_len)
        settings.set_val("custom_me_text", custom_html)
        await event.message.edit(
            f"✅ <b>Профиль .me обновлён</b>\n\n"
            f"<b>Превью:</b>\n<blockquote>{custom_html}</blockquote>\n\n"
            f"<b>Переменные:</b>\n"
            f"<code>(ник)</code> <code>(юзернейм)</code> <code>(айди)</code> "
            f"<code>(год)</code> <code>(чат)</code>\n\n"
            f"<code>.setme</code> — сброс к стандартному\n\n" + by_line(),
            parse_mode="html"
        )

    elif cmd == ".setme":
        settings.set_val("custom_me_text", None)
        settings.set_val("custom_me_pic", None)
        await event.message.edit(
            f"✅ <b>Профиль .me сброшен к стандартному</b>\n\n" + by_line(),
            parse_mode="html"
        )

    elif cmd.startswith(".setpic "):
        url = raw[8:].strip()
        if not url:
            await event.message.edit(
                "❗ Укажи ссылку: <code>.setpic https://...</code>",
                parse_mode="html"
            )
            return
        settings.set_val("custom_me_pic", url)
        await event.message.edit(
            f"✅ <b>Фото профиля .me обновлено</b>\n\n"
            f"<code>.setme</code> — сброс к стандартному\n\n" + by_line(),
            parse_mode="html"
        )

    elif cmd == ".check":
        reply = await event.message.get_reply_message()
        if not reply:
            await event.message.edit(
                "❗ Используй <code>.check</code> <b>ответом</b> на сообщение.",
                parse_mode="html"
            )
            return
        target = await resolve_sender(reply)
        if not target:
            await event.message.edit(
                "❌ Не удалось определить пользователя.", parse_mode="html"
            )
            return
        name      = get_username(target)
        target_id = target.id
        if target_id == (await client.get_me()).id:
            await event.message.edit(
                f"{pe('alien')} <b>Binary Userbot обнаружен</b>\n\n"
                f"{pe('user')} Это ты сам\n"
                f"📦 Версия: <code>{BOT_VERSION}</code>\n\n" + by_line(),
                parse_mode="html"
            )
            return
        await event.message.edit(LOADING, parse_mode="html")
        evt = asyncio.Event()
        state.check_events[target_id]  = evt
        state.check_results.pop(target_id, None)
        try:
            await client.send_message(target_id, CHECK_PING)
        except Exception as e:
            state.check_events.pop(target_id, None)
            await event.message.edit(
                f"❌ Не удалось отправить сообщение: <code>{html(str(e)[:150])}</code>",
                parse_mode="html"
            )
            return
        try:
            await asyncio.wait_for(evt.wait(), timeout=5.0)
            result_text  = state.check_results.get(target_id, "")
            version_info = result_text[len(CHECK_PONG):].strip()
            version_label = version_info.split("\n", 1)[0].strip()
            await event.message.edit(
                f"{pe('alien')} <b>Binary Userbot обнаружен!</b>\n\n"
                f"{pe('user')} {html(name)}\n"
                f"📦 Версия: <code>{html(version_label)}</code>\n\n" + by_line(),
                parse_mode="html"
            )
        except asyncio.TimeoutError:
            await event.message.edit(
                f"{pe('skull')} <b>Binary Userbot не найден</b>\n\n"
                f"{pe('user')} {html(name)} не ответил за 5 сек.\n"
                f"<i>Вероятно, юзербот не установлен.</i>\n\n" + by_line(),
                parse_mode="html"
            )
        finally:
            state.check_events.pop(target_id, None)
            state.check_results.pop(target_id, None)

    elif cmd == ".stat":
        await event.message.edit(LOADING, parse_mode="html")
        await event.message.edit(await cmd_stat(), parse_mode="html")

    elif cmd.startswith(".faq"):
        rest = raw[4:].strip().lower()
        try:
            from module_loader import get_loaded_modules
            mods = get_loaded_modules()
            combined_faq = dict(FAQ_DATA)
            for mod_cmd, mod in mods.items():
                if mod_cmd not in combined_faq:
                    combined_faq[mod_cmd] = (
                        f"📦 <b>{mod['cmd']}</b>\n\n"
                        f"{mod['desc']}\n\n"
                        f"<i>Модуль: {mod['name']}</i>"
                    )
        except Exception:
            combined_faq = dict(FAQ_DATA)

        if not rest:
            keys_list = "  ".join(f"<code>{k}</code>" for k in combined_faq.keys())
            await event.message.edit(
                f"❓ <b>FAQ — доступные команды:</b>\n\n{keys_list}\n\n"
                f"<i>Пример: </i><code>.faq .gpt</code>\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            key  = rest if rest.startswith(".") else "." + rest
            info = combined_faq.get(key)
            if info:
                await event.message.edit(info + "\n\n" + by_line(), parse_mode="html")
            else:
                await event.message.edit(
                    f"❓ Команда <code>{html(key)}</code> не найдена в FAQ.\n\n" + by_line(),
                    parse_mode="html"
                )

    elif cmd == ".lastnews":
        await event.message.edit(LOADING, parse_mode="html")
        try:
            await event.message.edit(await get_last_news(), parse_mode="html")
        except Exception as e:
            await event.message.edit(
                f"❌ <b>Ошибка:</b> <code>{html(str(e)[:200])}</code>",
                parse_mode="html"
            )

    elif cmd.startswith(".note"):
        note_text = raw[5:].strip() if len(raw) > 5 else ""
        notes = load_notes()
        if note_text:
            ts = datetime.now().strftime("%d.%m.%Y %H:%M")
            notes.append({"text": note_text, "ts": ts})
            save_notes(notes)
            star = pe("star_pe")
            write_ico = '<tg-emoji emoji-id="5258331647358540449">✍️</tg-emoji>'
            cal_ico   = '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji>'
            await event.message.edit(
                f"{cal_ico} Заметка сохранена\n\n"
                f"{write_ico} Всего: {len(notes)}\n\n"
                f"by @B1nnary {star}",
                parse_mode="html"
            )
        else:
            cal_ico  = '<tg-emoji emoji-id="5258105663359294787">🗓</tg-emoji>'
            stat_ico = '<tg-emoji emoji-id="5258391025281408576">📈</tg-emoji>'
            star     = pe("star_pe")
            if not notes:
                await event.message.edit(
                    f"{cal_ico} Заметок нет.\n\n"
                    f"<code>.note текст</code> — добавить",
                    parse_mode="html"
                )
            else:
                lines = [f"{cal_ico} <b>Мои заметки</b>\n"]
                for i, n in enumerate(notes, 1):
                    lines.append(f"<b>{i}.</b> ({n.get('ts', '')}) {html(n['text'])}")
                lines.append(f"\n{stat_ico} Всего: {len(notes)}")
                lines.append(f"by @B1nnary {star}")
                await event.message.edit("\n".join(lines), parse_mode="html")

    elif cmd == ".delnote":
        save_notes([])
        arch_ico = '<tg-emoji emoji-id="5258389041006518073">📂</tg-emoji>'
        star     = pe("star_pe")
        await event.message.edit(
            f"{arch_ico} Все заметки удалены.\n\nby @B1nnary {star}",
            parse_mode="html"
        )

    elif cmd == ".proxy":
        await event.message.edit(PROXY_TEXT + by_line(), parse_mode="html")

    elif cmd.startswith(".bwchat"):
        arg = raw[7:].strip()
        if not arg:
            cur = state.bw_chat_id
            await event.message.edit(
                f"🔒 <b>Чат модерации</b>\n\n"
                f"Текущий: <code>{cur if cur else 'не задан'}</code>\n\n"
                f"Использование: <code>.bwchat @username или ID</code>\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            try:
                if arg.lstrip("-").isdigit():
                    new_id = int(arg)
                else:
                    entity = await client.get_entity(arg)
                    new_id = entity.id
                state.bw_chat_id = new_id
                settings.set_val("bw_chat_id", new_id)
                await event.message.edit(
                    f"🔒 <b>Чат модерации установлен</b>\n\n"
                    f"ID: <code>{new_id}</code>\n\n" + by_line(),
                    parse_mode="html"
                )
            except Exception as e:
                await event.message.edit(
                    f"❌ Не удалось найти чат: <code>{html(str(e)[:200])}</code>",
                    parse_mode="html"
                )

    elif cmd.startswith(".bw"):
        rest = raw[3:].strip()
        if not rest:
            await event.message.edit(
                f"🚫 <b>Bad Word Filter</b>\n\n"
                f"📋 Активных слов: <code>{len(state.bw_words)}</code>\n\n"
                f"<b>Управление:</b>\n"
                f"<code>.bw слово</code> — добавить\n"
                f"<code>.bw список</code> — показать все\n"
                f"<code>.bw очистить</code> — удалить все\n\n" + by_line(),
                parse_mode="html"
            )
        elif rest.lower() == "список":
            if state.bw_words:
                words_str = "\n".join(f"• <code>{html(w)}</code>" for w in state.bw_words)
                await event.message.edit(
                    f"🚫 <b>Запрещённые слова</b>\n\n{words_str}\n\n"
                    f"📊 Всего: <code>{len(state.bw_words)}</code>\n\n" + by_line(),
                    parse_mode="html"
                )
            else:
                await event.message.edit("📋 <b>Список пуст.</b>", parse_mode="html")
        elif rest.lower() == "очистить":
            state.bw_words.clear()
            settings.set_val("bw_words", state.bw_words)
            await event.message.edit("✅ <b>Список слов очищен.</b>\n\n" + by_line(), parse_mode="html")
        else:
            word = rest.lower()
            if word not in state.bw_words:
                state.bw_words.append(word)
                await event.message.edit(
                    f"✅ <b>Слово добавлено в фильтр</b>\n\n"
                    f"🔤 <code>{html(word)}</code>\n"
                    f"📊 Всего слов: <code>{len(state.bw_words)}</code>\n\n" + by_line(),
                    parse_mode="html"
                )
            else:
                await event.message.edit(
                    f"ℹ️ Слово <code>{html(word)}</code> уже в списке.", parse_mode="html"
                )

    elif cmd == ".mute":
        reply = await event.message.get_reply_message()
        if not reply:
            await event.message.edit(
                "❗ Используй <code>.mute</code> <b>ответом</b>.", parse_mode="html"
            )
            return
        target = await resolve_sender(reply)
        if not target:
            await event.message.edit(
                "❌ Не удалось определить пользователя.", parse_mode="html"
            )
            return
        state.muted_users.setdefault(msg.chat_id, set()).add(target.id)
        await event.message.edit(
            f"🔇 <b>{html(get_username(target))}</b> замьючен\n\n"
            f"<code>.unmute</code> — снять\n\n" + by_line(),
            parse_mode="html"
        )

    elif cmd == ".unmute":
        reply = await event.message.get_reply_message()
        if not reply:
            await event.message.edit(
                "❗ Используй <code>.unmute</code> <b>ответом</b>.", parse_mode="html"
            )
            return
        target = await resolve_sender(reply)
        if not target:
            await event.message.edit(
                "❌ Не удалось определить пользователя.", parse_mode="html"
            )
            return
        chat_muted = state.muted_users.get(msg.chat_id, set())
        name = get_username(target)
        if target.id in chat_muted:
            chat_muted.discard(target.id)
            await event.message.edit(
                f"🔊 <b>{html(name)}</b> размьючен\n\n" + by_line(), parse_mode="html"
            )
        else:
            await event.message.edit(
                f"ℹ️ <b>{html(name)}</b> не был замьючен.", parse_mode="html"
            )

    elif cmd == ".cat":
        asyncio.create_task(run_animation(event.message, CAT_FRAMES, delay=1.1))

    elif cmd == ".rocket":
        asyncio.create_task(
            run_animation(event.message, ROCKET_FRAMES, delay=1.0, parse_mode="html")
        )

    elif cmd == ".fight":
        asyncio.create_task(
            run_animation(event.message, POKEMON_FRAMES, delay=1.1, parse_mode="html")
        )

    elif cmd.startswith(".ком ") or cmd == ".ком":
        new_text = raw[5:].strip() if (len(raw) > 4 and raw[4] == " ") else ""
        if not new_text or state.auto_comment_text == new_text:
            state.auto_comment_text = None
            await event.message.edit(
                "💬 <b>Авто-комментирование отключено</b>\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            state.auto_comment_text = new_text
            ch_count = len(state.auto_comment_channels)
            await event.message.edit(
                f"💬 <b>Авто-комментирование включено</b>\n\n"
                f"📝 <code>{html(new_text)}</code>\n"
                f"📡 Каналов: <code>{ch_count}</code>\n\n"
                f"Повтори для отключения.\n\n" + by_line(),
                parse_mode="html"
            )

    elif cmd == ".ебалай":
        if not priv:
            await event.message.edit(
                "❗ Только в <b>личных чатах</b>.", parse_mode="html"
            )
            return
        state.ebalaj_active[msg.chat_id]  = 0
        state.ebalaj_history[msg.chat_id] = []
        await event.message.delete()

    elif cmd == ".troll":
        if not priv:
            await event.message.edit(
                "❗ Только в <b>личных чатах</b>.", parse_mode="html"
            )
            return
        state.troll_active[msg.chat_id]  = 0
        state.troll_history[msg.chat_id] = []
        await event.message.delete()

    elif cmd == ".ac":
        if not priv:
            await event.message.edit(
                "❗ Только в <b>личных чатах</b>.", parse_mode="html"
            )
            return
        if state.ac_active.get(msg.chat_id):
            state.ac_active[msg.chat_id] = False
            state.ac_history.pop(msg.chat_id, None)
            await event.message.edit(
                "🔴 <b>Авто-общение отключено</b>\n\n" + by_line(), parse_mode="html"
            )
        else:
            state.ac_active[msg.chat_id] = True
            state.ac_history.pop(msg.chat_id, None)
            await event.message.edit(
                "🤖 <b>Авто-общение включено</b>\n\n"
                "Анализирую твой стиль...\n"
                "Повтори <code>.ac</code> для отключения.\n\n" + by_line(),
                parse_mode="html"
            )

    elif cmd == ".стоп":
        stopped = []
        if msg.chat_id in state.ebalaj_active:
            c = state.ebalaj_active.pop(msg.chat_id, 0)
            state.ebalaj_history.pop(msg.chat_id, None)
            stopped.append(f"🤪 Ебалай — <code>{c}</code> сообщений")
        if msg.chat_id in state.troll_active:
            c = state.troll_active.pop(msg.chat_id, 0)
            state.troll_history.pop(msg.chat_id, None)
            stopped.append(f"😡 Troll — <code>{c}</code> сообщений")
        if state.ac_active.get(msg.chat_id):
            state.ac_active[msg.chat_id] = False
            state.ac_history.pop(msg.chat_id, None)
            stopped.append("🤖 Auto-Chat")
        if stopped:
            await event.message.edit(
                "🛑 <b>Режим(ы) отключены</b>\n\n" +
                "\n".join(stopped) + "\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            await event.message.edit(
                "ℹ️ Ни один режим не был активен.", parse_mode="html"
            )

    elif cmd == ".stopall":
        stopped = []
        cnt = len(state.ebalaj_active)
        if cnt:
            state.ebalaj_active.clear()
            state.ebalaj_history.clear()
            stopped.append(f"🤪 Ебалай ({cnt} чатов)")
        cnt = len(state.troll_active)
        if cnt:
            state.troll_active.clear()
            state.troll_history.clear()
            stopped.append(f"😡 Troll ({cnt} чатов)")
        ac_cnt = sum(1 for v in state.ac_active.values() if v)
        if ac_cnt:
            state.ac_active.clear()
            state.ac_history.clear()
            stopped.append(f"🤖 Auto-Chat ({ac_cnt} чатов)")
        if state.auto_comment_text:
            state.auto_comment_text = None
            stopped.append("💬 Авто-комментирование")
        if state.eng_mode_active:
            state.eng_mode_active = False
            stopped.append("🇬🇧 ENG режим")
        if state.bw_words:
            state.bw_words.clear()
            stopped.append("🚫 Bad Words фильтр")
        if stopped:
            await event.message.edit(
                f"🛑 <b>Все процессы остановлены</b>\n\n" +
                "\n".join(f"• {s}" for s in stopped) +
                "\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            await event.message.edit("ℹ️ Нет активных процессов.", parse_mode="html")

    elif cmd == ".setting":
        await event.message.edit(cmd_setting(), parse_mode="html")

    elif cmd == ".premium":
        state.premium_emoji_active = not state.premium_emoji_active
        settings.set_val("premium_emoji_active", state.premium_emoji_active)
        status = "включены ✨" if state.premium_emoji_active else "выключены"
        await event.message.edit(
            f"{pe('star_pe')} <b>Премиум эмодзи {status}</b>\n\n"
            f"Повтори <code>.premium</code> для переключения.\n\n" + by_line(),
            parse_mode="html"
        )

    elif cmd.startswith(".terminal "):
        terminal_cmd = raw[10:].strip()
        if not terminal_cmd:
            return
        await event.message.edit(
            f"{pe('pc')} <i>Выполняю команду...</i>", parse_mode="html"
        )
        try:
            proc = await asyncio.create_subprocess_shell(
                terminal_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            out    = stdout.decode("utf-8", errors="replace")
            err    = stderr.decode("utf-8", errors="replace")
            output = (out + err).strip() or "(нет вывода)"
            if len(output) > 3000:
                output = output[:3000] + "\n…(обрезано)"
            await event.message.edit(
                f"{pe('pc')} <b>Terminal</b>\n\n"
                f"<code>$ {html(terminal_cmd)}</code>\n\n"
                f"<code>{html(output)}</code>\n\n" + by_line(),
                parse_mode="html"
            )
        except asyncio.TimeoutError:
            await event.message.edit(
                f"⏱ <b>Таймаут</b> (30с)\n\n<code>$ {html(terminal_cmd)}</code>",
                parse_mode="html"
            )
        except Exception as e:
            await event.message.edit(
                f"❌ <b>Ошибка:</b>\n<code>{html(str(e)[:300])}</code>",
                parse_mode="html"
            )

    elif cmd.startswith(".logs"):
        arg = raw[5:].strip()
        if not arg or arg.lower() == "me":
            from config import MY_ID
            state.logs_chat_id = MY_ID
            settings.set_val("logs_chat_id", MY_ID)
            await event.message.edit(
                f"📋 <b>Чат логов сброшен</b>\n\nЛоги идут в <b>Избранное</b>\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            try:
                if arg.lstrip("-").isdigit():
                    new_id = int(arg)
                else:
                    entity = await client.get_entity(arg)
                    new_id = entity.id
                state.logs_chat_id = new_id
                settings.set_val("logs_chat_id", new_id)
                await event.message.edit(
                    f"📋 <b>Чат логов установлен</b>\n\n"
                    f"Логи идут в: <code>{html(str(new_id))}</code>\n\n" + by_line(),
                    parse_mode="html"
                )
            except Exception as e:
                await event.message.edit(
                    f"❌ Не удалось найти чат: <code>{html(str(e)[:200])}</code>",
                    parse_mode="html"
                )

    elif cmd == ".ss":
        reply = await event.message.get_reply_message()
        if not reply:
            await event.message.edit(
                "❗ Используй <code>.ss</code> <b>ответом</b> на сообщение.",
                parse_mode="html"
            )
            return
        target    = await resolve_sender(reply)
        name      = get_username(target) if target else "красавчик"
        last_text = (reply.text or "")[:100]
        await event.message.edit(LOADING, parse_mode="html")
        try:
            flirt = await or_request(
                "Ты дерзкий, уверенный в себе чувак, который умеет подкатывать. "
                "Напиши одну дерзкую, остроумную фразу-подкат к человеку — коротко, "
                "с юмором, уверенно, чуть нагло. "
                "Используй имя/ник если есть. На русском. Только сам текст подката.",
                f"Имя/ник: {name}. Последнее сообщение: «{last_text}»",
                max_chars=200, max_tokens=150
            )
            await event.message.edit(
                f"{pe('love')} {html(flirt)}", parse_mode="html"
            )
        except Exception as e:
            await event.message.edit(
                f"❌ <b>Ошибка:</b> <code>{html(str(e)[:150])}</code>",
                parse_mode="html"
            )

    elif cmd == ".max":
        meme_url = "https://memepedia.ru/wp-content/uploads/2017/04/%D0%B5%D0%B1%D0%B0%D1%82%D1%8C-%D1%82%D1%8B-%D0%BB%D0%BE%D1%85.jpg"
        await event.message.edit(
            f"Я перехожу в мессенджер макс, скачайте по моей ссылке чтобы получить "
            f"фрибет на бонусный баланс и 30 фриспинов: "
            f'<a href="{meme_url}">я в макс</a>',
            parse_mode="html", link_preview=False
        )

    elif cmd == ".snos":
        reply = await event.message.get_reply_message()
        if reply:
            target = await resolve_sender(reply)
            target_name = get_username(target) if target else "Unknown"
        else:
            target_name = get_username(await client.get_me())
        try:
            await event.message.delete()
        except Exception:
            pass
        asyncio.create_task(run_prank(event.chat_id, target_name))

    elif cmd.startswith(".перевод "):
        text_to_translate = raw[9:].strip()
        if not text_to_translate:
            return
        await event.message.edit(LOADING, parse_mode="html")
        try:
            translated = await or_request(
                "Ты переводчик. Переведи на английский. Только перевод, без пояснений.",
                text_to_translate, max_tokens=500
            )
            await event.message.edit(html(translated), parse_mode="html")
        except Exception as e:
            await event.message.edit(
                f"❌ <b>Ошибка:</b> <code>{html(str(e)[:200])}</code>",
                parse_mode="html"
            )

    elif cmd.startswith(".addcom"):
        parts = raw[7:].strip().split()
        if len(parts) < 2:
            await event.message.edit(
                f"📡 <b>Добавить канал для авто-комментирования</b>\n\n"
                f"<code>.addcom CHANNEL_ID DISCUSSION_ID</code>\n\n"
                f"Текущих каналов: <code>{len(state.auto_comment_channels)}</code>\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            try:
                ch_id   = int(parts[0])
                disc_id = int(parts[1])
                state.auto_comment_channels[ch_id] = disc_id
                settings.add_auto_comment_channel(ch_id, disc_id)
                await event.message.edit(
                    f"✅ <b>Канал добавлен</b>\n\n"
                    f"Канал: <code>{ch_id}</code>\n"
                    f"Чат: <code>{disc_id}</code>\n"
                    f"Всего каналов: <code>{len(state.auto_comment_channels)}</code>\n\n" + by_line(),
                    parse_mode="html"
                )
            except ValueError:
                await event.message.edit(
                    "❌ ID должны быть числами. Пример: <code>.addcom -1001234567890 -1009876543210</code>",
                    parse_mode="html"
                )

    elif cmd.startswith(".delcom"):
        arg = raw[7:].strip()
        if not arg:
            if not state.auto_comment_channels:
                await event.message.edit("📡 Список каналов пуст.", parse_mode="html")
            else:
                lines = "\n".join(
                    f"• <code>{ch}</code> → <code>{disc}</code>"
                    for ch, disc in state.auto_comment_channels.items()
                )
                await event.message.edit(
                    f"📡 <b>Каналы авто-комментирования ({len(state.auto_comment_channels)})</b>\n\n"
                    f"<blockquote>{lines}</blockquote>\n\n"
                    f"<code>.delcom CHANNEL_ID</code> — удалить канал\n\n" + by_line(),
                    parse_mode="html"
                )
        else:
            try:
                ch_id = int(arg)
                if settings.remove_auto_comment_channel(ch_id):
                    state.auto_comment_channels.pop(ch_id, None)
                    await event.message.edit(
                        f"🗑 <b>Канал удалён</b>\n\n"
                        f"ID: <code>{ch_id}</code>\n"
                        f"Осталось: <code>{len(state.auto_comment_channels)}</code>\n\n" + by_line(),
                        parse_mode="html"
                    )
                else:
                    await event.message.edit(
                        f"❌ Канал <code>{ch_id}</code> не найден в списке.",
                        parse_mode="html"
                    )
            except ValueError:
                await event.message.edit(
                    "❌ Укажи числовой ID канала. Пример: <code>.delcom -1001234567890</code>",
                    parse_mode="html"
                )

    elif cmd == ".eng":
        state.eng_mode_active = not state.eng_mode_active
        settings.set_val("eng_mode_active", state.eng_mode_active)
        if state.eng_mode_active:
            await event.message.edit(
                "🇬🇧 <b>ENG режим включён</b>\n\nВсе твои сообщения → английский.\n"
                "Повтори <code>.eng</code> для отключения.\n\n" + by_line(),
                parse_mode="html"
            )
        else:
            await event.message.edit(
                "🔴 <b>ENG режим отключён</b>\n\n" + by_line(), parse_mode="html"
            )
