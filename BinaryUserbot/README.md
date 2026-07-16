# Binary Userbot v2.0

Binary Userbot — Telegram userbot на Telethon с модульной системой, premium emoji, менеджер-ботом, AI-командами, заметками, погодой, скачиванием видео, настройками через Telegram и быстрым рестартом.

## Быстрые ссылки на установку

- [Инструкция для Linux / VPS](#linux--vps)
- [Инструкция для macOS](#macos)
- [Инструкция для Windows](#windows)

## Оглавление

- [Что нового в 2.0](#что-нового-в-20)
- [Требования](#требования)
- [Linux / VPS](#linux--vps)
- [macOS](#macos)
- [Windows](#windows)
- [Настройка в терминале](#настройка-в-терминале)
- [Первый запуск](#первый-запуск)
- [Менеджер-бот](#менеджер-бот)
- [Обновление и быстрый рестарт](#обновление-и-быстрый-рестарт)
- [Безопасность](#безопасность)

## Что нового в 2.0

- Приватные данные вынесены из `config.py` в локальный `config.local.json`.
- Добавлен мастер настройки `setup_config.py`: пользователь заполняет конфиг прямо в терминале.
- `FUNSTAT_TOKEN` и ban words не спрашиваются при установке. Их можно включить позже командами `.funstat`, `.bw` и `.bwchat`.
- При первом запуске `logs_chat_id` берётся из `MY_ID`, а ban words по умолчанию пустые.
- Inline-ответы менеджер-бота сначала отправляют HTML с premium emoji, обычный текст используется только как fallback.
- `.restart` перезапускает процесс через `os.execv` с короткой задержкой.
- Updater сохраняет `config.local.json`, сессии, `settings.json`, `notes.json` и пользовательские модули.

## Требования

- Python 3.10 или новее.
- Git.
- ffmpeg для скачивания и обработки медиа.
- Telegram `API_ID` и `API_HASH` с https://my.telegram.org/apps.
- Telegram user ID владельца. Его можно узнать у `@userinfobot`.

## Linux / VPS

Подходит для Ubuntu/Debian и большинства чистых VPS.

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv ffmpeg

git clone https://github.com/binary166/BinaryUserbot.git
cd BinaryUserbot/BinaryUserbot

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
pip install -r requirements.txt

python setup_config.py
python main.py
```

Если сервер должен работать постоянно, после первого успешного запуска используйте systemd из раздела [Обновление и быстрый рестарт](#обновление-и-быстрый-рестарт).

## macOS

Установите Homebrew, если его ещё нет:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Затем установите зависимости и запустите userbot:

```bash
brew install git python ffmpeg

git clone https://github.com/binary166/BinaryUserbot.git
cd BinaryUserbot/BinaryUserbot

python3 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
pip install -r requirements.txt

python setup_config.py
python main.py
```

Если macOS просит разрешение на сетевые подключения Python, разрешите его.

## Windows

Откройте PowerShell от обычного пользователя и установите зависимости:

```powershell
winget install Python.Python.3.12 Git.Git Gyan.FFmpeg
```

Закройте PowerShell, откройте заново и выполните:

```powershell
git clone https://github.com/binary166/BinaryUserbot.git
cd BinaryUserbot\BinaryUserbot

py -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install -r requirements.txt

python setup_config.py
python main.py
```

Если PowerShell не даёт активировать окружение:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

## Настройка в терминале

Запустите мастер:

```bash
python setup_config.py
```

Он создаст `config.local.json`. Это приватный файл, его нельзя публиковать.

| Поле | Что вводить |
| --- | --- |
| `API_ID` | Числовой Telegram API ID с https://my.telegram.org/apps |
| `API_HASH` | Telegram API hash с той же страницы |
| `PHONE` | Номер аккаунта в международном формате, например `+79991234567` |
| `PASSWORD_2FA` | Пароль двухфакторной защиты Telegram, если она включена |
| `MY_ID` | Ваш Telegram user ID |
| `CREATOR_ID` | ID создателя в `.info`; обычно такой же, как `MY_ID` |
| `SESSION_NAME` | Имя файла сессии, обычно `binaryuserbot_session` |
| `OR_TOKEN` | OpenRouter token для AI-команд, можно оставить пустым |
| `OR_MODEL` | Модель OpenRouter, например `openai/gpt-4o-mini` |
| `NEWS_CHANNEL` | ID канала новостей, если нужен AI-дайджест |
| `SCAM_CHANNEL` | Username базы скама, по умолчанию `GID_ScamBase` |
| `WALLET_SEED` | TON seed-фраза, только если нужен crypto-модуль |
| `CHANNEL_TO_CHAT` | пары `канал:чат` через запятую для автокомментариев |
| `STARS_*` | настройки Stars AutoPay, если используете этот модуль |

Если ошиблись, запустите `python setup_config.py` ещё раз. Текущие значения можно оставить Enter-ом.

## Первый запуск

```bash
python main.py
```

При первом запуске Telethon попросит код входа Telegram. После успешной авторизации появится `.runtime/` с локальной сессией. Эту папку нельзя публиковать.

## Менеджер-бот

После запуска напишите в Telegram:

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

Команда `.restart` перезапускает процесс через `os.execv`, поэтому рестарт обычно занимает меньше секунды.

Пример systemd для VPS:

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

Команды для systemd:

```bash
sudo systemctl daemon-reload
sudo systemctl enable roll.service
sudo systemctl restart roll.service
sudo journalctl -u roll.service -f
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
