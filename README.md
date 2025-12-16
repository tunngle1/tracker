# 🎯 Telegram Habit Tracker Bot

Бот для отслеживания привычек с ежедневными напоминаниями, статистикой и поддержкой таймзон.

## ✨ Возможности

- ✅ Создание привычек (ежедневные или N раз в неделю)
- 📅 Ежедневная отметка выполнения в 1 клик
- 🔔 Настраиваемые напоминания с учётом таймзоны
- 📊 Статистика: текущий/лучший streak, выполнено за 7/30 дней
- ⏭️ Статус "пропуск" не ломает серию

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
cd "трекер привычек"
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
# Скопировать шаблон
copy .env.example .env

# Отредактировать .env и вписать BOT_TOKEN
```

### 3. Запуск бота

```bash
python -m bot.main
```

## 📋 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Онбординг: создать первую привычку |
| `/help` | Справка по боту |

## 🎛️ Меню бота

- **✅ Отметить сегодня** — отметить привычки за текущий день
- **➕ Добавить привычку** — создать новую привычку
- **📋 Мои привычки** — управление (вкл/выкл, переименовать, удалить)
- **📊 Статистика** — просмотр прогресса
- **⚙️ Настройки** — время напоминания, таймзона

## 🔥 Правила Streak

### Daily (ежедневно)
- ✅ **done** — streak увеличивается
- ❌ **not_done** — streak сбрасывается
- ⏭️ **skipped** — streak сохраняется

### Weekly (N раз в неделю)
- Неделя успешна, если выполнено ≥ N раз
- Streak = количество успешных недель подряд
- Skipped не считается как done

## 🧪 Запуск тестов

```bash
# Запустить все тесты
pytest tests/ -v

# Запустить тесты streak
pytest tests/test_streak.py -v
```

## 📁 Структура проекта

```
трекер привычек/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Точка входа
│   ├── config.py            # Конфигурация
│   ├── database/
│   │   ├── models.py        # SQLAlchemy модели
│   │   ├── session.py       # Сессия БД
│   │   └── crud.py          # CRUD операции
│   ├── handlers/
│   │   ├── start.py         # /start, /help
│   │   ├── habits.py        # Управление привычками
│   │   ├── tracking.py      # Отметки за день
│   │   ├── stats.py         # Статистика
│   │   └── settings.py      # Настройки
│   ├── keyboards/
│   │   ├── reply.py         # Reply-клавиатуры
│   │   └── inline.py        # Inline-клавиатуры
│   └── services/
│       ├── streak.py        # Расчёт streak
│       └── scheduler.py     # Планировщик напоминаний
├── tests/
│   └── test_streak.py       # Тесты streak
├── .env.example
├── requirements.txt
└── README.md
```

## 🔧 Конфигурация (.env)

```env
# Токен бота (получить у @BotFather)
BOT_TOKEN=your_telegram_bot_token_here

# URL базы данных SQLite
DATABASE_URL=sqlite+aiosqlite:///./habits.db

# Таймзона по умолчанию
DEFAULT_TIMEZONE=Europe/Moscow
```

## 🌍 Поддерживаемые таймзоны

Быстрый выбор:
- 🇷🇺 Москва (Europe/Moscow)
- 🇺🇦 Киев (Europe/Kiev)
- 🇧🇾 Минск (Europe/Minsk)
- 🇰🇿 Алматы (Asia/Almaty)
- 🇷🇺 Екатеринбург (Asia/Yekaterinburg)

Также можно ввести любую IANA таймзону вручную.

## 🚢 Деплой

### Docker (рекомендуется)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
```

```bash
docker build -t habit-bot .
docker run -d --env-file .env habit-bot
```

### VPS / Сервер

```bash
# 1. Клонировать/загрузить проект
# 2. Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# 3. Установить зависимости
pip install -r requirements.txt

# 4. Настроить .env
cp .env.example .env
nano .env

# 5. Запустить (например через screen/tmux)
screen -S habit-bot
python -m bot.main

# Ctrl+A, D — отключиться от screen
```

### Systemd сервис (Linux)

```ini
# /etc/systemd/system/habit-bot.service
[Unit]
Description=Habit Tracker Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/habit-bot
ExecStart=/home/ubuntu/habit-bot/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable habit-bot
sudo systemctl start habit-bot
```

## 📝 Технологии

- **Python 3.11+**
- **aiogram 3.x** — async Telegram Bot API
- **SQLAlchemy 2.x** — ORM для SQLite
- **APScheduler** — планировщик напоминаний
- **pytz** — работа с таймзонами
- **pytest** — тестирование

## 📄 Лицензия

MIT
