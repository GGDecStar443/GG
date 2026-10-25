import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "your_bot_username")

# LLM — дешёвая модель для экономии (gemini-flash-1.5 в 2-3 раза дешевле claude-haiku)
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_API_URL: str = os.getenv("LLM_API_URL", "https://api.vsegpt.ru/v1/chat/completions")
LLM_MODEL: str = os.getenv("LLM_MODEL", "google/gemini-flash-1.5")

# Лимиты
DAILY_LIMIT: int = int(os.getenv("DAILY_LIMIT", "5"))

# Рефералка
REFERRAL_BONUS: int = int(os.getenv("REFERRAL_BONUS", "1"))          # +1 за друга
REFERRAL_DAILY_LIMIT: int = int(os.getenv("REFERRAL_DAILY_LIMIT", "10"))  # макс +10/день

# Монетизация — канал для обязательной подписки (пусто = отключено)
REQUIRED_CHANNEL: str = os.getenv("REQUIRED_CHANNEL", "")

# БД
DB_PATH: str = os.getenv("DB_PATH", "mega_bot.db")

# Валидация
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY не задан в .env")
