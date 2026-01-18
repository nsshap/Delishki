# Delishki - Telegram Bot для рекомендаций

Бот для автоматической категоризации и сохранения рекомендаций (книги, места, кино, подарки) в Notion.

## Возможности

- 📱 Получение рекомендаций через прямые сообщения боту
- 🖼️ Обработка скриншотов с помощью LLM Vision API (OpenAI)
- 🤖 Автоматическая категоризация с помощью LLM (OpenAI)
- 📊 Сохранение в Notion
- 🔗 Автоматическое извлечение ссылок

## Установка

1. Клонируйте репозиторий и перейдите в директорию:
```bash
cd Delishki
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Настройка

1. Создайте файл `.env` в корне проекта и заполните переменные окружения:

### Telegram Bot
- Если у вас уже есть бот, используйте его токен
- Если нужно создать нового бота, используйте [@BotFather](https://t.me/botfather)
- Добавьте токен бота в `TELEGRAM_BOT_TOKEN`
- Бот будет обрабатывать все сообщения, отправленные ему напрямую

### OpenAI
- Получите API ключ на [platform.openai.com](https://platform.openai.com/api-keys)
- Добавьте в `OPENAI_API_KEY`

### Notion
1. Создайте интеграцию в [Notion Integrations](https://www.notion.so/my-integrations)
2. Получите API ключ и добавьте в `NOTION_API_KEY`
3. Создайте базу данных в Notion с полями:
   - `Категория` (Select)
   - `Название` (Title)
   - `Описание` (Rich Text)
   - `Ссылка` (URL)
   - `Дата` (Date)
4. Поделитесь базой данных с интеграцией
5. Скопируйте ID базы данных из URL и добавьте в `NOTION_DATABASE_ID`

## Запуск

```bash
python bot.py
```

Бот начнет слушать все сообщения, отправленные ему напрямую, и автоматически обрабатывать их.

## Использование

Просто отправляйте боту:
- Текстовые сообщения с рекомендациями
- Ссылки на книги, фильмы, места и т.д.
- Скриншоты с рекомендациями

Бот автоматически:
1. Извлечет текст и информацию из скриншотов с помощью LLM Vision API
2. Определит категорию с помощью LLM
3. Сохранит в Notion

## Структура проекта

```
Delishki/
├── bot.py                    # Основной файл бота
├── config.py                 # Конфигурация
├── image_processor.py        # Обработка изображений (LLM Vision API)
├── llm_categorizer.py        # Категоризация через LLM
├── notion_storage.py         # Интеграция с Notion
├── storage_factory.py       # Фабрика для создания хранилища
├── requirements.txt          # Зависимости
└── README.md                # Документация
```

## Категории

По умолчанию бот использует следующие категории:
- Книги
- Места (рестораны, кафе, достопримечательности)
- Кино/Сериалы
- Идеи подарков
- Другое

Категории можно изменить в `config.py`.

## Деплой

Бот можно задеплоить на различные платформы. Ниже инструкции для самых популярных вариантов.

### Railway (Рекомендуется)

1. Зарегистрируйтесь на [Railway](https://railway.app)
2. Создайте новый проект и подключите GitHub репозиторий
3. Добавьте переменные окружения в настройках проекта:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY`
   - `NOTION_API_KEY`
   - `NOTION_DATABASE_ID`
4. Railway автоматически определит конфигурацию из `railway.json` и `Procfile`
5. Бот запустится автоматически после деплоя

### Render

1. Зарегистрируйтесь на [Render](https://render.com)
2. Создайте новый "Background Worker"
3. Подключите GitHub репозиторий
4. Используйте следующие настройки:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. Добавьте переменные окружения в разделе Environment
6. Render автоматически использует `render.yaml` если он есть

### Heroku

1. Установите [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli)
2. Войдите в аккаунт:
   ```bash
   heroku login
   ```
3. Создайте приложение:
   ```bash
   heroku create delishki-bot
   ```
4. Добавьте переменные окружения:
   ```bash
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   heroku config:set OPENAI_API_KEY=your_key
   heroku config:set NOTION_API_KEY=your_key
   heroku config:set NOTION_DATABASE_ID=your_id
   ```
5. Задеплойте:
   ```bash
   git push heroku main
   ```

### Fly.io

1. Установите [flyctl](https://fly.io/docs/getting-started/installing-flyctl/)
2. Войдите в аккаунт:
   ```bash
   fly auth login
   ```
3. Создайте приложение:
   ```bash
   fly launch
   ```
4. Добавьте переменные окружения:
   ```bash
   fly secrets set TELEGRAM_BOT_TOKEN=your_token
   fly secrets set OPENAI_API_KEY=your_key
   fly secrets set NOTION_API_KEY=your_key
   fly secrets set NOTION_DATABASE_ID=your_id
   ```
5. Запустите:
   ```bash
   fly deploy
   ```

### Важные замечания для деплоя

- ⚠️ **Не коммитьте `.env` файл в Git!** Используйте переменные окружения на платформе деплоя
- Бот должен работать как **worker/background process**, а не как web-сервер
- Убедитесь, что платформа поддерживает долгоживущие процессы (не только HTTP запросы)
- Railway и Render имеют бесплатные планы, достаточные для работы бота

## Примечания

- Обработка изображений выполняется через OpenAI Vision API (gpt-4o), что обеспечивает высокое качество распознавания текста и понимания контекста
- Бот обрабатывает все сообщения, отправленные ему напрямую (не требуется настройка канала)
- Все рекомендации сохраняются в Notion базу данных

# Delishki
