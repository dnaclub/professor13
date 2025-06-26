import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
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
        await db.execute(
            "INSERT OR REPLACE INTO subscribers (user_id, username, join_date, expire_date, warned) VALUES (?, ?, ?, ?, 0)",
            (user_id, user.username, now.isoformat(), expire.isoformat())
        )
        await db.commit()
    await context.bot.send_message(
        chat_id=user_id,
        text="✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n" + INVITE_LINK
    )

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.photo:
        user = update.effective_user
        file_id = update.message.photo[-1].file_id
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Έγκριση", callback_data=f"approve_{user.id}")]]
        )
        try:
            await context.bot.send_photo(
                chat_id=ADMIN_USER_ID,
                photo=file_id,
                caption=f"ΝΕΟ screenshot πληρωμής!\nUser: @{user.username} | ID: {user.id}",
                reply_markup=keyboard
            )
            await update.message.reply_text("📸 Η απόδειξή σου καταχωρήθηκε! Θα ενημερωθείς μόλις εγκριθεί.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Σφάλμα κατά την προώθηση στον admin: {e}")
    else:
        if update.message:
            await update.message.reply_text("❌ Παρακαλώ στείλε φωτογραφία/screenshot ως αρχείο εικόνας.")

async def button_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if user.id != ADMIN_USER_ID:
        await query.edit_message_caption(caption="⛔ Δεν έχεις άδεια να εγκρίνεις χρήστες.")
        return
    if query.data.startswith("approve_"):
        approved_user_id = int(query.data.split("_")[1])
        await approve_user(context, approved_user_id)
        await query.edit_message_caption(
            caption="✅ Ο χρήστης εγκρίθηκε, καταχωρήθηκε και έλαβε το invite."
        )

# ------- AUTO CHECK -------
async def check_expired_users(app: Application):
    while True:
        now = datetime.utcnow()
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT user_id, username, expire_date, warned FROM subscribers") as cursor:
                async for row in cursor:
                    user_id, username, expire_date, warned = row
                    expire_dt = datetime.fromisoformat(expire_date)
                    days_left = (expire_dt - now).days

                    # 1. Ειδοποίηση 3 μέρες πριν
                    if 0 < days_left <= 3 and not warned:
                        try:
                            await app.bot.send_message(
                                chat_id=user_id,
                                text="🔔 Η συνδρομή σου λήγει σε {} μέρες. Για ανανέωση, πλήρωσε ξανά και στείλε απόδειξη!".format(days_left)
                            )
                            await db.execute("UPDATE subscribers SET warned=1 WHERE user_id=?", (user_id,))
                            await db.commit()
                        except Exception:
                            pass

                    # 2. Kick όταν λήξει
                    if now >= expire_dt:
                        try:
                            # Προσπάθησε να αφαιρέσεις από το κανάλι (αν είναι ακόμα μέλος)
                            await app.bot.ban_chat_member(CHANNEL_ID, user_id)
                            await app.bot.unban_chat_member(CHANNEL_ID, user_id)
                        except Exception:
                            pass
                        try:
                            await app.bot.send_message(
                                chat_id=user_id,
                                text="❌ Η συνδρομή σου έληξε και αφαιρέθηκες από το κανάλι."
                            )
                        except Exception:
                            pass
                        await db.execute("DELETE FROM subscribers WHERE user_id=?", (user_id,))
                        await db.commit()
        await asyncio.sleep(3600)  # έλεγχος κάθε 1 ώρα

# ------- MAIN -------
if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db())

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    application.add_handler(CallbackQueryHandler(button_approve))

    # Βάζουμε το background task για έλεγχο λήξης
    application.job_queue.run_once(lambda c: asyncio.create_task(check_expired_users(application)), when=1)

    application.run_polling()
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, AIORateLimiter

async def background_check(context: ContextTypes.DEFAULT_TYPE):
    await check_expired_users(context.application)

if __name__ == "__main__":
    import asyncio

    asyncio.run(init_db())

    application = Application.builder().token(TOKEN).rate_limiter(AIORateLimiter()).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    application.add_handler(CallbackQueryHandler(button_approve))

    # Προσθέτουμε το job κάθε ώρα
    application.job_queue.run_repeating(background_check, interval=3600, first=10)

    application.run_polling()
