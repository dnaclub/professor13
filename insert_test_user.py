
import aiosqlite
import asyncio
from datetime import datetime, timedelta

DB_FILE = "subscribers.db"

# ✅ Το Telegram ID σου
TEST_USER_ID = 7189542392
USERNAME = "testuser"
DAYS_UNTIL_EXPIRY = 3  # Βάλε 1 για υπενθύμιση 1 μέρας

async def insert_test_user():
    now = datetime.utcnow()
    expires = now + timedelta(days=DAYS_UNTIL_EXPIRY)

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                approved_at TEXT,
                expires_at TEXT
            )
        """)
        await db.execute(
            "INSERT OR REPLACE INTO subscribers (user_id, username, approved_at, expires_at) VALUES (?, ?, ?, ?)",
            (TEST_USER_ID, USERNAME, now.isoformat(), expires.isoformat())
        )
        await db.commit()
        print(f"✅ Προστέθηκε χρήστης {USERNAME} με λήξη σε {DAYS_UNTIL_EXPIRY} μέρες.")

if __name__ == "__main__":
    asyncio.run(insert_test_user())
