import os
from dotenv import load_dotenv

load_dotenv()

# ─── Telegram ───
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "your_bot").lstrip("@")
BOT_LINK: str = f"https://t.me/{BOT_USERNAME}"
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))

# Ссылка на админа (для политики и /help)
ADMIN_URL: str = os.getenv("ADMIN_URL", "https://t.me/your_admin_username")

# ─── LLM (VseGPT) ───
# Поддерживаем ОБА имени переменных (LLM_* и старое GROQ_*)
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
LLM_API_URL: str = (
    os.getenv("LLM_API_URL", "")
    or os.getenv("GROQ_API_URL", "")
    or "https://api.vsegpt.ru/v1/chat/completions"
)
LLM_MODEL: str = (
    os.getenv("LLM_MODEL", "")
    or os.getenv("GROQ_MODEL", "")
    or "anthropic/claude-haiku-5.5"
)

# ─── Лимиты ───
DAILY_LIMIT: int = int(os.getenv("DAILY_LIMIT", "4"))
REFERRAL_BONUS: int = int(os.getenv("REFERRAL_BONUS", "1"))
REFERRAL_DAILY_LIMIT: int = int(os.getenv("REFERRAL_DAILY_LIMIT", "10"))

# ─── Монетизация ───
# Пусто = проверка подписки отключена
REQUIRED_CHANNEL: str = os.getenv("REQUIRED_CHANNEL", "")

# ─── База ───
DB_PATH: str = os.getenv("DB_PATH", "data/mega_bot.db")

# ─── Валидация ───
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан")
if not LLM_API_KEY:
    raise RuntimeError("LLM_API_KEY (или GROQ_API_KEY) не задан")
if ADMIN_ID == 0:
    print("⚠️ ADMIN_ID не задан — команда /admin будет недоступна")
