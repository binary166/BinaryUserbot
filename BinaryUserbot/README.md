# Binary Userbot v2.0

Binary Userbot — Telegram userbot на Telethon с модульной системой, premium emoji в HTML-сообщениях, менеджер-ботом, AI-командами, заметками, погодой, скачиванием видео, настройками через Telegram и быстрым рестартом.

## Что нового в 2.0

- Приватные данные вынесены из `config.py` в локальный `config.local.json`.
- Добавлен мастер настройки `setup_config.py`: пользователь заполняет конфиг прямо в терминале.
- README переписан под актуальную установку без ручного редактирования Python-файлов.
- Inline-ответы менеджер-бота сначала отправляют HTML с premium emoji, а обычный текст используется только как fallback.
- Быстрый `.restart` работает через `os.execv` с короткой задержкой, без долгого ожидания systemd.
- Updater сохраняет `config.local.json`, сессии, `settings.json`, `notes.json` и пользовательские модули.

## Быстрый старт

```bash
git clone https://github.com/binary166/BinaryUserbot.git
cd BinaryUserbot

python -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
pip install -r requirements.txt

python setup_config.py
python main.py
```

На Windows активация окружения:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup_config.py
python main.py
```

## Настройка в терминале

Запустите:

```bash
python setup_config.py
```

Мастер сам создаст `config.local.json`. Этот файл содержит личные значения и не должен попадать в GitHub.

| Поле | Что вводить |
| --- | --- |
| `API_ID` | Числовой Telegram API ID с https://my.telegram.org/apps |
| `API_HASH` | Telegram API hash с той же страницы |
| `PHONE` | Номер аккаунта в международном формате, например `+79991234567` |
| `PASSWORD_2FA` | Пароль двухфакторной защиты Telegram, если она включена |
| `MY_ID` | Ваш Telegram user ID. Его можно узнать у `@userinfobot` |
| `CREATOR_ID` | ID создателя в карточке `.info`; обычно такой же, как `MY_ID` |
| `SESSION_NAME` | Имя файла сессии. Обычно оставляйте `binaryuserbot_session` |
| `OR_TOKEN` | OpenRouter token для AI-команд. Можно оставить пустым |
| `OR_MODEL` | Модель OpenRouter, например `openai/gpt-4o-mini` |
| `NEWS_CHANNEL` | ID канала новостей, если используете AI-дайджест |
| `SCAM_CHANNEL` | Username базы скама, по умолчанию `GID_ScamBase` |
| `WALLET_SEED` | TON seed-фраза, нужна только для crypto-модуля |
| `CHANNEL_TO_CHAT` | пары `канал:чат` через запятую для автокомментариев |
| `STARS_*` | настройки Stars AutoPay, если используете этот модуль |

Если ошиблись, просто запустите `python setup_config.py` ещё раз: текущие значения будут показаны и их можно оставить Enter-ом.

## Первый запуск

```bash
python main.py
```

При первом запуске Telethon попросит код входа Telegram. После успешной авторизации появится `.runtime/` с локальной сессией. Эту папку нельзя публиковать.

## Менеджер-бот

После запуска в Telegram:

```text
.sb
```

Команда привязывает менеджер-бота. Дальше доступны панель, OpenRouter-настройки, терминал, выгрузка чатов, проверка обновлений и быстрый рестарт.

Полезные команды:

```text
.help
.setting
.restart
.ub
.sbc
.sbt <token>
.funstat <token>
.bw <слово>
.bwchat <чат>
```

FunStat token и ban words не запрашиваются при установке. Их можно включить позже командами `.funstat`, `.bw` и `.bwchat`.

## Обновление и быстрый рестарт

Встроенный updater берёт код из GitHub и не трогает приватные файлы:

- `config.local.json`
- `settings.json`
- `notes.json`
- `.runtime/`
- `*.session*`
- папку `modules/`

Команда `.restart` перезапускает процесс через `os.execv`, поэтому рестарт обычно занимает меньше секунды. Для сервера рекомендуется systemd с коротким `RestartSec`:

```ini
[Unit]
Description=Binary Userbot
After=network-online.target

[Service]
WorkingDirectory=/root/roll
ExecStart=/root/bots-venv/bin/python /root/roll/main.py
Restart=always
RestartSec=1
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

## Безопасность

Не публикуйте:

- `config.local.json`
- `.runtime/`
- `*.session`, `*.session-journal`, `*.session-wal`, `*.session-shm`
- `settings.json`
- `notes.json`
- `.env`

В репозитории лежит только безопасный `config.py` и пример `config.example.json`.
