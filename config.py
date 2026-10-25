import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_bot")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

LLM_API_KEY = os.getenv("LLM_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.vsegpt.ru/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "anthropic/claude-haiku-5.5")

DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "5"))

# Переменные для базы (рефералка)
REFERRAL_BONUS = int(os.getenv("REFERRAL_BONUS", "1"))
REFERRAL_DAILY_LIMIT = int(os.getenv("REFERRAL_DAILY_LIMIT", "10"))

REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "")
DB_PATH = os.getenv("DB_PATH", "mega_bot.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY не задан")
