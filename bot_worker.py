import logging
import aiosqlite
import asyncio
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from config import TOKEN, ADMIN_USER_ID, INVITE_LINK, PAYMENT_MESSAGE, CHANNEL_ID, DB_FILE

# Διάρκεια συνδρομής (ημέρες)
SUB_DURATION = 30

# Ρύθμιση logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# --- Δημιουργία πίνακα αν δεν υπάρχει ---
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

# --- Menu Buttons ---
def main_menu():
    keyboard = [
        ["🟢 Συνδρομή", "🔁 Ανανέωση"],
        ["📊 Στατιστικά", "📞 Επικοινωνία"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- /start: Ζητάει payment ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await init_db()
    await update.message.reply_text(PAYMENT_MESSAGE, reply_markup=main_menu())

# --- Διαχείριση κειμένου μενού ---
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id

    if text == "🟢 Συνδρομή":
        # Έλεγχος υπολοίπου
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT expires_at FROM subscribers WHERE user_id=?", (user_id,)) as cursor:
                row = await cursor.fetchone()
        if not row:
            await update.message.reply_text("❌ Δεν έχεις ενεργή συνδρομή.")
        else:
            expires = datetime.fromisoformat(row[0])
            days = (expires - datetime.utcnow()).days
            await update.message.reply_text(
                f"✅ Η συνδρομή σου λήγει σε {days} ημέρες, στις {expires.strftime('%d-%m-%Y')}."
            )

    elif text == "🔁 Ανανέωση":
        await update.message.reply_text(
            "🔁 Στείλε screenshot απόδειξης πληρωμής εδώ για ανανέωση."
        )

    elif text == "📊 Στατιστικά":
        buttons = [[
            InlineKeyboardButton("📈 Δες Στατιστικά", url="https://app.bet-analytix.com/bankroll/1051507")
        ]]
        await update.message.reply_text(
            "📊 Στατιστικά:", reply_markup=InlineKeyboardMarkup(buttons)
        )

    elif text == "📞 Επικοινωνία":
        await update.message.reply_text(
            f"📩 Επικοινώνησε με τον admin: https://t.me/professorbetts"
        )

# --- Screenshot handler: δέχεται φωτογραφία ---
async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Στείλε σε φωτογραφία την απόδειξη πληρωμής.")
        return
    user = update.effective_user
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user.id}")]
    ])
    await context.bot.send_photo(
        chat_id=ADMIN_USER_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"📸 Απόδειξη από @{user.username or user.id}",
        reply_markup=kb
    )
    await update.message.reply_text("📸 Η απόδειξή σου εστάλη! Περιμένετε έγκριση.")

# --- Approve Callback ---
async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_USER_ID:
        await query.edit_message_caption("❌ Δεν έχεις άδεια.", reply_markup=None)
        return

    user_id = int(query.data.split("_")[1])
    now = datetime.utcnow()
    expires = now + timedelta(days=SUB_DURATION)

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscribers (user_id, username, approved_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, (await context.bot.get_chat(user_id)).username, now.isoformat(), expires.isoformat())
        )
        await db.commit()

    expires_str = expires.strftime("%d-%m-%Y")
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n"
            f"{INVITE_LINK}\n\n"
            f"Η συνδρομή σου ισχύει μέχρι {expires_str}."
        )
    )
    await query.edit_message_caption("✅ Ο χρήστης εγκρίθηκε.", reply_markup=None)

# --- Main ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    # Σωστό pattern με μία backslash
    app.add_handler(CallbackQueryHandler(approve_callback, pattern=r"^approve_\d+$"))
    print("🤖 Bot τρέχει...")
    app.run_polling()

if __name__ == "__main__":
    main()
