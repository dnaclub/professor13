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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscribers (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                approved_at TEXT,
                expires_at  TEXT
            )
        """)
        await db.commit()

# /start: Payment ή Admin panel
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_USER_ID:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Λίστα Συνδρομητών", callback_data="panel_list")],
            [InlineKeyboardButton("🔄 Ανανέωση Συνδρομής", callback_data="panel_renew")],
            [InlineKeyboardButton("🗑️ Διαγραφή Συνδρομής", callback_data="panel_remove")]
        ])
        await update.message.reply_text("🔧 Admin Panel:", reply_markup=kb)
    else:
        keyboard = [
            ["🟢 Συνδρομή", "🔁 Ανανέωση"],
            ["📊 Στατιστικά", "📞 Επικοινωνία"]
        ]
        await update.message.reply_text(PAYMENT_MESSAGE, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# /subs: Εμφάνιση ενεργών συνδρομών (admin)
async def subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        return
    await init_db()
    text = "📋 Ενεργές Συνδρομές:\n"
    now = datetime.utcnow()
    found = False
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT user_id, username, expires_at FROM subscribers") as cursor:
            async for uid, uname, exp_at in cursor:
                found = True
                exp = datetime.fromisoformat(exp_at)
                days = (exp - now).days
                text += f"- {uname or uid} (ID:{uid}): λήγει σε {days} ημέρες ({exp.strftime('%d-%m-%Y')})\n"
    if not found:
        text += "Κανείς."
    await update.message.reply_text(text)

# Handle menu choices for users
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id

    if text == "🟢 Συνδρομή":
        await init_db()
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
        await update.message.reply_text("📩 Επικοινώνησε με τον admin: https://t.me/professorbetts")

# Screenshot handler: στέλνει στον admin για έγκριση
async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Στείλε φωτογραφία με απόδειξη πληρωμής.")
        return
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

# Approve callback: εγκρίνει συνδρομή
async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if update.effective_user.id != ADMIN_USER_ID:
        await query.edit_message_caption("❌ Δεν έχεις άδεια.", reply_markup=None)
        return

    user_id = int(query.data.split("_")[1])
    now = datetime.utcnow()
    expires = now + timedelta(days=SUB_DURATION)

    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            "INSERT OR REPLACE INTO subscribers (user_id, username, approved_at, expires_at) VALUES (?, ?, ?, ?)",
            (user_id, (await context.bot.get_chat(user_id)).username or str(user_id), now.isoformat(), expires.isoformat())
        )
        await db.commit()

    expires_str = expires.strftime('%d-%m-%Y')
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            f"✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n"
            f"{INVITE_LINK}\n\n"
            f"Η συνδρομή σου ισχύει μέχρι {expires_str}."
        )
    )
    await query.edit_message_caption("✅ Ο χρήστης εγκρίθηκε.", reply_markup=None)

# Admin panel callbacks
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "panel_list":
        await init_db()
        text = "📋 Συνδρομητές:\n"
        now = datetime.utcnow()
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT user_id, username, expires_at FROM subscribers") as cur:
                async for uid, uname, exp_at in cur:
                    exp = datetime.fromisoformat(exp_at)
                    days = (exp - now).days
                    text += f"- {uname or uid}: λήγει σε {days} ημέρες ({exp.strftime('%d-%m-%Y')})\n"
        await query.edit_message_text(text)

    elif data == "panel_renew":
        await query.edit_message_text("♻️ Στείλε το user_id που θες να ανανεώσεις.")
        context.user_data["admin_action"] = "renew"

    elif data == "panel_remove":
        await query.edit_message_text("🗑️ Στείλε το user_id που θες να διαγράψεις.")
        context.user_data["admin_action"] = "remove"

# Handle admin text after panel
async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    action = context.user_data.pop("admin_action", None)
    if not action or not update.message.text.isdigit():
        return
    uid = int(update.message.text)
    await init_db()
    async with aiosqlite.connect(DB_FILE) as db:
        if action == "renew":
            exp = datetime.utcnow() + timedelta(days=SUB_DURATION)
            await db.execute("UPDATE subscribers SET expires_at=? WHERE user_id=?", (exp.isoformat(), uid))
            await db.commit()
            await update.message.reply_text(f"♻️ Ανανεώθηκε η συνδρομή του {uid} έως {exp.strftime('%d-%m-%Y')}.")
        else:  # remove
            await db.execute("DELETE FROM subscribers WHERE user_id=?", (uid,))
            await db.commit()
            await update.message.reply_text(f"🗑️ Διαγράφηκε η συνδρομή του {uid}.")

# Main
def main():
    app = Application.builder().token(TOKEN).build()
    # Startup
    app.post_init = lambda app: asyncio.create_task(init_db())
    # Admin panel
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subs", subs))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern=r"^panel_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text), group=1)
    # User interactions
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(CallbackQueryHandler(approve_callback, pattern=r"^approve_\d+$"))
    logging.info("🤖 Bot τρέχει...")
    app.run_polling()

if __name__ == "__main__":
    main()
