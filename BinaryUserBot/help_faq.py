"""
Тексты .help, .faq и .setting.
"""
import state
from config import BOT_NAME, BOT_VERSION, MY_ID
import settings
from premium_emoji import pe, by_line, toggle_pe, status_pe

CMD_EMOJI = '<tg-emoji emoji-id="5260348422266822411">💬</tg-emoji>'
FAQ_EMOJI = '<tg-emoji emoji-id="5258334872878980409">🎓</tg-emoji>'
CHECK_EMOJI = '<tg-emoji emoji-id="5260726538302660868">✅</tg-emoji>'

FAQ_DATA = {
    ".gpt": (
        "🐓 <b>.gpt &lt;запрос&gt;</b>\n\n"
        "Отправляет запрос к нейросети GPT-4o-mini через OpenRouter.\n\n"
        "<b>Пример:</b>\n<code>.gpt объясни квантовую запутанность</code>"
    ),
    ".погода": (
        "🌤 <b>.погода &lt;город&gt;</b>\n\n"
        "Загружает карточку прогноза погоды.\n\n"
        "<b>Пример:</b>\n<code>.погода Москва</code>"
    ),
    ".calc": (
        "🧮 <b>.calc &lt;выражение&gt;</b>\n\n"
        "Математика и крипто-конвертор.\n\n"
        "<code>.calc 2^10</code>\n<code>.calc 1 BTC</code>"
    ),
    ".скачать": (
        "📥 <b>.скачать [720|1080] &lt;ссылка&gt;</b>\n\n"
        "Скачивает видео с YouTube.\n\n"
        "<code>.скачать https://youtu.be/xxx</code>"
    ),
    ".tt": (
        "🎵 <b>.tt &lt;ссылка TikTok&gt;</b>\n\n"
        "Скачивает видео из TikTok без водяного знака.\n\n"
        "<code>.tt https://vm.tiktok.com/xxx</code>"
    ),
    ".scam": (
        "🔍 <b>.scam</b> <i>(ответом)</i>\n\n"
        "Проверяет юзернейм по базе скамеров @GID_ScamBase."
    ),
    ".lol": (
        "😂 <b>.lol</b> <i>(ответом)</i>\n\n"
        "ИИ придумывает едкую шутку про пользователя."
    ),
    ".info": (
        "📊 <b>.info</b> <i>(ответом)</i>\n\n"
        "Подробный профиль пользователя: имя, ID, флаги, сообщения, дата."
    ),
    ".me": (
        "👤 <b>.me</b>\n\n"
        "Твой собственный профиль с фото."
    ),
    ".mute": (
        "🔇 <b>.mute</b> <i>(ответом)</i>\n\n"
        "Замьючивает пользователя — все сообщения молча удаляются.\n"
        "Снять: <code>.unmute</code>"
    ),
    ".bw": (
        "🚫 <b>.bw &lt;слово&gt;</b>\n\n"
        "Добавляет слово в чёрный список чата модерации.\n\n"
        "<code>.bw список</code> — все слова\n"
        "<code>.bw очистить</code> — сброс\n"
        "<code>.bwchat @чат</code> — сменить чат модерации"
    ),
    ".ком": (
        "💬 <b>.ком &lt;текст&gt;</b>\n\n"
        "Включает авто-комментирование постов в 7 каналах."
    ),
    ".ебалай": (
        "🤪 <b>.ебалай</b> <i>(в личку)</i>\n\n"
        "ИИ-персонаж 'тупой Вася' отвечает вместо тебя. Лимит 50 сообщений.\n"
        "Отключить: <code>.стоп</code>"
    ),
    ".troll": (
        "😡 <b>.troll</b> <i>(в личку)</i>\n\n"
        "Злой матерящийся ИИ-тролль. Лимит 50 сообщений.\n"
        "Отключить: <code>.стоп</code>"
    ),
    ".ac": (
        "🤖 <b>.ac</b>\n\n"
        "Авто-общение: ИИ отвечает в твоём стиле. Только личные чаты.\n"
        "Повтор — выключить."
    ),
    ".note": (
        "📝 <b>.note &lt;текст&gt;</b>\n\n"
        "<code>.note текст</code> — добавить\n"
        "<code>.note</code> — показать все\n"
        "<code>.delnote</code> — удалить все"
    ),
    ".lastnews": (
        "📰 <b>.lastnews</b>\n\n"
        "AI-дайджест последних постов @binary_news за 24 часа."
    ),
    ".stat": (
        "📈 <b>.stat</b>\n\n"
        "Статистика по всем диалогам аккаунта."
    ),
    ".proxy": (
        "🌐 <b>.proxy</b>\n\n"
        "3 бесплатных MTProto прокси для Telegram."
    ),

    ".eng": (
        "🇬🇧 <b>.eng</b>\n\n"
        "Все исходящие сообщения → английский. Повтор — выключить."
    ),
    ".check": (
        "🔍 <b>.check</b> <i>(ответом)</i>\n\n"
        "Проверяет, установлен ли Binary Userbot у пользователя."
    ),
    ".terminal": (
        "🖥 <b>.terminal &lt;команда&gt;</b>\n\n"
        "Выполняет команду оболочки на сервере. Таймаут 30 сек."
    ),
    ".setting": (
        "⚙️ <b>.setting</b>\n\n"
        "Панель всех настроек и активных режимов."
    ),
    ".premium": (
        "✨ <b>.premium</b>\n\n"
        "Включает/выключает анимированные премиум эмодзи."
    ),
    ".stopall": (
        "🛑 <b>.stopall</b>\n\n"
        "Останавливает все активные режимы и процессы."
    ),
    ".logs": (
        "📋 <b>.logs &lt;@username или ID&gt;</b>\n\n"
        "<code>.logs me</code> — Избранное\n"
        "<code>.logs @чат</code> — свой чат"
    ),
    ".ss": (
        "😍 <b>.ss</b> <i>(ответом)</i>\n\n"
        "ИИ дерзко подкатывает к пользователю."
    ),
    ".max": ("📱 <b>.max</b>\n\nОтправляет сообщение о переходе в мессенджер Макс."),
    ".snos": (
        "🎭 <b>.snos</b> <i>(ответом)</i>\n\n"
        "Шуточная анимация-розыгрыш с прогресс-баром."
    ),
    ".гороскоп": (
        "♈️ <b>.гороскоп &lt;знак&gt;</b>\n\n"
        "Гороскоп на выбранный знак зодиака."
    ),
    ".wiki": (
        "🧠 <b>.wiki &lt;запрос&gt;</b>\n\n"
        "Краткая выжимка из Википедии."
    ),
    ".movie": (
        "🎬 <b>.movie &lt;название&gt;</b>\n\n"
        "Рейтинг и информация о фильме."
    ),
    ".tz": (
        "⏰ <b>.tz &lt;город&gt;</b>\n\n"
        "Текущее местное время в указанном городе."
    ),
    ".dict": (
        "📖 <b>.dict &lt;слово&gt;</b>\n\n"
        "Определение слова из словаря."
    ),
    ".lyr": (
        "🎤 <b>.lyr &lt;песня&gt;</b>\n\n"
        "Текст указанной песни."
    ),
    ".music": (
        "🎵 <b>.music &lt;название&gt;</b>\n\n"
        "Ищет и присылает готовую песню аудио-файлом для прослушивания."
    ),
    ".steam": (
        "🎮 <b>.steam &lt;игра&gt;</b>\n\n"
        "Информация об игре в Steam."
    ),
    ".metadata": (
        "🌐 <b>.metadata &lt;ссылка&gt;</b>\n\n"
        "Информация о странице (метаданные сайта)."
    ),
    ".afk": (
        "💤 <b>.afk &lt;причина&gt;</b>\n\n"
        "Включает режим AFK. Авто-ответ при тегах и в ЛС."
    ),
    ".chat": (
        "📊 <b>.chat</b>\n\n"
        "Статистика чата за последние 3000 сообщений."
    ),
    ".meme": (
        "🤡 <b>.meme</b>\n\n"
        "Случайный мем с Reddit."
    ),
    ".ip": (
        "📡 <b>.ip &lt;IP-адрес&gt;</b>\n\n"
        "Информация об IP-адресе."
    ),
    ".whois": (
        "🔎 <b>.whois &lt;домен&gt;</b>\n\n"
        "Информация о владельце домена."
    ),
    ".history": (
        "🕰 <b>.history &lt;число&gt;</b>\n\n"
        "Показывает последние N сообщений от пользователя (вызывать ответом)."
    ),
    ".bwchat": (
        "🔒 <b>.bwchat &lt;@username или ID&gt;</b>\n\n"
        "Устанавливает чат для модерации (Bad Words фильтр).\n"
        "Сохраняется после перезапуска.\n\n"
        "<code>.bwchat</code> — показать текущий\n"
        "<code>.bwchat -1001234567890</code> — установить по ID"
    ),
    ".addcom": (
        "📡 <b>.addcom &lt;CHANNEL_ID&gt; &lt;DISCUSSION_ID&gt;</b>\n\n"
        "Добавляет канал в список авто-комментирования.\n"
        "Сохраняется после перезапуска.\n\n"
        "<code>.addcom -1001234567890 -1009876543210</code>"
    ),
    ".delcom": (
        "🗑 <b>.delcom &lt;CHANNEL_ID&gt;</b>\n\n"
        "Удаляет канал из списка авто-комментирования.\n"
        "<code>.delcom</code> — показать список каналов"
    ),
}


def get_help_text() -> str:
    # Предполагается, что pe, CMD_EMOJI, BOT_NAME и т.д. определены глобально
    alien = pe("alien")
    cmds = [
        ".gpt", ".погода", ".цена", ".calc", ".скачать", ".tt",
        ".scam", ".lol", ".info", ".me", ".check",
        ".mute", ".unmute", ".bw",
        ".cat", ".rocket", ".fight",
        ".ком", ".proxy",
        ".ебалай", ".troll", ".стоп",
        ".ac",
        ".note", ".delnote",
        ".lastnews", ".stat",
        ".перевод", ".eng",
        ".terminal",
        ".setting", ".premium", ".stopall", ".logs",
        ".ss", ".max", ".snos",
        ".гороскоп", ".wiki", ".movie", ".tz", ".dict", ".lyr",
        ".music", ".steam", ".metadata", ".afk", ".chat", ".meme",
        ".ip", ".whois", ".history",
        ".md",
        ".bwchat", ".addcom", ".delcom",
    ]

    try:
        from module_loader import get_loaded_modules
        for mod_cmd in get_loaded_modules():
            if mod_cmd not in cmds:
                cmds.append(mod_cmd)
    except Exception:
        pass

    rows = []
    for i in range(0, len(cmds), 3):
        chunk = cmds[i:i+3]
        # Используем f-строку аккуратно
        rows.append("  ".join(f"{CMD_EMOJI} {c}" for c in chunk))

    cmds_block = "\n".join(rows)
    
    # Исправленная строка с ссылкой (используем одинарные кавычки снаружи)
    return (
        f"  {alien} <b>{BOT_NAME} {BOT_VERSION}</b>\n\n"
        f"<blockquote expandable>{cmds_block}</blockquote>\n\n"
        f"{FAQ_EMOJI} .faq &lt;команда&gt; — подробно о любой команде\n"
        f"----\n"
        f"{CHECK_EMOJI} Авто-мониторинг личных чатов.\n\n"
        f"{GIT} <b><a href='https://github.com/binary166/BinaryUserbot'>GitHub</a></b>\n\n"
        f"{by_line()}"
    )


def cmd_setting() -> str:
    # Получаем данные из состояния
    ebalaj_count = len(state.ebalaj_active)
    troll_count  = len(state.troll_active)
    ac_count     = sum(1 for v in state.ac_active.values() if v)
    muted_count  = sum(len(v) for v in state.muted_users.values())
    logs_label   = "Избранное" if state.logs_chat_id == MY_ID else str(state.logs_chat_id)

    # Иконки (добавил определения, чтобы не было ошибок)
    header_bolt = pe("gear")
    bw_tag = pe("shield") # или просто иконка, если pe не вернет ничего
    mute_ico = "🔇"
    log_ico = "📋"

    # Подгружаем список каналов из настроек (исправлено с ch_list на auto_comment_channels)
    auto_comment_channels = settings.get("auto_comment_channels", {})
    bw_chat = state.bw_chat_id or settings.get("bw_chat_id", "не задан")

    # Формируем красивый список каналов для вывода
    if auto_comment_channels:
        ch_lines = "\n".join(
            f"  <code>{ch_id}</code> → <code>{disc_id}</code>"
            for ch_id, disc_id in list(auto_comment_channels.items())[:5]
        )
        if len(auto_comment_channels) > 5:
            ch_lines += f"\n  … ещё {len(auto_comment_channels) - 5}"
    else:
        ch_lines = "  <i>нет каналов</i>"

    lines = [
        f"{header_bolt} <b>{BOT_NAME} {BOT_VERSION}</b> — настройки",
        "",
        "- <b>Режимы</b> -",
        f"{toggle_pe(state.eng_mode_active)}  ENG автоперевод",
        f"{status_pe(bool(state.auto_comment_text))}  Авто-комментирование",
        f"{status_pe(ebalaj_count > 0)}  Ебалай  ({ebalaj_count} чатов)",
        f"{status_pe(troll_count > 0)}  Troll  ({troll_count} чатов)",
        f"{status_pe(ac_count > 0)}  Auto-Chat  ({ac_count} чатов)",
        "",
        "- <b>Авто-комментирование</b> -",
        f"📡 Каналов: <b>{len(auto_comment_channels)}</b>",
        f"<blockquote>{ch_lines}</blockquote>", # Используем отформатированные строки ch_lines
        "<code>.addcom ID DISC_ID</code>  <code>.delcom ID</code>",
        "",
        "- <b>Фильтры</b> -",
        f"♾️ Bad Words: <code>{len(state.bw_words)}</code> слов",
        f"🔒 Чат модерации: <code>{bw_chat}</code>",
        f"<code>.bwchat @чат</code> — сменить",
        f"{mute_ico}  Замьючено: <code>{muted_count}</code> польз.",
        "",
        "- <b>Логи</b> -",
        f"{log_ico}  Чат: <code>{logs_label}</code>",
        "<code>.logs me</code>  |  <code>.logs @чат</code>",
        "",
        "- <b>Интерфейс</b> -",
        f"{toggle_pe(state.premium_emoji_active)}  Премиум эмодзи",
        "<code>.premium</code> — переключить",
        "",
        f"<i>{BOT_NAME} {BOT_VERSION}</i>  ·  {by_line()}",
    ]
    return "\n".join(lines)
