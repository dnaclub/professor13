# Δημιουργία πλήρους αρχείου telegram bot με:
# - διαχείριση συνδρομής
# - αποδοχή screenshot
# - approve
# - διαγραφή ληγμένων
# - αποστολή invite
# - inline buttons
# - υπενθύμιση μέσω job

bot_full_code = """
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
SUB_DURATION = 30  # days

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)

# --- SQLite Setup ---
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(\"""
        CREATE TABLE IF NOT EXISTS subscribers (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            approved_at TEXT,
            expires_at TEXT
        )
        \""")
        await db.commit()

# --- Menu Buttons ---
def main_menu():
    buttons = [
        [InlineKeyboardButton("📥 Συνδρομή", callback_data="menu_subscribe")],
        [InlineKeyboardButton("🔄 Ανανέωση", callback_data="menu_renew")],
        [InlineKeyboardButton("📊 Στατιστικά", url="https://app.bet-analytix.com/bankroll/1051507")],
        [InlineKeyboardButton("📬 Επικοινωνία", url="https://t.me/professorbetts")]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        PAYMENT_MESSAGE,
        reply_markup=main_menu()
    )

async def subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    text = "Ενεργές Συνδρομές:\n"
    now = datetime.utcnow()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username, expires_at FROM subscribers") as cursor:
            async for user_id, username, expires_at in cursor:
                expires = datetime.fromisoformat(expires_at)
                left = (expires - now).days
                expires_str = expires.strftime("%d-%m-%Y")
                text += f"- {username or user_id} (ID: {user_id}): λήγει σε {left} μέρες ({expires_str})\n"
    await update.message.reply_text(text)

# --- Screenshot Handler ---
async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.photo:
        await update.message.reply_text("❌ Παρακαλώ στείλε screenshot ως φωτογραφία!")
        return
    user = update.effective_user
    caption = f"🆕 Screenshot από @{user.username or user.id}\\n\\nApprove;"
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

# --- Approve Callback ---
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
    except:
        username = str(user_id)
    now = datetime.utcnow()
    expires = now + timedelta(days=SUB_DURATION)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscribers (user_id, username, approved_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, username, now.isoformat(), expires.isoformat())
        )
        await db.commit()
    try:
        expires_str = expires.strftime("%d-%m-%Y")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n{INVITE_LINK}\n\nΗ συνδρομή σου ισχύει μέχρι {expires_str}."
        )
        await query.edit_message_caption("✅ Ο χρήστης εγκρίθηκε και έλαβε το invite.", reply_markup=None)
    except Exception as e:
        await query.edit_message_caption(f"⚠️ Σφάλμα invite: {e}", reply_markup=None)

# --- Auto-check Expired Users ---
async def check_expired_users(app: Application):
    now = datetime.utcnow()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username, expires_at FROM subscribers") as cursor:
            to_remove = []
            notify3 = []
            notify1 = []
            async for user_id, username, expires_at in cursor:
                expires = datetime.fromisoformat(expires_at)
                left = (expires - now).days
                if left <= 0:
                    to_remove.append((user_id, username))
                elif left == 3:
                    notify3.append((user_id, expires))
                elif left == 1:
                    notify1.append((user_id, expires))
        for user_id, username in to_remove:
            try:
                await app.bot.ban_chat_member(CHANNEL_ID, user_id)
                await app.bot.send_message(
                    chat_id=user_id,
                    text="❌ Η συνδρομή σου έληξε και αφαιρέθηκες από το κανάλι. Για ανανέωση επικοινώνησε με τον admin."
                )
            except Exception as e:
                logging.error(f"Remove user {user_id} failed: {e}")
            await db.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
        await db.commit()
        for user_id, _ in notify3:
            try:
                await app.bot.send_message(chat_id=user_id, text="🔔 Σε 3 μέρες λήγει η συνδρομή σου.")
            except: pass
        for user_id, _ in notify1:
            try:
                await app.bot.send_message(chat_id=user_id, text="🔔 Η συνδρομή σου λήγει αύριο.")
            except: pass

# --- Startup Init ---
async def on_startup(app: Application):
    await init_db()
    app.job_queue.run_repeating(lambda _: asyncio.create_task(check_expired_users(app)), interval=86400, first=3)

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subs", subs))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(CallbackQueryHandler(approve_callback, pattern=r"^approve_\\d+$"))
    app.post_init = on_startup
    print("🤖 Bot είναι ενεργό!")
    app.run_polling()

if __name__ == "__main__":
    main()
"""

with open("/mnt/data/bot_full.py", "w") as f:
    f.write(bot_full_code)
