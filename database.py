import asyncpg
import hashlib
import json
from datetime import date, datetime, timedelta
from config import DATABASE_URL, REFERRAL_BONUS, DAILY_LIMIT

pool: asyncpg.Pool | None = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    async with pool.acquire() as c:
        await c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                first_seen TIMESTAMPTZ DEFAULT NOW(),
                total_requests INTEGER DEFAULT 0,
                referred_by BIGINT,
                bonus_balance INTEGER DEFAULT 0,
                daily_used_today INTEGER DEFAULT 0,
                daily_date DATE,
                last_daily_bonus DATE,
                points INTEGER DEFAULT 0,
                privacy_accepted BOOLEAN DEFAULT FALSE
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT,
                date DATE,
                mode TEXT,
                score INTEGER,
                is_success BOOLEAN DEFAULT TRUE
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                hash TEXT PRIMARY KEY,
                mode TEXT,
                result_json TEXT,
                created TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        await c.execute("""
            CREATE TABLE IF NOT EXISTS violations (
                user_id BIGINT PRIMARY KEY,
                violations_count INTEGER DEFAULT 0,
                banned_until TIMESTAMPTZ,
                is_permanent BOOLEAN DEFAULT FALSE,
                reason TEXT
            )
        """)

async def close_db():
    global pool
    if pool:
        await pool.close()

async def register_user(user_id: int, username, referred_by=None):
    async with pool.acquire() as c:
        await c.execute(
            "INSERT INTO users (user_id, username, referred_by) VALUES ($1, $2, $3) "
            "ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username",
            user_id, username or "", referred_by,
        )

async def is_privacy_accepted(user_id: int) -> bool:
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT privacy_accepted FROM users WHERE user_id=$1", user_id)
    return bool(row and row["privacy_accepted"])

async def set_privacy_accepted(user_id: int):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
        await c.execute("UPDATE users SET privacy_accepted=TRUE WHERE user_id=$1", user_id)

async def _reset_daily_if_needed(c, user_id: int):
    today = date.today()
    row = await c.fetchrow("SELECT daily_date FROM users WHERE user_id=$1", user_id)
    if not row or row["daily_date"] != today:
        await c.execute("UPDATE users SET daily_used_today=0, daily_date=$1 WHERE user_id=$2", today, user_id)

async def get_daily_used(user_id: int) -> int:
    async with pool.acquire() as c:
        await _reset_daily_if_needed(c, user_id)
        row = await c.fetchrow("SELECT daily_used_today FROM users WHERE user_id=$1", user_id)
    return (row["daily_used_today"] or 0) if row else 0

async def get_bonus_balance(user_id: int) -> int:
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT bonus_balance FROM users WHERE user_id=$1", user_id)
    return (row["bonus_balance"] or 0) if row else 0

async def add_bonus(user_id: int, amount: int):
    async with pool.acquire() as c:
        await c.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
        await c.execute("UPDATE users SET bonus_balance = bonus_balance + $1 WHERE user_id=$2", amount, user_id)

async def check_daily_bonus(user_id: int) -> bool:
    today = date.today()
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT last_daily_bonus FROM users WHERE user_id=$1", user_id)
        if not row or row["last_daily_bonus"] != today:
            await c.execute("UPDATE users SET last_daily_bonus=$1 WHERE user_id=$2", today, user_id)
            return True
        return False

async def can_make_request(user_id: int, daily_limit: int) -> bool:
    today = date.today()
    async with pool.acquire() as c:
        await _reset_daily_if_needed(c, user_id)
        row = await c.fetchrow("SELECT daily_used_today, bonus_balance, last_daily_bonus FROM users WHERE user_id=$1", user_id)
            
    if not row: return False
    daily_used = row["daily_used_today"] or 0
    bonus_balance = row["bonus_balance"] or 0
    last_bonus = row["last_daily_bonus"]
    total_daily_limit = daily_limit + (1 if last_bonus == today else 0)
    return daily_used < total_daily_limit or bonus_balance > 0

async def use_attempt(user_id: int, daily_limit: int) -> dict:
    today = date.today()
    async with pool.acquire() as c:
        await _reset_daily_if_needed(c, user_id)
        row = await c.fetchrow("SELECT daily_used_today, bonus_balance, last_daily_bonus FROM users WHERE user_id=$1", user_id)
        daily_used = row["daily_used_today"] or 0
        bonus_balance = row["bonus_balance"] or 0
        last_bonus = row["last_daily_bonus"]
        total_daily_limit = daily_limit + (1 if last_bonus == today else 0)

        if daily_used < total_daily_limit:
            await c.execute("UPDATE users SET daily_used_today = daily_used_today + 1 WHERE user_id=$1", user_id)
            return {"type": "daily", "success": True}
        elif bonus_balance > 0:
            await c.execute("UPDATE users SET bonus_balance = bonus_balance - 1 WHERE user_id=$1", user_id)
            return {"type": "bonus", "success": True}
        else:
            return {"type": "none", "success": False}

async def refund_attempt(user_id: int, attempt_type: str):
    async with pool.acquire() as c:
        if attempt_type == "daily":
            await c.execute("UPDATE users SET daily_used_today = daily_used_today - 1 WHERE user_id=$1", user_id)
        elif attempt_type == "bonus":
            await c.execute("UPDATE users SET bonus_balance = bonus_balance + 1 WHERE user_id=$1", user_id)

async def log_request(user_id: int, score: int, mode: str):
    today = date.today()
    async with pool.acquire() as c:
        await c.execute(
            "INSERT INTO requests (user_id, date, mode, score, is_success) VALUES ($1, $2, $3, $4, $5)",
            user_id, today, mode, score, 1 if score > 0 else 0,
        )
        await c.execute("UPDATE users SET total_requests = total_requests + 1, points = points + 10 WHERE user_id=$1", user_id)

def _hash_image(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()

async def get_cached(image_bytes: bytes, mode: str) -> dict | None:
    h = _hash_image(image_bytes)
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT result_json FROM cache WHERE hash=$1 AND mode=$2", h, mode)
    return json.loads(row["result_json"]) if row else None

async def save_cache(image_bytes: bytes, mode: str, result: dict):
    h = _hash_image(image_bytes)
    async with pool.acquire() as c:
        await c.execute("INSERT INTO cache (hash, mode, result_json) VALUES ($1, $2, $3) ON CONFLICT (hash) DO UPDATE SET result_json = EXCLUDED.result_json", h, mode, json.dumps(result, ensure_ascii=False))

async def get_referral_count(user_id: int) -> int:
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT COUNT(*) as cnt FROM users WHERE referred_by=$1", user_id)
    return row["cnt"] if row else 0

async def add_referral_bonus(user_id: int) -> bool:
    async with pool.acquire() as c:
        await c.execute("INSERT INTO users (user_id) VALUES ($1) ON CONFLICT DO NOTHING", user_id)
        await c.execute("UPDATE users SET bonus_balance = bonus_balance + $1 WHERE user_id=$2", REFERRAL_BONUS, user_id)
    return True

async def get_weekly_top() -> list:
    seven_days_ago = (date.today() - timedelta(days=7))
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT u.username, u.user_id, COUNT(r.id) as cnt
            FROM users u JOIN requests r ON r.user_id = u.user_id
            WHERE r.date >= $1 AND r.is_success = TRUE
            GROUP BY u.user_id, u.username ORDER BY cnt DESC LIMIT 10
        """, seven_days_ago)
    return [(r["username"], r["user_id"], r["cnt"]) for r in rows]

async def get_top_referrers(limit: int = 10) -> list:
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT u1.username, u1.user_id, COUNT(u2.user_id) as refs
            FROM users u1 JOIN users u2 ON u2.referred_by = u1.user_id
            GROUP BY u1.user_id, u1.username ORDER BY refs DESC LIMIT $1
        """, limit)
    return [(r["username"], r["user_id"], r["refs"]) for r in rows]

async def get_full_stats() -> dict:
    today = date.today()
    async with pool.acquire() as c:
        total_users = (await c.fetchrow("SELECT COUNT(*) as c FROM users"))["c"]
        new_today = (await c.fetchrow("SELECT COUNT(*) as c FROM users WHERE DATE(first_seen) = $1", today))["c"]
        active_today = (await c.fetchrow("SELECT COUNT(DISTINCT user_id) as c FROM requests WHERE date = $1", today))["c"]
        requests_today = (await c.fetchrow("SELECT COUNT(*) as c FROM requests WHERE date = $1", today))["c"]
        requests_total = (await c.fetchrow("SELECT COUNT(*) as c FROM requests"))["c"]
        by_mode_rows = await c.fetch("SELECT mode, COUNT(*) as c FROM requests GROUP BY mode")
        cache_size = (await c.fetchrow("SELECT COUNT(*) as c FROM cache"))["c"]
        top_users = await c.fetch("""SELECT u.username, u.user_id, COUNT(r.id) as cnt FROM users u JOIN requests r ON r.user_id = u.user_id GROUP BY u.user_id, u.username ORDER BY cnt DESC LIMIT 5""")
        top_referrers = await c.fetch("""SELECT u.username, u.user_id, COUNT(u2.user_id) as refs FROM users u JOIN users u2 ON u2.referred_by = u.user_id GROUP BY u.user_id, u.username ORDER BY refs DESC LIMIT 5""")
    return {
        "total_users": total_users, "new_today": new_today, "active_today": active_today,
        "requests_today": requests_today, "requests_total": requests_total,
        "by_mode": {r["mode"]: r["c"] for r in by_mode_rows}, "cache_size": cache_size,
        "top_users": [(r["username"], r["user_id"], r["cnt"]) for r in top_users],
        "top_refs": [(r["username"], r["user_id"], r["refs"]) for r in top_referrers],
    }

async def get_ban_status(user_id: int) -> dict:
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT violations_count, banned_until, is_permanent FROM violations WHERE user_id=$1", user_id)
    if not row: return {"is_banned": False, "is_permanent": False, "violations": 0}
    count, banned_until, is_perm = row["violations_count"], row["banned_until"], row["is_permanent"]
    if is_perm: return {"is_banned": True, "is_permanent": True, "violations": count}
    if banned_until and banned_until > datetime.now():
        remaining = int((banned_until - datetime.now()).total_seconds() / 60)
        return {"is_banned": True, "is_permanent": False, "violations": count, "remaining_min": remaining}
    return {"is_banned": False, "is_permanent": False, "violations": count}

async def add_violation(user_id: int, reason: str = "мат/спам") -> dict:
    async with pool.acquire() as c:
        row = await c.fetchrow("SELECT violations_count FROM violations WHERE user_id=$1", user_id)
        count = (row["violations_count"] if row else 0) + 1
        if count >= 3:
            await c.execute("INSERT INTO violations (user_id, violations_count, is_permanent, reason) VALUES ($1, $2, TRUE, $3) ON CONFLICT (user_id) DO UPDATE SET violations_count = $2, is_permanent = TRUE", user_id, count, reason)
            return {"action": "permanent_ban", "count": count}
        elif count == 2:
            ban_until = datetime.now() + timedelta(minutes=30)
            await c.execute("INSERT INTO violations (user_id, violations_count, banned_until, reason) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO UPDATE SET violations_count = $2, banned_until = $3", user_id, count, ban_until, reason)
            return {"action": "temp_ban", "count": count, "minutes": 30}
        else:
            await c.execute("INSERT INTO violations (user_id, violations_count, reason) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET violations_count = $2", user_id, count, reason)
            return {"action": "warning", "count": count}

async def get_banned_users() -> list:
    async with pool.acquire() as c:
        rows = await c.fetch("""
            SELECT v.user_id, u.username, v.violations_count, v.banned_until, v.is_permanent, v.reason
            FROM violations v LEFT JOIN users u ON u.user_id = v.user_id
            WHERE v.is_permanent = TRUE OR (v.banned_until IS NOT NULL AND v.banned_until > NOW())
            ORDER BY v.is_permanent DESC, v.banned_until DESC
        """)
    return [(r["user_id"], r["username"], r["violations_count"], r["banned_until"], r["is_permanent"], r["reason"]) for r in rows]

async def pardon_user(user_id: int):
    async with pool.acquire() as c:
        await c.execute("DELETE FROM violations WHERE user_id=$1", user_id)
