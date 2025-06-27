import logging
import aiosqlite
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import TOKEN, ADMIN_USER_ID, INVITE_LINK, PAYMENT_MESSAGE, CHANNEL_ID

DB_FILE = "subscribers.db"
SUB_DURATION = 0.0035  # ~5 λεπτά (5 / 1440)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- SQLite Setup ---
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

# --- /start Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"/start from {update.effective_user.id}")
    await update.message.reply_text(PAYMENT_MESSAGE)

# --- /subs για admin ---
async def subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    text = "📋 Ενεργές Συνδρομές:\n"
    now = datetime.utcnow()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username, expires_at FROM subscribers") as cursor:
            async for user_id, username, expires_at in cursor:
                expires = datetime.fromisoformat(expires_at)
                left = (expires - now).days
                expires_str = expires.strftime("%d-%m-%Y %H:%M")
                text += f"- {username or user_id} (ID: {user_id}): λήγει σε {left} μέρες ({expires_str})\n"
    await update.message.reply_text(text or "Δεν υπάρχουν ενεργές συνδρομές.")

# --- Screenshot Handler ---
async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        await update.message.reply_text("❌ Παρακαλώ στείλε screenshot ως φωτογραφία!")
        return
    user = update.effective_user
    caption = f"🆕 Screenshot από @{user.username or user.id}\n\nApprove;"
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user.id}")]
    ])
    await context.bot.send_photo(
        chat_id=ADMIN_USER_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption,
        reply_markup=kb
    )
    await update.message.reply_text("📸 Η απόδειξή σου καταχωρήθηκε! Θα ενημερωθείς μόλις εγκριθεί.")

# --- Approve Handler ---
async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_USER_ID:
        await query.edit_message_caption("❌ Δεν έχεις άδεια για approve.", reply_markup=None)
        return

    user_id = int(query.data.split("_")[1])
    username = None
    try:
        chat = await context.bot.get_chat(user_id)
        username = chat.username
    except Exception:
        username = str(user_id)

    now = datetime.utcnow()
    expires = now + timedelta(days=SUB_DURATION)

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscribers (user_id, username, approved_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, username, now.isoformat(), expires.isoformat())
        )
        await db.commit()

    # Invite user
    try:
        expires_str = expires.strftime("%d-%m-%Y %H:%M")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n{INVITE_LINK}\n\nΗ συνδρομή σου ισχύει μέχρι {expires_str}."
        )
        await query.edit_message_caption("✅ Ο χρήστης εγκρίθηκε, καταχωρήθηκε και έλαβε το invite.", reply_markup=None)
    except Exception as e:
        await query.edit_message_caption(f"⚠️ Σφάλμα invite: {e}", reply_markup=None)

# --- Έλεγχος Ληγμένων Συνδρομών ---
async def check_expired_users(app: Application):
    logging.info("✅ Τρέχει έλεγχος για ληγμένες συνδρομές...")
    now = datetime.utcnow()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username, expires_at FROM subscribers") as cursor:
            to_remove = []
            notify3 = []
            notify1 = []
            async for user_id, username, expires_at in cursor:
                expires = datetime.fromisoformat(expires_at)
                left = (expires - now).total_seconds()
                if left <= 0:
                    logging.info(f"❌ Ληγμένη συνδρομή για {user_id} - διαγράφεται")
                    to_remove.append((user_id, username))
                elif 60 * 60 * 24 * 3 - 60 < left < 60 * 60 * 24 * 3 + 60:
                    notify3.append((user_id, expires))
                elif 60 * 60 * 24 - 60 < left < 60 * 60 * 24 + 60:
                    notify1.append((user_id, expires))

        # Διαγραφή
        for user_id, username in to_remove:
            try:
                await app.bot.ban_chat_member(CHANNEL_ID, user_id)
                await app.bot.send_message(
                    chat_id=user_id,
                    text="❌ Η συνδρομή σου έληξε και αφαιρέθηκες από το κανάλι. Για ανανέωση: επικοινώνησε με τον admin."
                )
            except Exception as e:
                logging.error(f"⚠️ Αποτυχία αφαίρεσης χρήστη {user_id}: {e}")
            await db.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
        await db.commit()

        # Υπενθυμίσεις
        for user_id, _ in notify3:
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text="🔔 Η συνδρομή σου λήγει σε 3 μέρες. Επικοινώνησε για ανανέωση!"
                )
            except: pass
        for user_id, _ in notify1:
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text="🔔 Η συνδρομή σου λήγει αύριο. Επικοινώνησε για ανανέωση!"
                )
            except: pass

# --- Εκκίνηση ---
async def on_startup(app: Application):
    await init_db()
    # Έλεγχος ληγμένων κάθε 60 δευτερόλεπτα
    app.job_queue.run_repeating(
        lambda _: asyncio.create_task(check_expired_users(app)),
        interval=60,  # κάθε 1 λεπτό
        first=3
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subs", subs))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(CallbackQueryHandler(approve_callback, pattern=r"^approve_\\d+$"))
    app.post_init = on_startup
    print("✅ Το bot είναι ΕΝΕΡΓΟ σε test mode (5 λεπτών)")
    app.run_polling()

if __name__ == "__main__":
    main()
