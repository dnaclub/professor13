import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, AIORateLimiter
)
from config import TOKEN, ADMIN_USER_ID, INVITE_LINK, PAYMENT_MESSAGE, CHANNEL_ID
from datetime import datetime, timedelta
import asyncio

DB_FILE = "subscribers.db"

# ------- DB INIT -------
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                join_date TEXT,
                expire_date TEXT,
                warned INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# ------- HANDLERS -------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Λάβαμε μήνυμα /start από:", update.effective_user.id)
    await update.message.reply_text(PAYMENT_MESSAGE)

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Δεν έχεις άδεια για αυτή την εντολή.")
        return
    try:
        user_id = int(context.args[0])
        await approve_user(context, user_id)
        await update.message.reply_text("🟢 Χρήστης προσκλήθηκε και καταχωρήθηκε.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Σφάλμα: {e}")

async def approve_user(context, user_id):
    now = datetime.utcnow()
    expire = now + timedelta(days=30)
    user = await context.bot.get_chat(user_id)
    async with aiosqlite.connect(DB_FILE) as db:
        await d
