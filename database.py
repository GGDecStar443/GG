# Асинхронное логирование запросов в SQLite
import aiosqlite
from datetime import date
from typing import Optional
from config import DB_PATH


async def init_db() -> None:
    """Создаёт таблицы users и requests, если их нет."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_requests INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE,
                flags_percent INTEGER,
                toxic_who TEXT
            )
        """)
        await db.commit()


async def _ensure_user(db: aiosqlite.Connection, user_id: int, username: Optional[str]) -> None:
    """Гарантирует наличие пользователя в таблице users."""
    await db.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
        (user_id, username or ""),
    )
    if username:
        await db.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id),
        )


async def can_make_request(user_id: int, daily_limit: int) -> bool:
    """Проверяет, не превышен ли дневной лимит запросов пользователя."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id = ? AND date = ?",
            (user_id, today),
        ) as cur:
            row = await cur.fetchone()
    count = row[0] if row else 0
    return count < daily_limit


async def log_request(user_id: int, username: Optional[str], flags: int, toxic_who: str) -> None:
    """Записывает запрос в БД и инкрементирует счётчик пользователя."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await _ensure_user(db, user_id, username)
        await db.execute(
            "INSERT INTO requests (user_id, date, flags_percent, toxic_who) VALUES (?, ?, ?, ?)",
            (user_id, today, flags, toxic_who),
        )
        await db.execute(
            "UPDATE users SET total_requests = total_requests + 1 WHERE user_id = ?",
            (user_id,),
        )
        await db.commit()


async def get_stats(user_id: int) -> dict:
    """Возвращает статистику пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT total_requests FROM users WHERE user_id = ?", (user_id,)
        ) as cur:
            total_row = await cur.fetchone()
        async with db.execute(
            "SELECT AVG(flags_percent) FROM requests WHERE user_id = ?", (user_id,)
        ) as cur:
            avg_row = await cur.fetchone()
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id = ? AND date = ?",
            (user_id, date.today().isoformat()),
        ) as cur:
            today_row = await cur.fetchone()

    return {
        "total_requests": total_row[0] if total_row else 0,
        "avg_flags": round(avg_row[0], 1) if avg_row and avg_row[0] is not None else 0,
        "today_requests": today_row[0] if today_row else 0,
    }
