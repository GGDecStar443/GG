# База: юзеры, запросы, кэш, рефералка, статистика, бонусы, баны, приватность
import aiosqlite
import hashlib
import json
import os
from datetime import date, datetime, timedelta
from config import DB_PATH, REFERRAL_BONUS, REFERRAL_DAILY_LIMIT


async def init_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception as e:
            print(f"[DB] Не смог создать папку {db_dir}: {e}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_requests INTEGER DEFAULT 0,
                referred_by INTEGER,
                bonus_today INTEGER DEFAULT 0,
                bonus_date DATE,
                last_daily_bonus DATE,
                points INTEGER DEFAULT 0,
                privacy_accepted BOOLEAN DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date DATE,
                mode TEXT,
                score INTEGER,
                is_success BOOLEAN DEFAULT 1
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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                user_id INTEGER PRIMARY KEY,
                violations_count INTEGER DEFAULT 0,
                banned_until TIMESTAMP,
                is_permanent BOOLEAN DEFAULT 0,
                reason TEXT
            )
        """)
        # Миграции
        await _migrate_users_table(db)
        await _migrate_requests_table(db)
        await db.commit()


async def _migrate_users_table(db):
    async with db.execute("PRAGMA table_info(users)") as cur:
        columns = [row[1] for row in await cur.fetchall()]
    migrations = {
        "referred_by": "ALTER TABLE users ADD COLUMN referred_by INTEGER",
        "bonus_today": "ALTER TABLE users ADD COLUMN bonus_today INTEGER DEFAULT 0",
        "bonus_date": "ALTER TABLE users ADD COLUMN bonus_date DATE",
        "last_daily_bonus": "ALTER TABLE users ADD COLUMN last_daily_bonus DATE",
        "points": "ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 0",
        "privacy_accepted": "ALTER TABLE users ADD COLUMN privacy_accepted BOOLEAN DEFAULT 0",
    }
    for col, sql in migrations.items():
        if col not in columns:
            try:
                await db.execute(sql)
            except Exception:
                pass


async def _migrate_requests_table(db):
    """Добавляет колонку is_success, если её нет (для старых баз)."""
    async with db.execute("PRAGMA table_info(requests)") as cur:
        columns = [row[1] for row in await cur.fetchall()]
    if "is_success" not in columns:
        try:
            await db.execute("ALTER TABLE requests ADD COLUMN is_success BOOLEAN DEFAULT 1")
            # Всем старым запросам ставим успешные
            await db.execute("UPDATE requests SET is_success = 1 WHERE is_success IS NULL")
        except Exception:
            pass


async def register_user(user_id: int, username, referred_by=None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, referred_by) VALUES (?, ?, ?)",
            (user_id, username or "", referred_by),
        )
        if username:
            await db.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
        await db.commit()


# ─────────── ПРИВАТНОСТЬ ───────────
async def is_privacy_accepted(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT privacy_accepted FROM users WHERE user_id=?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
    return bool(row and row[0])


async def set_privacy_accepted(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        await db.execute(
            "UPDATE users SET privacy_accepted=1 WHERE user_id=?",
            (user_id,)
        )
        await db.commit()


# ─────────── ЗАПРОСЫ И ЛИМИТЫ ───────────
async def get_today_requests(user_id: int) -> int:
    """Считает ТОЛЬКО успешные запросы (is_success=1)."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM requests WHERE user_id=? AND date=? AND is_success=1",
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
    """
    Админская выдача бонусов.
    ВАЖНО: bonus_today привязан к дате. На следующий день сбрасывается.
    """
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)) as cur:
            if not await cur.fetchone():
                await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        
        async with db.execute("SELECT bonus_today, bonus_date FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        
        current_bonus = 0
        if row and row[1] == today:
            current_bonus = row[0] or 0
        
        new_bonus = current_bonus + amount
        
        await db.execute(
            "UPDATE users SET bonus_today=?, bonus_date=? WHERE user_id=?",
            (new_bonus, today, user_id)
        )
        await db.commit()


async def check_daily_bonus(user_id: int) -> bool:
    """
    Даёт +1 бонус за вход, если сегодня ещё не брал.
    НЕ перезаписывает существующий бонус из админки.
    """
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT last_daily_bonus, bonus_today, bonus_date FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        
        if not row:
            return False
        
        last_daily, current_bonus, current_date = row
        
        # Если сегодня уже брал — не даём
        if last_daily == today:
            return False
        
        # Считаем бонус: если bonus_date = сегодня — прибавляем к текущему, иначе 1
        base = (current_bonus or 0) if current_date == today else 0
        new_bonus = base + 1
        
        await db.execute(
            "UPDATE users SET last_daily_bonus=?, bonus_today=?, bonus_date=? WHERE user_id=?",
            (today, new_bonus, today, user_id)
        )
        await db.commit()
        return True


async def can_make_request(user_id: int, daily_limit: int) -> bool:
    used = await get_today_requests(user_id)
    bonus = await get_bonus_today(user_id)
    return used < (daily_limit + bonus)


async def log_request(user_id: int, score: int, mode: str):
    """
    Логирует КАЖДЫЙ запрос. is_success=1 — если score > 0.
    Токсик с флагами 0 → is_success=0 (не списывает лимит).
    """
    today = date.today().isoformat()
    is_success = 1 if score > 0 else 0
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO requests (user_id, date, mode, score, is_success) VALUES (?, ?, ?, ?, ?)",
            (user_id, today, mode, score, is_success),
        )
        await db.execute(
            "UPDATE users SET total_requests = total_requests + 1, points = points + 10 WHERE user_id=?",
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


# ─────────── РЕФЕРАЛКА ───────────
async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM users WHERE referred_by=?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0


async def get_weekly_top() -> list:
    """Топ-10 юзеров по активности за 7 дней."""
    seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT u.username, u.user_id, COUNT(r.id) as cnt
            FROM users u
            JOIN requests r ON r.user_id = u.user_id
            WHERE r.date >= ? AND r.is_success = 1
            GROUP BY u.user_id
            ORDER BY cnt DESC
            LIMIT 10
        """, (seven_days_ago,)) as cur:
            return await cur.fetchall()


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


# ─────────── БАНЫ ───────────
async def get_ban_status(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT violations_count, banned_until, is_permanent FROM violations WHERE user_id=?",
            (user_id,)
        ) as cur:
            row = await cur.fetchone()
    if not row:
        return {"is_banned": False, "is_permanent": False, "violations": 0}
    count, banned_until, is_perm = row
    if is_perm:
        return {"is_banned": True, "is_permanent": True, "violations": count}
    if banned_until:
        try:
            ban_dt = datetime.fromisoformat(banned_until)
            if ban_dt > datetime.now():
                remaining = int((ban_dt - datetime.now()).total_seconds() / 60)
                return {"is_banned": True, "is_permanent": False, "violations": count, "remaining_min": remaining}
        except Exception:
            pass
    return {"is_banned": False, "is_permanent": False, "violations": count}


async def add_violation(user_id: int, reason: str = "мат/спам") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT violations_count FROM violations WHERE user_id=?", (user_id,)
        ) as cur:
            row = await cur.fetchone()
        count = (row[0] if row else 0) + 1
        if count >= 3:
            await db.execute("""
                INSERT OR REPLACE INTO violations (user_id, violations_count, banned_until, is_permanent, reason)
                VALUES (?, ?, NULL, 1, ?)
            """, (user_id, count, reason))
            await db.commit()
            return {"action": "permanent_ban", "count": count}
        elif count == 2:
            ban_until = (datetime.now() + timedelta(minutes=30)).isoformat()
            await db.execute("""
                INSERT OR REPLACE INTO violations (user_id, violations_count, banned_until, is_permanent, reason)
                VALUES (?, ?, ?, 0, ?)
            """, (user_id, count, ban_until, reason))
            await db.commit()
            return {"action": "temp_ban", "count": count, "minutes": 30}
        else:
            await db.execute("""
                INSERT OR REPLACE INTO violations (user_id, violations_count, banned_until, is_permanent, reason)
                VALUES (?, ?, NULL, 0, ?)
            """, (user_id, count, reason))
            await db.commit()
            return {"action": "warning", "count": count}


async def get_banned_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT v.user_id, u.username, v.violations_count, v.banned_until, v.is_permanent, v.reason
            FROM violations v
            LEFT JOIN users u ON u.user_id = v.user_id
            WHERE v.is_permanent = 1 OR (v.banned_until IS NOT NULL AND v.banned_until > ?)
            ORDER BY v.is_permanent DESC, v.banned_until DESC
        """, (datetime.now().isoformat(),)) as cur:
            return await cur.fetchall()


async def pardon_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM violations WHERE user_id=?", (user_id,))
        await db.commit()
