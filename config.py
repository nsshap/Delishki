"""Configuration module for loading environment variables."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Get the directory where this config file is located
BASE_DIR = Path(__file__).parent.resolve()

# Load .env file from the project root
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

# Notion
NOTION_API_KEY = os.getenv("NOTION_API_KEY", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip()


def validate_config():
    """Validate that all required configuration variables are set."""
    errors = []
    
    # Check if .env file exists
    if not env_path.exists():
        print(f"❌ Файл .env не найден по пути: {env_path}")
        print(f"💡 Создайте файл .env в корне проекта ({BASE_DIR})")
        sys.exit(1)
    
    # Check each required variable
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_telegram_bot_token_here":
        errors.append("❌ TELEGRAM_BOT_TOKEN не установлен или пуст в файле .env")
    
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        errors.append("❌ OPENAI_API_KEY не установлен или пуст в файле .env")
    
    if not NOTION_API_KEY or NOTION_API_KEY == "your_notion_api_key_here":
        errors.append("❌ NOTION_API_KEY не установлен или пуст в файле .env")
    
    if not NOTION_DATABASE_ID or NOTION_DATABASE_ID == "your_notion_database_id_here":
        errors.append("❌ NOTION_DATABASE_ID не установлен или пуст в файле .env")
    
    if errors:
        print("\n".join(errors))
        print(f"\n💡 Проверьте файл .env по пути: {env_path}")
        print("   Убедитесь, что все переменные заполнены и не содержат лишних пробелов или кавычек.")
        print("   Формат должен быть: TELEGRAM_BOT_TOKEN=ваш_токен")
        sys.exit(1)

# Categories
CATEGORIES = [
    "Books",
    "Movies",
    "ShoppingClothes",
    "WorkReading",
    "LeisureIdeas",
    "TravelIdeas",
    "ShoppingHome",
    "Other"
]


