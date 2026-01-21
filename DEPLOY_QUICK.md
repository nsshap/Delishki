# 🚀 Быстрый деплой Delishki Bot

## Шаг 1: Подготовка

Убедитесь, что у вас есть:
- ✅ GitHub репозиторий с кодом
- ✅ Telegram Bot Token (от [@BotFather](https://t.me/botfather))
- ✅ OpenAI API Key
- ✅ Notion API Key и Database ID

## Шаг 2: Выберите платформу

### 🎯 Railway (Самый простой - 3 минуты)

1. Зайдите на [railway.app](https://railway.app) → Login with GitHub
2. **New Project** → **Deploy from GitHub repo**
3. Выберите репозиторий `Delishki`
4. Railway автоматически определит Dockerfile
5. В настройках проекта → **Variables** добавьте:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен
   OPENAI_API_KEY=ваш_ключ
   NOTION_API_KEY=ваш_ключ
   NOTION_DATABASE_ID=ваш_id
   ```
6. Готово! Бот запустится автоматически

### 🎯 Render (Бесплатный план)

1. Зайдите на [render.com](https://render.com) → Sign Up
2. **New** → **Background Worker**
3. Подключите GitHub репозиторий
4. Настройки:
   - **Name**: `delishki-bot`
   - **Environment**: `Docker`
   - **Dockerfile Path**: `Dockerfile` (по умолчанию)
5. В разделе **Environment Variables** добавьте все 4 переменные
6. **Create Background Worker**

### 🎯 Fly.io (Через CLI)

```bash
# Установите flyctl
curl -L https://fly.io/install.sh | sh

# Войдите
fly auth login

# Создайте приложение (автоматически определит Dockerfile)
fly launch

# Добавьте секреты
fly secrets set TELEGRAM_BOT_TOKEN=ваш_токен
fly secrets set OPENAI_API_KEY=ваш_ключ
fly secrets set NOTION_API_KEY=ваш_ключ
fly secrets set NOTION_DATABASE_ID=ваш_id

# Задеплойте
fly deploy
```

## Шаг 3: Проверка

1. Откройте логи на платформе
2. Должно быть сообщение: `Bot is running...`
3. Отправьте тестовое сообщение боту в Telegram
4. Проверьте, что бот отвечает

## Проблемы?

- **Бот не запускается**: Проверьте логи, убедитесь что все переменные установлены
- **Бот не отвечает**: Проверьте токен Telegram бота
- **Ошибки API**: Проверьте ключи OpenAI/Notion

## Обновление

После изменений в коде:
```bash
git add .
git commit -m "Update"
git push origin main
```

Платформа автоматически задеплоит новую версию.
