# База: юзеры, запросы, кэш, рефералка, статистика, бонусы
import aiosqlite
import hashlib
import json
from datetime import date
from config import DB_PATH, REFERRAL_BONUS, REFERRAL_DAILY_LIMIT


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_requests INTEGER DEFAULT 0,
                referred_by INTEGER,
                bonus_today INTEGER DEFAULT 0,
                bonus_date DATE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE,
                mode TEXT,
                score INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                hash TEXT PRIMARY KEY,
                mode TEXT,
                result_json TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


async def register_user(user_id: int, username, referred_by=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, referred_by) VALUES (?, ?, ?)",
            (user_id, username or "", referred_by),
        )
        if username:
            await db.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
        await db.commit()


async def get_today_requests(user_id: int) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=? AND date=?",
            (user_id, today),
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def get_bonus_today(user_id: int) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT bonus_today, bonus_date FROM users WHERE user_id=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return 0
    bonus, bdate = row
    if bdate != today:
        return 0
    return bonus or 0


async def add_referral_bonus(user_id: int) -> bool:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT bonus_today, bonus_date FROM users WHERE user_id=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return False
        bonus, bdate = row
        if bdate != today:
            bonus = 0
        if (bonus or 0) >= REFERRAL_DAILY_LIMIT:
            return False
        new_bonus = (bonus or 0) + REFERRAL_BONUS
        await db.execute(
            "UPDATE users SET bonus_today=?, bonus_date=? WHERE user_id=?",
            (new_bonus, today, user_id),
        )
        await db.commit()
    return True


async def add_bonus(user_id: int, amount: int):
    """Админская выдача бонусных попыток."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, есть ли юзер
        async with db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)) as cur:
            if not await cur.fetchone():
                await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        
        async with db.execute("SELECT bonus_today, bonus_date FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        
        current_bonus = 0
        if row and row[1] == today:
            current_bonus = row[0] or 0
            
        new_bonus = current_bonus + amount
        await db.execute("UPDATE users SET bonus_today=?, bonus_date=? WHERE user_id=?", (new_bonus, today, user_id))
        await db.commit()


async def can_make_request(user_id: int, daily_limit: int) -> bool:
    used = await get_today_requests(user_id)
    bonus = await get_bonus_today(user_id)
    return used < (daily_limit + bonus)


async def log_request(user_id: int, score: int, mode: str):
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO requests (user_id, date, mode, score) VALUES (?, ?, ?, ?)",
            (user_id, today, mode, score),
        )
        await db.execute(
            "UPDATE users SET total_requests = total_requests + 1 WHERE user_id=?",
            (user_id,),
        )
        await db.commit()


# ─────────── КЭШ ───────────
def _hash_image(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


async def get_cached(image_bytes: bytes, mode: str) -> dict | None:
    h = _hash_image(image_bytes)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT result_json FROM cache WHERE hash=? AND mode=?",
            (h, mode),
        ) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else None


async def save_cache(image_bytes: bytes, mode: str, result: dict):
    h = _hash_image(image_bytes)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO cache (hash, mode, result_json) VALUES (?, ?, ?)",
            (h, mode, json.dumps(result, ensure_ascii=False)),
        )
        await db.commit()


async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


# ─────────── СТАТИСТИКА ───────────
async def get_full_stats() -> dict:
    today = date.today().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(first_seen) = ?", (today,)
        ) as cur:
            new_today = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM requests WHERE date = ?", (today,)
        ) as cur:
            active_today = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE date = ?", (today,)
        ) as cur:
            requests_today = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM requests") as cur:
            requests_total = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT mode, COUNT(*) FROM requests GROUP BY mode"
        ) as cur:
            by_mode_rows = await cur.fetchall()

        async with db.execute("SELECT COUNT(*) FROM cache") as cur:
            cache_size = (await cur.fetchone())[0]

        async with db.execute("""
            SELECT u.username, u.user_id, COUNT(r.id) as cnt
            FROM users u
            JOIN requests r ON r.user_id = u.user_id
            GROUP BY u.user_id
            ORDER BY cnt DESC
            LIMIT 5
        """) as cur:
            top_users = await cur.fetchall()

        async with db.execute("""
            SELECT u.username, u.user_id, COUNT(u2.user_id) as refs
            FROM users u
            JOIN users u2 ON u2.referred_by = u.user_id
            GROUP BY u.user_id
            ORDER BY refs DESC
            LIMIT 5
        """) as cur:
            top_referrers = await cur.fetchall()

    return {
        "total_users": total_users,
        "new_today": new_today,
        "active_today": active_today,
        "requests_today": requests_today,
        "requests_total": requests_total,
        "by_mode": dict(by_mode_rows),
        "cache_size": cache_size,
        "top_users": top_users,
        "top_refs": top_referrers,
    }
