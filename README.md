# 👾 Binary Userbot `v1.51`

> Удобный Telegram Userbot с AI-функциями, приятным интерфейсом и расширяемой системой модулей.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://python.org)
[![Telethon](https://img.shields.io/badge/Telethon-latest-blue?style=flat-square)](https://github.com/LonamiWebs/Telethon)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📋 Содержание

- [Возможности](#-возможности)
- [Перед установкой — получение ключей](#-перед-установкой--получение-ключей)
- [Установка](#-установка)
  - [Ubuntu / Debian](#ubuntu--debian)
  - [CentOS / Fedora / RHEL](#centos--fedora--rhel)
  - [macOS](#macos)
  - [Windows 10/11](#windows-1011)
  - [Android (Termux)](#android-termux)
- [Настройка config.py](#-настройка-configpy)
- [Запуск](#-запуск)
- [Автозапуск на сервере (VPS)](#-автозапуск-на-сервере-vps)
- [Команды](#-команды)
- [Система модулей](#-система-модулей)
- [Структура проекта](#-структура-проекта)
- [Частые вопросы](#-частые-вопросы)
- [Дисклеймер](#%EF%B8%8F-дисклеймер)

---

## ✨ Возможности

| Категория | Функции |
|-----------|---------|
| 🤖 **AI** | GPT-4o через OpenRouter, авто-перевод, стендап-шутки, автообщение |
| 🌍 **Информация** | Погода, курсы крипты/фиата, новостной дайджест |
| 🔍 **Безопасность** | Проверка по базе скамеров, мут пользователей, фильтр слов |
| 📝 **Утилиты** | Заметки, калькулятор, скачивание видео с YouTube/TikTok |
| ⭐ **Telegram** | Stars AutoPay, авто-комментирование каналов, профили пользователей |
| 🎭 **Развлечения** | Анимации, режим троллинга, розыгрыши |
| 🧩 **Модули** | Динамическая загрузка .py модулей прямо из Telegram |

---

## 🔑 Перед установкой — получение ключей

Прежде чем начинать установку, нужно получить три ключа.

### 1. Telegram API ID и API Hash

1. Войдите на сайт [my.telegram.org](https://my.telegram.org)
2. Авторизуйтесь своим номером телефона
3. Перейдите в раздел **API development tools**
4. Создайте приложение (название и описание — любые)
5. Скопируйте `App api_id` и `App api_hash`

> ⚠️ Это данные вашего **личного аккаунта**. Никому не передавайте!

### 2. OpenRouter API Token (для AI-функций)

1. Зарегистрируйтесь на [openrouter.ai](https://openrouter.ai)
2. Перейдите в **Settings → API Keys**
3. Нажмите **Create Key**, скопируйте токен
4. 
> 💡 Без токена работают все функции **кроме** `.gpt`, `.погода` (описание), `.lol`, `.ac`, `.ебалай`, `.troll`

### 3. Ваш Telegram User ID

1. Напишите боту [@userinfobot](https://t.me/userinfobot) в Telegram
2. Он ответит вашим числовым ID (например, `750545571`)

---

## 🛠 Установка

> ⚠️ Рекомендуется устанавливать в `/root` на сервере или в домашнюю папку на ПК.

### Ubuntu / Debian

```bash
# 1. Обновляем систему и ставим зависимости
sudo apt update && sudo apt install -y git python3 python3-pip python3-venv ffmpeg

# 2. Клонируем репозиторий
git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot

# 3. Создаём виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 4. Устанавливаем библиотеки
pip install telethon aiohttp yt-dlp

# 5. Настраиваем конфиг (смотри раздел ниже)
nano config.py

# 6. Запускаем
python3 main.py
```

---

### CentOS / Fedora / RHEL

```bash
# 1. Устанавливаем зависимости
sudo dnf install -y git python3 python3-pip ffmpeg   # Fedora / RHEL 9+
# или для CentOS 7/8:
sudo yum install -y git python3 python3-pip

# 2. Клонируем репозиторий
git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot

# 3. Виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 4. Устанавливаем библиотеки
pip install telethon aiohttp yt-dlp

# 5. Настраиваем конфиг
nano config.py

# 6. Запускаем
python3 main.py
```

---

### macOS

```bash
# 1. Устанавливаем Homebrew (если нет)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Устанавливаем Python и ffmpeg
brew install python ffmpeg git

# 3. Клонируем репозиторий
git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot

# 4. Виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 5. Устанавливаем библиотеки
pip install telethon aiohttp yt-dlp

# 6. Настраиваем конфиг
open -e config.py   # откроет TextEdit, или используйте nano/vim

# 7. Запускаем
python3 main.py
```

---

### Windows 10/11

#### Шаг 1 — Python

1. Скачайте Python 3.11+ с официального сайта: [python.org/downloads](https://www.python.org/downloads/)
2. При установке **обязательно** поставьте галочку **"Add Python to PATH"**
3. Нажмите "Install Now"

#### Шаг 2 — Git (для клонирования)

Скачайте и установите с [git-scm.com](https://git-scm.com/download/win).

Или просто скачайте ZIP с GitHub и распакуйте вручную.

#### Шаг 3 — Установка бота

Откройте **командную строку** (`Win + R` → `cmd`) и выполните:

```cmd
cd C:\Users\%USERNAME%\Desktop

git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot

python -m venv .venv
.venv\Scripts\activate

pip install telethon aiohttp yt-dlp
```

#### Шаг 4 — Настройка и запуск

```cmd
notepad config.py
```

Заполните все поля, сохраните файл, затем:

```cmd
python main.py
```

> 💡 Для скачивания видео на Windows дополнительно установите [ffmpeg](https://ffmpeg.org/download.html) и добавьте в PATH.

---

### Android (Termux)

```bash
# 1. Установите Termux из F-Droid (не из Play Market!)
# https://f-droid.org/packages/com.termux/

# 2. Обновляем пакеты
pkg update && pkg upgrade -y

# 3. Устанавливаем зависимости
pkg install -y git python python-pip ffmpeg

# 4. Клонируем
git clone https://github.com/binary166/BinaryUserBot
cd BinaryUserBot

# 5. Устанавливаем библиотеки
pip install telethon aiohttp yt-dlp

# 6. Настройка
nano config.py

# 7. Запускаем
python main.py
```

> ⚠️ На Android бот работает только пока Termux открыт. Для постоянной работы используйте VPS.

---

## ⚙️ Настройка `config.py`

Откройте файл `config.py` и заполните следующие поля:

```python
# ─── ОБЯЗАТЕЛЬНО ──────────────────────────────────────────────────────────────

API_ID       = 12345678          # Ваш API ID с my.telegram.org
API_HASH     = "abcdef123456"    # Ваш API Hash с my.telegram.org
PHONE        = "+79001234567"    # Ваш номер телефона (с + и кодом страны)
PASSWORD_2FA = "ваш_пароль"      # Пароль двухфакторной аутентификации (если есть, иначе "")

MY_ID        = 123456789         # Ваш числовой Telegram ID (@userinfobot)

# ─── ДЛЯ AI-ФУНКЦИЙ ───────────────────────────────────────────────────────────

OR_TOKEN     = "sk-or-v1-..."    # Токен OpenRouter (openrouter.ai)
```

> ✅ После заполнения `config.py` бот готов к первому запуску.

---

## 🚀 Запуск

```bash
# Активируем окружение (если ещё не активировано)
source .venv/bin/activate   # Linux/macOS
# или
.venv\Scripts\activate      # Windows

# Запускаем бота
python3 main.py
```

При первом запуске Telegram попросит:
1. Подтвердить вход кодом из приложения
2. Ввести пароль 2FA (если установлен)

После успешного входа в ваши **Избранные сообщения** придёт приветственное сообщение от бота. Напишите `.help` в любом чате, чтобы увидеть список команд.

---

## 🖥 Автозапуск на сервере (VPS)

Чтобы бот работал постоянно — даже после перезагрузки сервера — настройте systemd-сервис.

### Через systemd (рекомендуется)

```bash
# 1. Узнаём полный путь к Python в виртуальном окружении
which python3   # или: /root/BinaryUserBot/.venv/bin/python3

# 2. Создаём файл сервиса
sudo nano /etc/systemd/system/binarybot.service
```

Вставьте содержимое (замените пути на свои):

```ini
[Unit]
Description=Binary Userbot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/BinaryUserBot
ExecStart=/root/BinaryUserBot/.venv/bin/python3 main.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# 3. Активируем и запускаем
sudo systemctl daemon-reload
sudo systemctl enable binarybot
sudo systemctl start binarybot

# 4. Проверяем статус
sudo systemctl status binarybot

# Просмотр логов в реальном времени
sudo journalctl -u binarybot -f
```

### Через screen (более простой способ)

```bash
# Устанавливаем screen
sudo apt install screen -y

# Создаём сессию
screen -S binarybot

# Запускаем бота внутри сессии
source .venv/bin/activate
python3 main.py

# Выходим из сессии без остановки (Ctrl+A, затем D)
# Вернуться к логам:
screen -r binarybot
```

### Через pm2 (Node.js менеджер процессов)

```bash
# Устанавливаем pm2
npm install -g pm2

# Запускаем
pm2 start "python3 main.py" --name binarybot --cwd /root/BinaryUserBot

# Автозапуск после перезагрузки
pm2 startup
pm2 save
```

---

## 📌 Команды

### 🤖 Нейросеть и AI

| Команда | Описание |
|---------|----------|
| `.gpt <запрос>` | Ответ GPT-4o-mini на любой вопрос |
| `.ac` | Авто-общение в твоём стиле в личных чатах |
| `.ебалай` | ИИ-персонаж «тупой Вася» отвечает вместо тебя |
| `.troll` | Агрессивный ИИ-тролль в личных чатах |
| `.eng` | Автоперевод всех исходящих на английский |
| `.перевод <текст>` | Перевести текст на английский |

### 🌍 Информация

| Команда | Описание |
|---------|----------|
| `.погода <город>` | Погода с красивой карточкой |
| `.цена` | Курсы BTC, TON, ETH, USD, EUR, CNY |
| `.calc <выражение>` | Калькулятор + крипто-конвертор |
| `.lastnews` | AI-дайджест новостей за 24 часа |

### 👤 Пользователи

| Команда | Описание |
|---------|----------|
| `.info` | Профиль пользователя (ответом) |
| `.me` | Твой профиль с фото |
| `.scam` | Проверить по базе скамеров (ответом) |
| `.lol` | Шутка про пользователя от ИИ (ответом) |
| `.check` | Проверить наличие Binary Userbot (ответом) |
| `.ss` | Дерзко подкатить к пользователю (ответом) |

### 🔒 Модерация

| Команда | Описание |
|---------|----------|
| `.mute` | Замьютить пользователя (ответом) |
| `.unmute` | Размьютить пользователя (ответом) |
| `.bw <слово>` | Добавить слово в фильтр чата |
| `.bw список` | Показать все запрещённые слова |
| `.bw очистить` | Очистить список слов |

### 📥 Медиа

| Команда | Описание |
|---------|----------|
| `.скачать <ссылка>` | Скачать видео с YouTube (720p) |
| `.скачать 1080 <ссылка>` | Скачать видео с YouTube (1080p) |
| `.tt <ссылка>` | Скачать видео из TikTok |

### 📝 Заметки и утилиты

| Команда | Описание |
|---------|----------|
| `.note <текст>` | Добавить заметку |
| `.note` | Показать все заметки |
| `.delnote` | Удалить все заметки |
| `.proxy` | Список бесплатных MTProto-прокси |
| `.stat` | Статистика диалогов аккаунта |
| `.terminal <команда>` | Выполнить команду на сервере |

### 🎭 Развлечения

| Команда | Описание |
|---------|----------|
| `.cat` | Анимация с котом |
| `.rocket` | Анимация ракеты |
| `.fight` | Покемон-битва |
| `.snos` | Розыгрыш с прогресс-баром |

### Авто-комментирование

| Команда | Описание |
|---------|----------|
| `.ком <текст>` | Авто-комментирование постов в каналах |

### ⚙️ Настройки

| Команда | Описание |
|---------|----------|
| `.setting` | Панель всех настроек и активных режимов |
| `.premium` | Включить/выключить премиум эмодзи |
| `.logs <@чат>` | Сменить чат для логов |
| `.stopall` | Остановить все активные режимы |
| `.стоп` | Остановить активный режим в текущем чате |
| `.help` | Список всех команд |
| `.faq <команда>` | Подробная справка по команде |

### 🧩 Модули

| Команда | Описание |
|---------|----------|
| `.md` | Установить модуль (ответом на .py файл) |
| `.modules` | Список установленных модулей |
| `.delmod <команда>` | Удалить установленный модуль |

---

## 🧩 Система модулей

Binary Userbot поддерживает динамическую загрузку модулей прямо из Telegram — не нужно трогать сервер!

### Установка модуля

1. Найдите или создайте `.py` файл с модулем
2. Отправьте файл в любой чат
3. Ответьте на это сообщение командой `.md`
4. Модуль установится и сразу заработает

### Официальные модули

Ищите готовые модули в официальном чате: **[t.me/+f6-E3zFi8KQyOTg0](https://t.me/+f6-E3zFi8KQyOTg0)**

> ❌ **Не устанавливайте модули из незнакомых источников!** Модуль — это Python-код, который выполняется с полным доступом к вашему аккаунту.

### Создание своего модуля

```python
# MODULE_NAME = "Моя команда"
# MODULE_CMD  = ".hello"
# MODULE_DESC = "Приветствует пользователя"

from telethon import events
from bot_client import client

@client.on(events.NewMessage(outgoing=True, pattern=r'\.hello$'))
async def hello_handler(event):
    await event.message.edit("👋 Привет, мир!")
```

Первые три строки — обязательные метаданные. Далее — стандартный Telethon-обработчик.

---

## 📁 Структура проекта

```
BinaryUserBot/
│
├── main.py                    ← Точка входа, запускать именно его
├── config.py                  ← Ваши ключи и настройки (заполнить!)
├── settings.json              ← Автосохранение настроек между запусками
├── notes.json                 ← Файл заметок
│
├── state.py                   ← Глобальное состояние бота
├── bot_client.py              ← Экземпляр TelegramClient
├── premium_emoji.py           ← Таблица премиум эмодзи
├── utils.py                   ← Вспомогательные функции
├── settings.py                ← Загрузка/сохранение настроек
├── module_loader.py           ← Система динамических модулей
│
├── ai.py                      ← OpenRouter AI запросы
├── weather.py                 ← Погода
├── prices.py                  ← Курсы валют и крипты
├── calc.py                    ← Калькулятор
├── downloader.py              ← YouTube / TikTok
├── notes.py                   ← Работа с заметками
├── news.py                    ← Дайджест новостей
│
├── user_info.py               ← .info / .me / .stat
├── scam.py                    ← .scam / .lol
├── autochat.py                ← Режим .ac
├── ebalaj.py                  ← .ебалай / .troll
├── prank.py                   ← .snos
├── animations.py              ← Анимации
├── help_faq.py                ← Тексты .help и .faq
│
├── handlers/
│   ├── commands.py            ← Основные команды
│   ├── new_commands.py        ← Новые команды (гороскоп, wiki, и др.)
│   ├── bw_handler.py          ← Фильтр слов
│   ├── channel_handler.py     ← Авто-комментирование
│   └── edit_delete_handler.py ← Логи изменений/удалений
│
└── modules/                   ← Установленные пользователем модули
```

---

## ❓ Частые вопросы

**Q: Бот не запускается, ошибка `ModuleNotFoundError`**
```bash
# Убедитесь, что виртуальное окружение активно:
source .venv/bin/activate
pip install telethon aiohttp yt-dlp
```

**Q: Ошибка `FloodWaitError` при запуске**

Это ограничение Telegram. Подождите указанное количество секунд и попробуйте снова. При частых запусках Telegram временно ограничивает активность.

**Q: Не работает `.гpt` / AI-функции**

Проверьте `OR_TOKEN` в `config.py`. Убедитесь, что на балансе OpenRouter есть средства.

**Q: Команда `.скачать` возвращает ошибку**

Убедитесь, что установлен `ffmpeg`:
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`
- Windows: [скачайте с сайта ffmpeg.org](https://ffmpeg.org/download.html) и добавьте в PATH

**Q: Как обновить бота?**
```bash
cd BinaryUserBot
git pull
source .venv/bin/activate
pip install -r requirements.txt --upgrade
python3 main.py
```

**Q: Как перенести бота на другой сервер?**

1. Скопируйте весь каталог проекта, включая `binsave_session.session` — это файл авторизации
2. Скопируйте `settings.json` и `notes.json`
3. Установите зависимости на новом сервере
4. Запустите `python3 main.py` — авторизоваться повторно не потребуется

**Q: Потерял файл сессии, как переавторизоваться?**

Просто удалите `*.session` файл и запустите бота заново — он попросит код из Telegram.

---

## 📡 Полезные ссылки

- 💬 **Официальный чат / модули** — [t.me/+f6-E3zFi8KQyOTg0](https://t.me/+f6-E3zFi8KQyOTg0)
- 👤 **Поддержка** — [@burgerbeats](https://t.me/burgerbeats)
- 🔑 **Telegram API** — [my.telegram.org](https://my.telegram.org)
- 🤖 **OpenRouter** — [openrouter.ai](https://openrouter.ai)
- 📰 **Новостной канал** — [@binary_news](https://t.me/binary_news)
- 🛡 **Скам-база** — [@GID_ScamBase](https://t.me/GID_ScamBase)

> ⚠️ Для работы команды `.scam` и дайджеста `.lastnews` необходима подписка на [@binary_news](https://t.me/binary_news) и [@GID_ScamBase](https://t.me/GID_ScamBase).

---

## ⚠️ Дисклеймер

Данный проект создан исключительно в образовательных целях. Авторы **не несут ответственности** за любые последствия использования, включая блокировку аккаунта Telegram.

- Не нарушайте [Правила использования Telegram](https://telegram.org/tos)
- Не используйте бота для спама, мошенничества или других незаконных действий
- Устанавливайте только те модули, в безопасности которых уверены
- Никому не передавайте `API_ID`, `API_HASH` и файл сессии `*.session`

---

<div align="center">
  <sub>Сделано с ❤️ by <a href="https://t.me/B1nnary">@B1nnary</a></sub>
</div>
