from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TOKEN, ADMIN_USER_ID, INVITE_LINK

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Λάβαμε μήνυμα /start από:", update.effective_user.id)
    await update.message.reply_text("✅ Το bot είναι ΕΝΕΡΓΟ και επικοινωνεί! (Minimal Test)")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Δεν έχεις άδεια για αυτή την εντολή.")
        return
    try:
        user_id = int(context.args[0])
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n" + INVITE_LINK
        )
        await update.message.reply_text("🟢 Ο χρήστης έλαβε το invite.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Σφάλμα: {e}")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve))
    app.run_polling()
