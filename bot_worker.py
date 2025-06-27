import logging
import aiosqlite
import asyncio
from datetime import datetime
from telegram.ext import Application
from config import TOKEN, DB_FILE  # Φρόντισε το config.py να έχει DB_FILE = "subscribers.db"

# Μηνύματα υπενθύμισης
REMINDER_3_DAYS = "🔔 Η συνδρομή σου λήγει σε 3 μέρες. Επικοινώνησε για ανανέωση!"
REMINDER_1_DAY  = "🔔 Η συνδρομή σου λήγει αύριο. Επικοινώνησε άμεσα για ανανέωση!"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Δημιουργεί τον πίνακα αν δεν υπάρχει
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                approved_at TEXT,
                expires_at TEXT
            )
        """)
        await db.commit()

# Στέλνει υπενθυμίσεις
async def notify_users(bot):
    logging.info("📢 Έναρξη αποστολής υπενθυμίσεων")
    now = datetime.utcnow()

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, expires_at FROM subscribers") as cursor:
            async for user_id, expires_at in cursor:
                try:
                    expires   = datetime.fromisoformat(expires_at)
                    days_left = (expires - now).days

                    if days_left == 3:
                        await bot.send_message(chat_id=user_id, text=REMINDER_3_DAYS)
                        logging.info(f"✅ Υπενθύμιση 3 ημερών σε {user_id}")
                    elif days_left == 1:
                        await bot.send_message(chat_id=user_id, text=REMINDER_1_DAY)
                        logging.info(f"✅ Υπενθύμιση 1 ημέρας σε {user_id}")

                except Exception as e:
                    logging.error(f"❌ Σφάλμα αποστολής σε {user_id}: {e}")

# Κύρια συνάρτηση
async def main():
    await init_db()
    app = Application.builder().token(TOKEN).build()
    await notify_users(app.bot)

if __name__ == "__main__":
    asyncio.run(main())
