from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import TOKEN, ADMIN_USERNAME, INVITE_LINK, PAYMENT_MESSAGE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PAYMENT_MESSAGE)

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Δεν έχεις άδεια για αυτή την εντολή.")
        return
    try:
        user_id = int(context.args[0])
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n" + INVITE_LINK
        )
        await update.message.reply_text("🟢 Χρήστης προσκλήθηκε.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Σφάλμα: {e}")

async def screenshot_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ελέγχει αν υπάρχει μήνυμα και αν είναι photo
    if update.message and update.message.photo:
        user = update.effective_user
        file_id = update.message.photo[-1].file_id
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✅ Έγκριση", callback_data=f"approve_{user.id}")]]
        )
        try:
            await context.bot.send_photo(
                chat_id=ADMIN_USERNAME,
                photo=file_id,
                caption=f"ΝΕΟ screenshot πληρωμής!\nUser: @{user.username} | ID: {user.id}",
                reply_markup=keyboard
            )
            await update.message.reply_text("📸 Η απόδειξή σου καταχωρήθηκε! Θα ενημερωθείς μόλις εγκριθεί.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Σφάλμα κατά την προώθηση στον admin: {e}")
    else:
        # Ασφαλής απάντηση μόνο αν υπάρχει μήνυμα
        if update.message:
            await update.message.reply_text("❌ Παρακαλώ στείλε φωτογραφία/screenshot ως αρχείο εικόνας.")

async def button_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user

    # Μόνο admin μπορεί να εγκρίνει
    if user.username != ADMIN_USERNAME:
        await query.edit_message_caption(caption="⛔ Δεν έχεις άδεια να εγκρίνεις χρήστες.")
        return

    # Παίρνει το user_id από το callback_data
    if query.data.startswith("approve_"):
        approved_user_id = int(query.data.split("_")[1])
        await context.bot.send_message(
            chat_id=approved_user_id,
            text="✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n" + INVITE_LINK
        )
        await query.edit_message_caption(
            caption="✅ Ο χρήστης εγκρίθηκε και έλαβε το invite."
        )

if __name__ == "__main__":
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    application.add_handler(CallbackQueryHandler(button_approve))
    application.run_polling()
