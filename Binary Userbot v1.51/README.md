# Binary Userbot v1.4

## Структура модулей

```
binarybot/
│
├── main.py                   # Точка входа — запускать именно его
│
├── config.py                 # Все константы и настройки (API ключи, ID чатов, тексты систем)
├── state.py                  # Глобальные переменные состояния (режимы, сессии, флаги)
├── bot\_client.py             # Единственный экземпляр TelegramClient
│
├── premium\_emoji.py          # Таблица PE\_TABLE, функции pe(), by\_line(), toggle\_pe()
├── utils.py                  # html(), get\_username(), send\_me(), resolve\_sender()
│
├── ai.py                     # Запросы к OpenRouter: or\_request(), or\_chat()
├── weather.py                # Погода через Open-Meteo + wttr.in
├── prices.py                 # Курсы крипты/фиата + крипто-конвертор .calc
├── calc.py                   # Безопасный математический eval
├── downloader.py             # Скачивание YouTube и TikTok через yt-dlp
├── notes.py                  # Заметки: load\_notes() / save\_notes() → notes.json
├── news.py                   # AI-дайджест новостей из @binary\_news
│
├── user\_info.py              # .info, .me, .stat — профили и статистика
├── scam.py                   # .scam (проверка по GID\_ScamBase) и .lol
├── stars.py                  # Stars AutoPay: мониторинг + оплата инвойсов
├── autochat.py               # .ac — авто-общение в стиле хозяина
├── ebalaj.py                 # .ебалай (тупой Вася) и .troll (агрессор)
├── prank.py                  # .snos — шуточная анимация-розыгрыш
├── animations.py             # Кадры .cat / .rocket / .fight + run\_animation()
├── help\_faq.py               # Тексты .help, .faq, .setting
│
└── handlers/
    ├── \_\_init\_\_.py
    ├── bw\_handler.py         # Фильтр запрещённых слов (NewMessage в BW\_CHAT\_ID)
    ├── channel\_handler.py    # Авто-комментирование (NewMessage в AUTO\_COMMENT\_CHANNELS)
    ├── edit\_delete\_handler.py# Логи изменений/удалений + Stars edit
    └── commands.py           # Главный обработчик всех команд (on\_new\_message)
```

## Установка и запуск

```bash
pip install telethon aiohttp yt-dlp
python main.py
```

## 

