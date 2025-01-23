# базовый образ
FROM python:3.9

# рабочая директория
WORKDIR /usr/src/async_TGbot

# копируем проект
COPY . /usr/src/async_TGbot

# обновление pip и установка зависимостей
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# запуск Telegram-бота
CMD ["python", "async_TGbot.py"]