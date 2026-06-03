Вот более минималистичная версия README:

```md
# Binary Userbot v1.6

Telegram userbot на Python/Telethon с командами для AI, заметок, скачивания медиа, модерации, автокомментариев и пользовательских модулей.

## Возможности

- AI-команды через OpenRouter
- погода, курсы валют и крипты, новости
- заметки, калькулятор, скачивание YouTube/TikTok
- муты, фильтр слов, проверка по скам-базе
- автоответы и авто-комментарии
- установка своих `.py` модулей прямо из Telegram

## Что нужно

- Python 3.10+
- Git
- ffmpeg
- Telegram `API_ID` и `API_HASH`
- OpenRouter token, если нужны AI-функции

## Получение ключей

### Telegram API

1. Откройте [my.telegram.org](https://my.telegram.org)
2. Авторизуйтесь по номеру телефона
3. Перейдите в `API development tools`
4. Создайте приложение
5. Скопируйте `api_id` и `api_hash`

### OpenRouter

1. Зарегистрируйтесь на [openrouter.ai](https://openrouter.ai)
2. Откройте `Settings -> API Keys`
3. Создайте ключ и скопируйте его

Без OpenRouter не будут работать команды `.gpt`, `.lol`, `.ac`, `.ебалай`, `.troll` и AI-описание погоды.

### Telegram ID

Напишите [@userinfobot](https://t.me/userinfobot), чтобы получить свой числовой Telegram ID.

## Установка

### Linux / VPS

```bash
sudo apt update
sudo apt install -y git python3 python3-pip python3-venv ffmpeg

git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot/BinaryUserBot

python3 -m venv .venv
source .venv/bin/activate

pip install telethon aiohttp yt-dlp
nano config.py

python3 main.py
```

### Windows

Установите:

- [Python](https://www.python.org/downloads/) с галочкой `Add Python to PATH`
- [Git](https://git-scm.com/download/win)
- [ffmpeg](https://ffmpeg.org/download.html), если нужно скачивание видео

```cmd
git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot\BinaryUserBot

python -m venv .venv
.venv\Scripts\activate

pip install telethon aiohttp yt-dlp
notepad config.py

python main.py
```

### Termux

```bash
pkg update && pkg upgrade -y
pkg install -y git python python-pip ffmpeg

git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot/BinaryUserBot

pip install telethon aiohttp yt-dlp
nano config.py

python main.py
```

На Android бот работает только пока открыт Termux. Для постоянной работы лучше использовать VPS.

## Настройка

Откройте `config.py` и заполните поля:

```python
API_ID       = 12345678
API_HASH     = "abcdef123456"
PHONE        = "+79001234567"
PASSWORD_2FA = ""

MY_ID        = 123456789

OR_TOKEN     = "sk-or-v1-..."
```

`PASSWORD_2FA` можно оставить пустым, если двухфакторная авторизация не включена.

## Запуск

```bash
source .venv/bin/activate
python3 main.py
```

На Windows:

```cmd
.venv\Scripts\activate
python main.py
```

При первом запуске Telegram попросит код входа. Если включена 2FA, понадобится пароль.

После входа можно написать `.help` в любом чате.

## Автозапуск на VPS

Пример через `systemd`:

```bash
sudo nano /etc/systemd/system/binarybot.service
```

```ini
[Unit]
Description=Binary Userbot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/BinaryUserBot/BinaryUserBot
ExecStart=/root/BinaryUserBot/BinaryUserBot/.venv/bin/python3 main.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable binarybot
sudo systemctl start binarybot
sudo systemctl status binarybot
```

Логи:

```bash
sudo journalctl -u binarybot -f
```

## Основные команды

### AI

| Команда | Описание |
|---|---|
| `.gpt <запрос>` | ответ от GPT |
| `.ac` | автоответы в личных чатах |
| `.ебалай` | AI-персонаж отвечает вместо вас |
| `.troll` | режим агрессивных автоответов |
| `.eng` | автоперевод исходящих сообщений на английский |
| `.перевод <текст>` | перевод текста на английский |

### Информация

| Команда | Описание |
|---|---|
| `.погода <город>` | погода |
| `.цена` | курсы BTC, TON, ETH, USD, EUR, CNY |
| `.calc <выражение>` | калькулятор |
| `.lastnews` | дайджест новостей |

### Пользователи

| Команда | Описание |
|---|---|
| `.info` | информация о пользователе |
| `.me` | ваш профиль |
| `.scam` | проверка по скам-базе |
| `.lol` | шутка про пользователя |
| `.check` | проверка Binary Userbot |
| `.ss` | подкат к пользователю |

### Модерация

| Команда | Описание |
|---|---|
| `.mute` | замьютить пользователя |
| `.unmute` | размьютить пользователя |
| `.bw <слово>` | добавить слово в фильтр |
| `.bw список` | список запрещенных слов |
| `.bw очистить` | очистить фильтр |

### Медиа

| Команда | Описание |
|---|---|
| `.скачать <ссылка>` | скачать видео с YouTube |
| `.скачать 1080 <ссылка>` | скачать YouTube в 1080p |
| `.tt <ссылка>` | скачать видео из TikTok |

### Утилиты

| Команда | Описание |
|---|---|
| `.note <текст>` | добавить заметку |
| `.note` | показать заметки |
| `.delnote` | удалить заметки |
| `.proxy` | список MTProto-прокси |
| `.stat` | статистика диалогов |
| `.terminal <команда>` | выполнить команду на сервере |

### Настройки

| Команда | Описание |
|---|---|
| `.setting` | настройки и активные режимы |
| `.premium` | premium emoji |
| `.logs <@чат>` | чат для логов |
| `.stopall` | остановить все режимы |
| `.стоп` | остановить режим в текущем чате |
| `.help` | список команд |
| `.faq <команда>` | справка по команде |

## Модули

Userbot умеет ставить пользовательские `.py` модули.

1. Отправьте файл модуля в Telegram
2. Ответьте на него командой `.md`
3. Модуль установится и появится в списке `.modules`

Удаление:

```text
.delmod <команда>
```

Пример модуля:

```python
# MODULE_NAME = "Hello"
# MODULE_CMD  = ".hello"
# MODULE_DESC = "Приветствие"

from telethon import events
from bot_client import client

@client.on(events.NewMessage(outgoing=True, pattern=r'\.hello$'))
async def hello_handler(event):
    await event.message.edit("Привет")
```

Не ставьте модули из неизвестных источников. Модуль выполняется как обычный Python-код и имеет доступ к аккаунту.

## Структура

```text
BinaryUserBot/
├── main.py
├── config.py
├── settings.json
├── notes.json
├── bot_client.py
├── module_loader.py
├── ai.py
├── weather.py
├── prices.py
├── calc.py
├── downloader.py
├── notes.py
├── news.py
├── handlers/
└── modules/
```

## Частые проблемы

### ModuleNotFoundError

```bash
source .venv/bin/activate
pip install telethon aiohttp yt-dlp
```

### FloodWaitError

Telegram временно ограничил активность. Подождите указанное время и запустите снова.

### Не работают AI-команды

Проверьте `OR_TOKEN` в `config.py` и баланс OpenRouter.

### Не скачивается видео

Установите `ffmpeg` и убедитесь, что он доступен из консоли.

### Как обновить

```bash
cd BinaryUserBot/BinaryUserBot
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
python3 main.py
```

## Ссылки

- Чат и модули: [t.me/+f6-E3zFi8KQyOTg0](https://t.me/+f6-E3zFi8KQyOTg0)
- Поддержка: [@burgerbeats](https://t.me/burgerbeats)
- Telegram API: [my.telegram.org](https://my.telegram.org)
- OpenRouter: [openrouter.ai](https://openrouter.ai)
- Новости: [@binary_news](https://t.me/binary_news)
- Скам-база: [@GID_ScamBase](https://t.me/GID_ScamBase)

Для `.scam` и `.lastnews` нужна подписка на соответствующие каналы.

## Дисклеймер

Проект предназначен для личного и образовательного использования.

Не используйте userbot для спама, мошенничества или действий, нарушающих правила Telegram. Автор не отвечает за блокировки аккаунтов и другие последствия использования.

Никому не передавайте `API_ID`, `API_HASH`, `OR_TOKEN` и файлы `*.session`.
```
