# Δημιουργία αρχείου bot_payment_photo.py με πλήρη κώδικα συμπεριλαμβάνοντας /subs

bot_code = """
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
    filters,
)
from config import TOKEN, ADMIN_USER_ID, INVITE_LINK, PAYMENT_MESSAGE, CHANNEL_ID, DB_FILE

# Διάρκεια συνδρομής (ημέρες)
SUB_DURATION = 30

# Logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

# Δημιουργία πίνακα αν δεν υπάρχει
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(\"\"\"
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                approved_at TEXT,
                expires_at  TEXT
            )
        \"\"\")
        await db.commit()

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await init_db()
    await update.message.reply_text(
        PAYMENT_MESSAGE,
        reply_markup=ReplyKeyboardMarkup(
            [["🟢 Συνδρομή", "🔁 Ανανέωση"], ["📊 Στατιστικά", "📞 Επικοινωνία"]],
            resize_keyboard=True
        )
    )

# /subs handler for admin
async def subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await init_db()
    text = "📋 Ενεργές Συνδρομές:\\n"
    now = datetime.utcnow()
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username, expires_at FROM subscribers") as cursor:
            found = False
            async for user_id, username, expires_at in cursor:
                found = True
                exp = datetime.fromisoformat(expires_at)
                left = (exp - now).days
                text += f"- {username or user_id} (ID: {user_id}): λήγει σε {left} ημέρες ({exp.strftime('%d-%m-%Y')})\\n"
    if not found:
        text += "Κανείς."
    await update.message.reply_text(text)

# Menu handler
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "🟢 Συνδρομή":
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT expires_at FROM subscribers WHERE user_id=?", (uid,)) as cur:
                row = await cur.fetchone()
        if not row:
            await update.message.reply_text("❌ Δεν έχεις ενεργή συνδρομή.")
        else:
            exp = datetime.fromisoformat(row[0])
            days = (exp - datetime.utcnow()).days
            await update.message.reply_text(
                f"✅ Η συνδρομή σου λήγει σε {days} ημέρες, στις {exp.strftime('%d-%m-%Y')}."
            )

    elif text == "🔁 Ανανέωση":
        await update.message.reply_text("🔁 Στείλε screenshot απόδειξης πληρωμής εδώ για ανανέωση.")

    elif text == "📊 Στατιστικά":
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📈 Δες Στατιστικά", url="https://app.bet-analytix.com/bankroll/1051507")
        ]])
        await update.message.reply_text("📊 Στατιστικά:", reply_markup=kb)

    elif text == "📞 Επικοινωνία":
        await update.message.reply_text(f"📩 Επικοινώνησε με τον admin: https://t.me/professorbetts")

# Screenshot handler
async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        return await update.message.reply_text("❌ Στείλε την απόδειξη ως φωτογραφία.")
    user = update.effective_user
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ APPROVE", callback_data=f"approve_{user.id}")
    ]])
    await context.bot.send_photo(
        chat_id=ADMIN_USER_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"📸 Απόδειξη από @{user.username or user.id}",
        reply_markup=kb
    )
    await update.message.reply_text("📸 Η απόδειξή σου εστάλη! Περιμένετε έγκριση.")

# Approve callback
async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_USER_ID:
        return await query.edit_message_caption("❌ Δεν έχεις άδεια.", reply_markup=None)

    user_id = int(query.data.split("_")[1])
    now = datetime.utcnow()
    expires = now + timedelta(days=SUB_DURATION)

    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscribers (user_id, username, approved_at, expires_at) VALUES (?, ?, ?, ?)",
            (
                user_id,
                (await context.bot.get_chat(user_id)).username or str(user_id),
                now.isoformat(),
                expires.isoformat()
            )
        )
        await db.commit()

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\\n\\n"
            f"{INVITE_LINK}\\n\\n"
            f"Η συνδρομή σου ισχύει μέχρι {expires.strftime('%d-%m-%Y')}."
        )
    )
    await query.edit_message_caption("✅ Ο χρήστης εγκρίθηκε.", reply_markup=None)

# Main
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subs", subs))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(CallbackQueryHandler(approve_callback, pattern=r"^approve_\\d+$"))
    print("🤖 Bot τρέχει...")
    app.run_polling()

if __name__ == "__main__":
    main()
"""

# Save the file
with open("/mnt/data/bot_payment_photo.py", "w") as f:
    f.write(bot_code)

"/mnt/data/bot_payment_photo.py created"
