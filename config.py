# Загрузка переменных окружения из .env
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "your_bot_username")

# LLM-провайдер (VseGPT, OpenAI-совместимый API)
# По умолчанию — VseGPT + GPT-4o-mini (vision)
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL: str = os.getenv(
    "GROQ_API_URL",
    "https://api.vsegpt.ru/v1/chat/completions",
)
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-4o-mini")

# Лимиты и логи
DAILY_LIMIT: int = int(os.getenv("DAILY_LIMIT", "5"))
LOG_CHANNEL_ID: str = os.getenv("LOG_CHANNEL_ID", "")
DB_PATH: str = os.getenv("DB_PATH", "toxic_check.db")

# Валидация обязательных ключей
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY не задан в .env")
