# 📅 Расписание ТУСУР

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.x-blue?logo=telegram)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-brightgreen)

Telegram-бот для просмотра расписания занятий **ТУСУР** (Томский государственный университет систем управления и радиоэлектроники).


---

## Как выглядит расписание

```
📅 Среда, 4 марта
👥 Группа 746-1

📊 3 пары  ·  ⏱ 08:30 — 13:50  (5ч 20мин)
▶️ Математика  →  Физика

⏰  Пара 1  ·  08:30 — 10:05

📚  Математика
📝  Лекция
📍  ауд. 201
👤  Иванов И.И.

☕  Перерыв 09:15–09:20 · 5 мин
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
⏰  Пара 2  ·  10:20 — 11:55

📚  Программирование
📝  Практика
📍  ауд. 305
👤  Петров П.П.

☕  Перерыв 11:05–11:10 · 5 мин
```

---

## Возможности

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и выбор группы |
| `/schedule` | Расписание на сегодня |
| `/tomorrow` | Расписание на завтра |
| `/week` | Обзор недели с загруженностью `▓▓▓░░░` |
| `/next` | Следующая пара по текущему времени |
| `/group` | Текущая группа |
| `/change` | Сменить группу |
| `/notify` | Настройка уведомлений |
| `/help` | Справка |

### Дополнительно

- **Навигация по дням** — кнопки ◀ Вчера / Завтра ▶ прямо в расписании
- **Выбор дня текстом** — напиши `пн`, `вт`, `fri`, `3` — получишь расписание на этот день
- **Выбор группы** по факультетам (10 факультетов, 387+ групп) или вводом номера (`746-1`)
- **Уведомления** (настраиваются через `/notify`):
  - ✅ За 15 мин до начала пары
  - ✅ За 15 мин до конца пары
  - ✅ Перерыв в середине пары

---

## Быстрый старт

```bash
# 1. Клонировать репозиторий
git clone https://github.com/Nerykery/raspis-bot.git
cd raspis-bot

# 2. Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Создать .env файл
cp .env.example .env
# Вставить BOT_TOKEN из @BotFather

# 5. Запустить
python bot.py
```

---

## Переменные окружения

Создай файл `.env` в корне проекта:

```env
BOT_TOKEN=your_telegram_bot_token_here
```

Получить токен: [@BotFather](https://t.me/BotFather) → `/newbot`

---

## Деплой через pm2

```bash
# Установить pm2 (если нет)
npm install -g pm2

# Запустить бота
pm2 start .venv/bin/python --name raspis-bot -- bot.py

# Автозапуск при перезагрузке сервера
pm2 save
pm2 startup

# Мониторинг
pm2 status
pm2 logs raspis-bot
```

---

## Структура проекта

```
raspis-bot/
├── bot.py            # Точка входа, обработчики команд и callback-ов
├── ui.py             # Рендеринг сообщений и inline-клавиатуры
├── schedule_api.py   # Клиент API расписания ТУСУР, кеш, парсинг
├── group_catalog.py  # Каталог факультетов и групп (парсинг сайта)
├── storage.py        # Хранение данных пользователей (JSON)
├── notifier.py       # Фоновый планировщик уведомлений
├── config.py         # Конфигурация через переменные окружения
├── requirements.txt  # Зависимости
├── .env.example      # Шаблон переменных окружения
└── Makefile          # Удобные команды (install, run, lint)
```

---

## Технологии

- **[aiogram 3](https://docs.aiogram.dev/)** — асинхронный фреймворк для Telegram Bot API
- **[aiohttp](https://docs.aiohttp.org/)** — HTTP-клиент для запросов к API ТУСУР
- **API ТУСУР** — `https://api.tusur.ru/api/v1/timetable/lessons/{group}`

---

## Разработка

```bash
# Установить зависимости для разработки
pip install -r requirements-dev.txt

# Проверка кода
make lint
```

---

## Лицензия

MIT © 2026
