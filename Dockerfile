FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаём директорию для данных
RUN mkdir -p /app/data

# Устанавливаем PYTHONPATH чтобы импорты работали
ENV PYTHONPATH=/app

# Запускаем как модуль
CMD ["python", "-m", "bot.main"]
