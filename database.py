import aiosqlite
import asyncio
from datetime import datetime

DB_PATH = "tarot.db"
db = None  # global connection

async def init_db():
    global db
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            card_of_day_date TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            payload TEXT,
            stars INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    await db.commit()
    return db

async def save_user(user_id: int, username: str, first_name: str):
    global db
    await db.execute(
        "INSERT OR IGNORE INTO users (id, username, first_name) VALUES (?, ?, ?)",
        (user_id, username, first_name)
    )
    await db.commit()

async def save_payment(user_id: int, payload: str, stars: int):
    global db
    await db.execute(
        "INSERT INTO payments (user_id, payload, stars) VALUES (?, ?, ?)",
        (user_id, payload, stars)
    )
    await db.commit()

async def get_stats():
    global db
    async with db.execute("SELECT COUNT(*) as cnt FROM users") as cur:
        users = (await cur.fetchone())["cnt"]
    async with db.execute("SELECT COUNT(*) as cnt FROM payments") as cur:
        payments = (await cur.fetchone())["cnt"]
    async with db.execute("SELECT SUM(stars) as total FROM payments") as cur:
        stars = (await cur.fetchone())["total"] or 0
    return users, payments, stars

async def check_card_of_day(user_id: int) -> bool:
    """Returns True if user already got card today"""
    global db
    today = datetime.now().strftime("%Y-%m-%d")
    async with db.execute(
        "SELECT card_of_day_date FROM users WHERE id=?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
        if row and row["card_of_day_date"] == today:
            return True
    await db.execute(
        "UPDATE users SET card_of_day_date=? WHERE id=?", (today, user_id)
    )
    await db.commit()
    return False
