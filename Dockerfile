FROM python:3.11-slim

ENV PYTHONPATH=/app

# Создаём рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект внутрь /app
COPY . .

# Запуск будет идти из директории /app
CMD ["python3", "-m", "aio_bot.run"]