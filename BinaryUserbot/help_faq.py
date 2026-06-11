import state
from config import BOT_NAME, BOT_VERSION, MY_ID, EBALAJ_SYSTEM, TROLL_SYSTEM
import settings
from premium_emoji import pe, pe_force, by_line, toggle_pe, status_pe

CMD_EMOJI = '<tg-emoji emoji-id="5260348422266822411">💬</tg-emoji>'
FAQ_EMOJI = '<tg-emoji emoji-id="5258334872878980409">🎓</tg-emoji>'
CHECK_EMOJI = '<tg-emoji emoji-id="5260726538302660868">✅</tg-emoji>'
GIT = '<tg-emoji emoji-id="5346181118884331907">🐱</tg-emoji>'
UB_INFO_EMOJI = '<tg-emoji emoji-id="5877597667231534929">💠</tg-emoji>'
MANAGER_BOT_EMOJI = '<tg-emoji emoji-id="5895311993555915037">⚙️</tg-emoji>'
HELP_TITLE_EMOJI = '<tg-emoji emoji-id="5877260593903177342">⚙️</tg-emoji>'
HELP_FOOTER_EMOJI = '<tg-emoji emoji-id="5909015791088439934">✨</tg-emoji>'

FAQ_KNOWLEDGE_BASE = """
Binary Userbot v1.7 — Telegram userbot на Telethon.

Главное:
- Команды вызываются через точку: .help, .faq, .gpt, .md, .newmd и т.д.
- .help показывает список команд.
- .faq без аргументов показывает список команд, .faq .команда показывает описание команды.
- .faq вопрос задаёт вопрос нейросети по базе знаний Binary Userbot.
- .setting показывает режимы и настройки.
- .logs me сбрасывает лог-чат в Избранное, .logs @чат или ID меняет лог-чат.
- .premium включает/выключает премиум-эмодзи в оформлении.

AI:
- .gpt запрос — ответ нейросети через OpenRouter.
- .ca ответом — психологический анализ собеседника по последним 50 сообщениям.
- .newmd промпт — создаёт новый модуль по описанию и присылает .py файл.
- .md — GitMD: принимает .py файл, код или GitHub/raw ссылку, проверяет совместимость и при необходимости переписывает модуль под BinaryUserbot.
- .md install — сразу устанавливает модуль из ответа/ссылки.

Модули:
- builtin_modules — встроенные базовые модули, они загружаются вместе с ботом и не считаются дополнительной папкой пользователя.
- modules — пользовательские установленные модули.
- .savemod — установить .py файл ответом на сообщение.
- .mods — список установленных пользовательских модулей.
- .sendmod имя — прислать файл модуля.
- .loadmod имя — перезагрузить модуль.
- .delmod имя — удалить пользовательский модуль.

Heroku/Hikka совместимость:
- Простые Heroku/Hikka/FTG модули loader.Module поддерживаются через совместимый loader.
- Поддерживаются @loader.command, alias/aliases, методы вида namecmd, utils.answer, utils.get_args_raw, ModuleConfig, client_ready и простые @loader.loop.
- Если модуль нельзя поддержать нативно, GitMD/умная установка переписывает его под BinaryUserbot.
- Inline-боты, сложные callback/inline сценарии, allmodules/security/web Heroku API и отсутствующие сторонние библиотеки могут требовать переписывания.

Профиль:
- .info ответом — информация о пользователе.
- .me — профиль владельца.
- .editme текст — кастомный профиль .me.
- .setpic ссылка — кастомное фото .me.
- .setme — сброс профиля .me.

Медиа и утилиты:
- .скачать ссылка или .скачать 720/1080 ссылка — скачать YouTube.
- .tt ссылка — скачать TikTok.
- .music запрос — найти и прислать аудио.
- .calc выражение — калькулятор и крипто-конвертор.
- .погода город — прогноз погоды.
- .terminal команда — выполнить shell-команду на сервере.

Модерация и режимы:
- .mute/.unmute ответом — удалить сообщения пользователя в чате.
- .bw, .bwchat — фильтр запрещённых слов.
- .ac — AI авто-общение в личке.
- .ебалай, .troll, .стоп, .stopall — режимы автоответа и остановка.
- Антивирус в менеджер-боте — предупреждает об опасных файлах в ЛС и анализирует код .py/.bat.
- .tagwatcher — уведомления о reply/упоминаниях, .tagwatcher pm — авточтение ЛС, .tagwatcher unread — оставить ЛС непрочитанными.

YaMusic:
- Команды .yg/.yguide, .yb/.ybio, .yq/.ysearch, .yn/.ynow, .ynt/.ynowt, .ylike, .yunlike, .ydislike, .ylyrics.
- Для работы нужен OAuth-токен Яндекс.Музыки и библиотека yandex_music.
- .ymtoken TOKEN или .ytoken TOKEN — сохранить OAuth-токен Яндекс.Музыки прямо из юзербота.
- .ymtoken clear — удалить сохранённый токен.
""".strip()

FAQ_DATA = {
    ".help": (
        "📋 <b>.help</b>\n\n"
        "Показывает список команд BinaryUserbot, подсказки по .ub/.sb и ссылку на GitHub."
    ),
    ".faq": (
        "❓ <b>.faq</b>\n\n"
        "<code>.faq</code> — список команд с FAQ\n"
        "<code>.faq .команда</code> — описание конкретной команды\n"
        "<code>.faq вопрос</code> — AI-помощник по базе знаний BinaryUserbot"
    ),
    ".sb": (
        f"{MANAGER_BOT_EMOJI} <b>.sb</b>\n\n"
        "Показывает статус менеджер-бота и инструкции для создания или привязки Telegram-бота к юзерботу."
    ),
    ".sbc": (
        "🤖 <b>.sbc</b>\n\n"
        "Автоматически создаёт менеджер-бота через @BotFather, включает inline-режим, ставит аватар и сохраняет токен."
    ),
    ".sbt": (
        "🔗 <b>.sbt &lt;токен бота&gt;</b>\n\n"
        "Проверяет токен Telegram-бота, запускает менеджер-бота и привязывает его к Binary Userbot."
    ),
    ".restart": (
        "🔄 <b>.restart</b>\n\n"
        "Перезапускает Binary Userbot универсальным способом через текущий Python-процесс."
    ),
    ".gpt": (
        "🐓 <b>.gpt &lt;запрос&gt;</b>\n\n"
        "Отправляет запрос к нейросети GPT-4o-mini через OpenRouter.\n\n"
        "<b>Пример:</b>\n<code>.gpt объясни квантовую запутанность</code>"
    ),
    ".ub": (
        "👾 <b>.ub</b>\n\n"
        "Показывает красивую информацию о BinaryUserbot, проекте, студии и ссылке на GitHub."
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
    ".editme": (
        "✏️ <b>.editme &lt;текст&gt;</b>\n\n"
        "Кастомизация профиля .me с переменными:\n"
        "<code>(ник)</code> — имя\n"
        "<code>(юзернейм)</code> — @username\n"
        "<code>(айди)</code> — ID\n"
        "<code>(год)</code> — год регистрации\n"
        "<code>(чат)</code> — сообщений в чате\n\n"
        "Поддерживает премиум эмодзи и форматирование."
    ),
    ".setme": (
        "🔄 <b>.setme</b>\n\n"
        "Сброс профиля .me к стандартному дизайну.\n"
        "Также сбрасывает кастомное фото."
    ),
    ".setpic": (
        "🖼 <b>.setpic &lt;ссылка&gt;</b>\n\n"
        "Устанавливает кастомное фото для .me.\n\n"
        "<code>.setpic https://example.com/photo.jpg</code>\n"
        "<code>.setme</code> — сброс к стандартному фото"
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
    ".ca": (
        "🧠 <b>.ca</b> <i>(ответом)</i>\n\n"
        "Передаёт нейросети последние 50 сообщений собеседника и делает психологический анализ общения."
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
    ".cqr": (
        "🔳 <b>.cqr &lt;текст или ссылка&gt;</b>\n\n"
        "Создаёт QR-код в стиле CryptoBot и присылает его файлом."
    ),
    ".tagwatcher": (
        "🔔 <b>.tagwatcher</b>\n\n"
        "Уведомляет в лог-чат, когда тебя отмечают reply/mention.\n\n"
        "<code>.tagwatcher</code> — включить/выключить\n"
        "<code>.tagwatcher status</code> — статус\n"
        "<code>.tagwatcher pm</code> — авточтение ЛС\n"
        "<code>.tagwatcher unread</code> — оставлять ЛС непрочитанными"
    ),
    ".md": (
        "🧩 <b>.md</b> <i>(ответом / ссылка / install)</i>\n\n"
        "GitMD: принимает .py файл, код или GitHub/raw ссылку, проверяет совместимость с BinaryUserbot и при необходимости переписывает модуль.\n\n"
        "<code>.md</code> — ответом на файл/код\n"
        "<code>.md install</code> — сразу установить"
    ),
    ".newmd": (
        "🧠 <b>.newmd &lt;промпт&gt;</b>\n\n"
        "Создаёт через AI новый модуль BinaryUserbot по описанию и присылает готовый .py файл с названием, описанием и командой."
    ),
    ".ymtoken": (
        "🎵 <b>.ymtoken &lt;TOKEN&gt;</b>\n\n"
        "Сохраняет OAuth-токен Яндекс.Музыки прямо из юзербота.\n\n"
        "<code>.ymtoken</code> — показать статус\n"
        "<code>.ymtoken TOKEN</code> — сохранить токен\n"
        "<code>.ymtoken clear</code> — удалить токен\n"
        "Алиас: <code>.ytoken</code>"
    ),
    ".ytoken": (
        "🎵 <b>.ytoken &lt;TOKEN&gt;</b>\n\n"
        "Алиас команды <code>.ymtoken</code> для установки OAuth-токена Яндекс.Музыки."
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
    ".server": (
        "🖥 <b>.server</b>\n\n"
        "Полный мониторинг сервера: CPU, RAM, диск, сеть, пинг Telegram и Google, "
        "аптайм, OS, Python."
    ),
    ".tonnel": (
        "🔐 <b>.tonnel &lt;ссылка&gt;</b>\n\n"
        "Безопасный тоннель: открывает сайт через сервер и присылает "
        "скриншот + метаданные (заголовок, описание, статус, размер, сервер) "
        "без посещения сайта с твоей стороны.\n\n"
        "<code>.tonnel https://example.com/very/long/path?x=1</code>"
    ),
    ".telelog": (
        "📊 <b>.telelog &lt;@username / id&gt;</b>\n\n"
        "Funstat: топ чатов пользователя с количеством сообщений. "
        "Можно вызвать ответом на сообщение."
    ),
    ".femboy": (
        "🌟 <b>.femboy</b>\n\n"
        "Включает/выключает femboy-режим: к твоим сообщениям автоматически "
        "добавляются премиум-эмодзи и милые ASCII-лица."
    ),
    ".glban": (
        "🔨 <b>.glban</b> [юзер/реплай] [причина] [время] [-s]\n\n"
        "Глобальный бан во всех чатах, где ты админ с правом ban.\n"
        "Время: <code>30s</code>, <code>5m</code>, <code>2h</code>, <code>1d</code>.\n"
        "<code>-s</code> — тихий режим (без списка чатов).\n\n"
        "<code>.snoser</code> — помощь по всем командам модуля."
    ),
    ".glunban": (
        "🤗 <b>.glunban</b> [юзер/реплай]\n\n"
        "Глобальный разбан во всех чатах, где ты админ."
    ),
    ".glmute": (
        "🔇 <b>.glmute</b> [юзер/реплай] [время] [-s]\n\n"
        "Глобальный мут (запрет писать) во всех чатах, где ты админ."
    ),
    ".glunmute": (
        "🔊 <b>.glunmute</b> [юзер/реплай]\n\n"
        "Снять глобальный мут."
    ),
    ".addbull": (
        "☠️ <b>.addbull</b> <i>(реплай)</i>\n\n"
        "Добавить пользователя в буллинг — на каждое его сообщение бот будет "
        "отвечать случайной матерной фразой."
    ),
    ".rmbull": (
        "💀 <b>.rmbull</b> <i>(реплай или ID)</i>\n\n"
        "Убрать пользователя из списка буллинга."
    ),
    ".clearbull": (
        "🧹 <b>.clearbull</b>\n\n"
        "Очистить весь список жертв буллинга."
    ),
    ".bulla": (
        "✏️ <b>.bulla &lt;фраза&gt;</b>\n\n"
        "Добавить свою фразу в пул унижатора."
    ),
    ".bullr": (
        "🎲 <b>.bullr</b>\n\n"
        "Вкинуть случайное оскорбление в текущий чат."
    ),
    ".trealistic": (
        "🫠 <b>.trealistic</b>\n\n"
        "Переключить реалистичный режим: бот имитирует печатание + задержку "
        "соответствующую длине фразы. Меньше похож на бота."
    ),
    ".bulllist": (
        "📋 <b>.bulllist</b>\n\n"
        "Показать список буллимых пользователей и статистику фраз."
    ),
    ".doxing": (
        "💀 <b>.doxing &lt;@username / ID / +номер&gt;</b> <i>(или реплай)</i>\n\n"
        "Пробив пользователя через Telegram-бота (по умолчанию <code>@StarSHRobot</code>):\n"
        "• ID и история имён/юзернеймов\n"
        "• Телефоны и соцсети\n"
        "• Контактные связи и общие группы\n"
        "• Подарочные связи\n"
        "• Авто-пробив найденного номера (оператор, страна, соцсети)\n\n"
        "⚠️ Требует, чтобы ты был запущен с ботом-пробивом. "
        "Первый запуск: <a href=\"https://t.me/StarSHRobot?start=_ref_J55KZ22H9_X3QAyKjIF\">/start StarSHRobot</a>"
    ),
    ".doxbot": (
        "🤖 <b>.doxbot &lt;@бот&gt;</b>\n\n"
        "Сменить бота, через который идёт пробив.\n"
        "<code>.doxbot @другой_бот</code> — установить\n"
        "<code>.doxbot auto</code> — вернуть StarSHRobot по умолчанию\n"
        "<code>.doxbot</code> — показать текущего"
    ),
    ".doxstatus": (
        "📋 <b>.doxstatus</b>\n\n"
        "Показать, какой бот сейчас используется для пробива."
    ),
}


def get_help_text(force_premium: bool = True) -> str:
    title_emoji = HELP_TITLE_EMOJI if force_premium else pe("gear")
    footer_emoji = HELP_FOOTER_EMOJI if force_premium else pe("star_pe")
    cmds = [
        ".help", ".faq", ".sb", ".sbc", ".sbt", ".restart", ".gpt", ".ub", ".погода", ".цена", ".calc", ".скачать", ".tt",
        ".scam", ".lol", ".info", ".me", ".editme", ".setme", ".setpic",
        ".check",
        ".mute", ".unmute", ".bw",
        ".cat",
        ".ком", ".proxy",
        ".ебалай", ".troll", ".стоп",
        ".ac", ".ca",
        ".note", ".delnote",
        ".lastnews", ".stat",
        ".перевод", ".eng",
        ".terminal",
        ".setting", ".premium", ".stopall", ".logs",
        ".ss", ".max", ".snos",
        ".гороскоп", ".wiki", ".movie", ".tz", ".dict", ".lyr",
        ".music", ".steam", ".metadata", ".afk", ".chat", ".meme",
        ".ip", ".whois", ".history",
        ".md", ".newmd", ".cqr", ".tagwatcher", ".ymtoken", ".ytoken",
        ".bwchat", ".addcom", ".delcom",
        ".server", ".tonnel", ".telelog", ".femboy",
        ".glban", ".glunban", ".glmute", ".glunmute",
        ".addbull", ".rmbull", ".clearbull", ".bulla", ".bullr", ".trealistic", ".bulllist",
        ".doxing", ".doxbot", ".doxstatus",
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
        rows.append("  ".join(chunk))

    cmds_block = "\n".join(rows)

    return (
        f"  {title_emoji} <b>{BOT_NAME} {BOT_VERSION}</b>\n\n"
        f"<blockquote expandable>{cmds_block}</blockquote>\n\n"
        f"{UB_INFO_EMOJI} .ub - о BinaryUserBot\n"
        f"{FAQ_EMOJI} .faq &lt;команда&gt; — подробно о любой команде\n"
        f"{MANAGER_BOT_EMOJI} .sb - управление юзерботом с помощью вашего Telegram бота.\n"
        f"----\n"
        f"{CHECK_EMOJI} Авто-мониторинг личных чатов.\n\n"
        f"{GIT} GitHub: <a href=\"https://github.com/binary166/BinaryUserbot\">binary166/BinaryUserbot</a>\n\n"
        f"<i>by @burgerbeats {footer_emoji}</i>"
    )


def cmd_setting() -> str:
    ebalaj_count = len(state.ebalaj_active)
    troll_count  = len(state.troll_active)
    ac_count     = sum(1 for v in state.ac_active.values() if v)
    muted_count  = sum(len(v) for v in state.muted_users.values())
    logs_label   = "Избранное" if state.logs_chat_id == MY_ID else str(state.logs_chat_id)

    header_bolt = pe("gear")
    bw_tag = pe("shield")
    mute_ico = "🔇"
    log_ico = "📋"

    auto_comment_channels = settings.get("auto_comment_channels", {})
    bw_chat = state.bw_chat_id or settings.get("bw_chat_id", "не задан")

    if auto_comment_channels:
        ch_lines = "\n".join(
            f"  <code>{ch_id}</code> → <code>{disc_id}</code>"
            for ch_id, disc_id in list(auto_comment_channels.items())[:5]
        )
        if len(auto_comment_channels) > 5:
            ch_lines += f"\n  … ещё {len(auto_comment_channels) - 5}"
    else:
        ch_lines = "  <i>нет каналов</i>"

    custom_me = "✅" if settings.get("custom_me_text") else "❌"
    custom_pic = "✅" if settings.get("custom_me_pic") else "❌"
    custom_ebalaj = "✅" if (settings.get("ebalaj_system_prompt") or EBALAJ_SYSTEM) != EBALAJ_SYSTEM else "❌"
    custom_troll = "✅" if (settings.get("troll_system_prompt") or TROLL_SYSTEM) != TROLL_SYSTEM else "❌"

    lines = [
        f"{header_bolt} <b>{BOT_NAME} {BOT_VERSION}</b> — настройки",
        "",
        "- <b>Режимы</b> -",
        f"{toggle_pe(state.eng_mode_active)}  ENG автоперевод",
        f"{status_pe(bool(state.auto_comment_text))}  Авто-комментирование",
        f"{status_pe(ebalaj_count > 0)}  Ебалай  ({ebalaj_count} чатов)",
        f"{status_pe(troll_count > 0)}  Troll  ({troll_count} чатов)",
        f"{status_pe(ac_count > 0)}  Auto-Chat  ({ac_count} чатов)",
        f"{status_pe(bool(settings.get('antivirus_enabled', False)))}  Антивирус",
        f"🤪 Ебалай промпт: {custom_ebalaj}",
        f"😡 Troll промпт: {custom_troll}",
        "",
        "- <b>Авто-комментирование</b> -",
        f"📡 Каналов: <b>{len(auto_comment_channels)}</b>",
        f"<blockquote>{ch_lines}</blockquote>",
        "<code>.addcom ID DISC_ID</code>  <code>.delcom ID</code>",
        "",
        "- <b>Фильтры</b> -",
        f"♾️ Bad Words: <code>{len(state.bw_words)}</code> слов",
        f"🔒 Чат модерации: <code>{bw_chat}</code>",
        f"<code>.bwchat @чат</code> — сменить",
        f"{mute_ico}  Замьючено: <code>{muted_count}</code> польз.",
        "",
        "- <b>Профиль .me</b> -",
        f"✏️ Кастомный текст: {custom_me}",
        f"🖼 Кастомное фото: {custom_pic}",
        "<code>.editme</code> / <code>.setme</code> / <code>.setpic</code>",
        "",
        "- <b>Логи</b> -",
        f"{log_ico}  Чат: <code>{logs_label}</code>",
        "<code>.logs me</code>  |  <code>.logs @чат</code>",
        "",
        "- <b>Интерфейс</b> -",
        f"{toggle_pe(state.premium_emoji_active)}  Премиум эмодзи",
        "<code>.premium</code> — переключить",
        "",
        f"<i>{BOT_NAME} {BOT_VERSION}</i>  {by_line()}",
    ]
    return "\n".join(lines)
