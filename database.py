# База: юзеры, запросы, кэш, рефералка, статистика, бонусы, баны, приватность
import aiosqlite
import hashlib
import json
import os
from datetime import date, datetime, timedelta
from config import DB_PATH, REFERRAL_BONUS, REFERRAL_DAILY_LIMIT, DAILY_LIMIT


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
                bonus_balance INTEGER DEFAULT 0,
                daily_used_today INTEGER DEFAULT 0,
                daily_date DATE,
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
        await _migrate_users_table(db)
        await _migrate_requests_table(db)
        await db.commit()


async def _migrate_users_table(db):
    async with db.execute("PRAGMA table_info(users)") as cur:
        columns = [row[1] for row in await cur.fetchall()]
    migrations = {
        "referred_by": "ALTER TABLE users ADD COLUMN referred_by INTEGER",
        "bonus_balance": "ALTER TABLE users ADD COLUMN bonus_balance INTEGER DEFAULT 0",
        "daily_used_today": "ALTER TABLE users ADD COLUMN daily_used_today INTEGER DEFAULT 0",
        "daily_date": "ALTER TABLE users ADD COLUMN daily_date DATE",
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
    async with db.execute("PRAGMA table_info(requests)") as cur:
        columns = [row[1] for row in await cur.fetchall()]
    if "is_success" not in columns:
        try:
            await db.execute("ALTER TABLE requests ADD COLUMN is_success BOOLEAN DEFAULT 1")
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
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.execute("UPDATE users SET privacy_accepted=1 WHERE user_id=?", (user_id,))
        await db.commit()


# ─────────── ПОПЫТКИ (ДНЕВНЫЕ + БОНУСНЫЕ) ───────────
async def _reset_daily_if_needed(db, user_id: int):
    """Внутренняя функция: сбрасывает дневные счетчики, если наступил новый день."""
    today = date.today().isoformat()
    async with db.execute("SELECT daily_date FROM users WHERE user_id=?", (user_id,)) as cur:
        row = await cur.fetchone()
    if not row or row[0] != today:
        await db.execute(
            "UPDATE users SET daily_used_today=0, daily_date=? WHERE user_id=?",
            (today, user_id)
        )

async def get_daily_used(user_id: int) -> int:
    """Сколько дневных попыток потрачено сегодня."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await _reset_daily_if_needed(db, user_id)
        await db.commit()
        async with db.execute("SELECT daily_used_today FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return (row[0] or 0) if row else 0

async def get_daily_limit(user_id: int) -> int:
    """Дневной лимит (4 + 1 за вход)."""
    return DAILY_LIMIT + (1 if await check_daily_bonus(user_id) else 0)

async def get_bonus_balance(user_id: int) -> int:
    """Общий кошелёк бонусов (не сгорает)."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT bonus_balance FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return (row[0] or 0) if row else 0

async def add_bonus(user_id: int, amount: int):
    """Админская выдача попыток. Идёт в bonus_balance (НЕ сгорает)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.execute(
            "UPDATE users SET bonus_balance = bonus_balance + ? WHERE user_id=?",
            (amount, user_id)
        )
        await db.commit()


async def check_daily_bonus(user_id: int) -> bool:
    """+1 бонус за вход. Привязан к дню."""
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT last_daily_bonus FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        if not row or row[0] != today:
            await db.execute("UPDATE users SET last_daily_bonus=? WHERE user_id=?", (today, user_id))
            await db.commit()
            return True
        return False


async def can_make_request(user_id: int, daily_limit: int) -> bool:
    """Проверяет, есть ли попытки: либо дневные, либо бонусные."""
    daily_used = await get_daily_used(user_id)
    total_daily = daily_limit + (1 if await check_daily_bonus(user_id) else 0) # +1 за вход
    bonus_balance = await get_bonus_balance(user_id)
    
    if daily_used < total_daily:
        return True
    if bonus_balance > 0:
        return True
    return False


async def log_request(user_id: int, score: int, mode: str):
    """Логирует запрос. Списывает сначала дневные, потом бонусные."""
    today = date.today().isoformat()
    is_success = 1 if score > 0 else 0
    
    if not is_success:
        # Если запрос неудачный (например, токсик 0%) — просто пишем в лог
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO requests (user_id, date, mode, score, is_success) VALUES (?, ?, ?, ?, ?)",
                (user_id, today, mode, score, 0),
            )
            await db.commit()
        return

    async with aiosqlite.connect(DB_PATH) as db:
        # Проверяем, надо ли сбросить дневные
        await _reset_daily_if_needed(db, user_id)
        
        async with db.execute("SELECT daily_used_today, bonus_balance, last_daily_bonus FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            
        daily_used = row[0] or 0
        bonus_balance = row[1] or 0
        last_bonus = row[2]
        
        total_daily_limit = DAILY_LIMIT + (1 if last_bonus == today else 0)

        if daily_used < total_daily_limit:
            # Списываем дневную
            await db.execute("UPDATE users SET daily_used_today = daily_used_today + 1 WHERE user_id=?", (user_id,))
        elif bonus_balance > 0:
            # Списываем бонусную
            await db.execute("UPDATE users SET bonus_balance = bonus_balance - 1 WHERE user_id=?", (user_id,))
        
        # Пишем в лог
        await db.execute(
            "INSERT INTO requests (user_id, date, mode, score, is_success) VALUES (?, ?, ?, ?, ?)",
            (user_id, today, mode, score, 1),
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
        async with db.execute("SELECT result_json FROM cache WHERE hash=? AND mode=?", (h, mode)) as cur:
            row = await cur.fetchone()
    return json.loads(row[0]) if row else None

async def save_cache(image_bytes: bytes, mode: str, result: dict):
    h = _hash_image(image_bytes)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO cache (hash, mode, result_json) VALUES (?, ?, ?)", (h, mode, json.dumps(result, ensure_ascii=False)))
        await db.commit()


# ─────────── РЕФЕРАЛКА И СТАТИСТИКА ───────────
async def get_referral_count(user_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (user_id,)) as cur:
            row = await cur.fetchone()
    return row[0] if row else 0

async def get_weekly_top() -> list:
    seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT u.username, u.user_id, COUNT(r.id) as cnt
            FROM users u JOIN requests r ON r.user_id = u.user_id
            WHERE r.date >= ? AND r.is_success = 1
            GROUP BY u.user_id ORDER BY cnt DESC LIMIT 10
        """, (seven_days_ago,)) as cur:
            return await cur.fetchall()

async def get_full_stats() -> dict:
    today = date.today().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        total_users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        new_today = (await (await db.execute("SELECT COUNT(*) FROM users WHERE DATE(first_seen) = ?", (today,))).fetchone())[0]
        active_today = (await (await db.execute("SELECT COUNT(DISTINCT user_id) FROM requests WHERE date = ?", (today,))).fetchone())[0]
        requests_today = (await (await db.execute("SELECT COUNT(*) FROM requests WHERE date = ?", (today,))).fetchone())[0]
        requests_total = (await (await db.execute("SELECT COUNT(*) FROM requests")).fetchone())[0]
        by_mode_rows = await (await db.execute("SELECT mode, COUNT(*) FROM requests GROUP BY mode")).fetchall()
        cache_size = (await (await db.execute("SELECT COUNT(*) FROM cache")).fetchone())[0]
        top_users = await (await db.execute("""
            SELECT u.username, u.user_id, COUNT(r.id) as cnt
            FROM users u JOIN requests r ON r.user_id = u.user_id
            GROUP BY u.user_id ORDER BY cnt DESC LIMIT 5
        """)).fetchall()
        top_referrers = await (await db.execute("""
            SELECT u.username, u.user_id, COUNT(u2.user_id) as refs
            FROM users u JOIN users u2 ON u2.referred_by = u.user_id
            GROUP BY u.user_id ORDER BY refs DESC LIMIT 5
        """)).fetchall()
    return {
        "total_users": total_users, "new_today": new_today, "active_today": active_today,
        "requests_today": requests_today, "requests_total": requests_total,
        "by_mode": dict(by_mode_rows), "cache_size": cache_size,
        "top_users": top_users, "top_refs": top_referrers,
    }

# ─────────── БАНЫ ───────────
async def get_ban_status(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT violations_count, banned_until, is_permanent FROM violations WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
    if not row: return {"is_banned": False, "is_permanent": False, "violations": 0}
    count, banned_until, is_perm = row
    if is_perm: return {"is_banned": True, "is_permanent": True, "violations": count}
    if banned_until:
        try:
            ban_dt = datetime.fromisoformat(banned_until)
            if ban_dt > datetime.now():
                remaining = int((ban_dt - datetime.now()).total_seconds() / 60)
                return {"is_banned": True, "is_permanent": False, "violations": count, "remaining_min": remaining}
        except Exception: pass
    return {"is_banned": False, "is_permanent": False, "violations": count}

async def add_violation(user_id: int, reason: str = "мат/спам") -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT violations_count FROM violations WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
        count = (row[0] if row else 0) + 1
        if count >= 3:
            await db.execute("INSERT OR REPLACE INTO violations (user_id, violations_count, banned_until, is_permanent, reason) VALUES (?, ?, NULL, 1, ?)", (user_id, count, reason))
            await db.commit()
            return {"action": "permanent_ban", "count": count}
        elif count == 2:
            ban_until = (datetime.now() + timedelta(minutes=30)).isoformat()
            await db.execute("INSERT OR REPLACE INTO violations (user_id, violations_count, banned_until, is_permanent, reason) VALUES (?, ?, ?, 0, ?)", (user_id, count, ban_until, reason))
            await db.commit()
            return {"action": "temp_ban", "count": count, "minutes": 30}
        else:
            await db.execute("INSERT OR REPLACE INTO violations (user_id, violations_count, banned_until, is_permanent, reason) VALUES (?, ?, NULL, 0, ?)", (user_id, count, reason))
            await db.commit()
            return {"action": "warning", "count": count}

async def get_banned_users() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT v.user_id, u.username, v.violations_count, v.banned_until, v.is_permanent, v.reason
            FROM violations v LEFT JOIN users u ON u.user_id = v.user_id
            WHERE v.is_permanent = 1 OR (v.banned_until IS NOT NULL AND v.banned_until > ?)
            ORDER BY v.is_permanent DESC, v.banned_until DESC
        """, (datetime.now().isoformat(),)) as cur:
            return await cur.fetchall()

async def pardon_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM violations WHERE user_id=?", (user_id,))
        await db.commit()
async def get_top_referrers(limit: int = 10) -> list:
    """Возвращает топ юзеров по количеству приглашенных."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT u1.username, u1.user_id, COUNT(u2.user_id) as refs
            FROM users u1
            JOIN users u2 ON u2.referred_by = u1.user_id
            GROUP BY u1.user_id
            ORDER BY refs DESC
            LIMIT ?
        """, (limit,)) as cur:
            return await cur.fetchall()
