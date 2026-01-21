# Инструкция по деплою Delishki Bot

## 🐳 Деплой через Docker (Рекомендуется)

### Локальный запуск через Docker

1. **Соберите образ:**
   ```bash
   docker build -t delishki-bot .
   ```

2. **Запустите контейнер:**
   ```bash
   docker run -d \
     --name delishki-bot \
     --restart unless-stopped \
     -e TELEGRAM_BOT_TOKEN=your_token \
     -e OPENAI_API_KEY=your_key \
     -e NOTION_API_KEY=your_key \
     -e NOTION_DATABASE_ID=your_id \
     delishki-bot
   ```

   Или используйте docker-compose (удобнее):
   ```bash
   # Убедитесь, что файл .env существует с нужными переменными
   docker-compose up -d
   ```

3. **Проверьте логи:**
   ```bash
   docker logs -f delishki-bot
   ```

### Деплой Docker образа на платформы

#### Railway с Docker
1. Создайте проект на Railway
2. Подключите GitHub репозиторий
3. Railway автоматически определит Dockerfile
4. Добавьте переменные окружения в настройках
5. Деплой произойдет автоматически

#### Render с Docker
1. Создайте "Web Service" на Render
2. Подключите репозиторий
3. Выберите "Docker" как тип сервиса
4. Render автоматически использует Dockerfile
5. Добавьте переменные окружения

#### Fly.io с Docker
```bash
# Установите flyctl
fly auth login
fly launch  # Создаст fly.toml
fly secrets set TELEGRAM_BOT_TOKEN=your_token
fly secrets set OPENAI_API_KEY=your_key
fly secrets set NOTION_API_KEY=your_key
fly secrets set NOTION_DATABASE_ID=your_id
fly deploy
```

#### DigitalOcean App Platform
1. Создайте приложение на DigitalOcean
2. Подключите GitHub репозиторий
3. Выберите "Dockerfile" как способ деплоя
4. Добавьте переменные окружения
5. Задеплойте

#### VPS (Ubuntu/Debian)
```bash
# На вашем VPS
git clone your-repo
cd Delishki
docker build -t delishki-bot .
docker run -d \
  --name delishki-bot \
  --restart unless-stopped \
  --env-file .env \
  delishki-bot
```

### Обновление Docker образа
```bash
# Пересоберите образ
docker build -t delishki-bot .

# Остановите старый контейнер
docker stop delishki-bot
docker rm delishki-bot

# Запустите новый
docker run -d --name delishki-bot --restart unless-stopped --env-file .env delishki-bot
```

Или с docker-compose:
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Быстрый деплой на Railway (5 минут)

### Шаг 1: Подготовка репозитория
```bash
# Убедитесь, что все изменения закоммичены
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### Шаг 2: Создание проекта на Railway
1. Перейдите на [railway.app](https://railway.app) и войдите через GitHub
2. Нажмите "New Project"
3. Выберите "Deploy from GitHub repo"
4. Выберите репозиторий `Delishki`

### Шаг 3: Настройка переменных окружения
В настройках проекта Railway добавьте следующие переменные:

- `TELEGRAM_BOT_TOKEN` - токен вашего Telegram бота
- `OPENAI_API_KEY` - ключ OpenAI API
- `NOTION_API_KEY` - ключ Notion API
- `NOTION_DATABASE_ID` - ID базы данных Notion

### Шаг 4: Запуск
Railway автоматически:
- Определит Python проект
- Установит зависимости из `requirements.txt`
- Запустит бота через `Procfile`

Бот будет работать 24/7 и автоматически перезапускаться при сбоях.

## Альтернативные платформы

### Render.com
1. Создайте аккаунт на [render.com](https://render.com)
2. Создайте новый "Background Worker"
3. Подключите GitHub репозиторий
4. Установите:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python bot.py`
5. Добавьте переменные окружения
6. Нажмите "Create"

### Heroku
```bash
# Установите Heroku CLI
heroku login
heroku create delishki-bot
heroku config:set TELEGRAM_BOT_TOKEN=your_token
heroku config:set OPENAI_API_KEY=your_key
heroku config:set NOTION_API_KEY=your_key
heroku config:set NOTION_DATABASE_ID=your_id
git push heroku main
```

## Проверка работы бота

После деплоя:
1. Откройте логи на платформе деплоя
2. Убедитесь, что видите сообщение "Bot is running..."
3. Отправьте тестовое сообщение боту в Telegram
4. Проверьте, что бот отвечает и сохраняет данные в Notion

## Мониторинг

- **Railway**: Логи доступны в реальном времени в панели проекта
- **Render**: Логи в разделе "Logs" вашего сервиса
- **Heroku**: `heroku logs --tail`

## Обновление бота

После изменений в коде:
```bash
git add .
git commit -m "Update bot"
git push origin main
```

Платформа автоматически задеплоит новую версию.

## Устранение проблем

### Бот не запускается
- Проверьте логи на платформе
- Убедитесь, что все переменные окружения установлены
- Проверьте формат переменных (без лишних пробелов, кавычек)

### Бот не отвечает
- Проверьте, что токен Telegram бота правильный
- Убедитесь, что бот запущен (проверьте логи)
- Попробуйте перезапустить сервис на платформе

### Ошибки с OpenAI/Notion
- Проверьте API ключи
- Убедитесь, что у ключей есть необходимые права доступа
- Проверьте баланс OpenAI аккаунта (если используется платный план)
