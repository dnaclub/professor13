import logging
import aiosqlite
import asyncio
from datetime import datetime
from telegram.ext import Application
from config import TOKEN, DB_FILE  # Πρέπει να έχεις DB_FILE = "subscribers.db" στο config.py

# Μηνύματα
REMINDER_3_DAYS = "🔔 Η συνδρομή σου λήγει σε 3 μέρες. Επικοινώνησε για ανανέωση!"
REMINDER_1_DAY = "🔔 Η συνδρομή σου λήγει αύριο. Επικοινώνησε άμεσα για ανανέωση!"

# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def notify_users(bot):
    logging.info("📢 Έναρξη αποστολής υπενθυμίσεων")
    now = datetime.utcnow()

    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, expires_at FROM subscribers") as cursor:
            async for user_id, expires_at in cursor:
                try:
                    expires = datetime.fromisoformat(expires_at)
                    days_left = (expires - now).days

                    if days_left == 3:
                        await bot.send_message(chat_id=user_id, text=REMINDER_3_DAYS)
                        logging.info(f"✅ Υπενθύμιση 3 ημερών σε {user_id}"_
