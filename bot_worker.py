from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from config import TOKEN, ADMIN_USER_ID, INVITE_LINK, PAYMENT_MESSAGE

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PAYMENT_MESSAGE)

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
                caption=f"ΝΕΟ screenshot πληρωμής!\nUser: @{user.username or user.id}\nID: {user.id}",
                reply_markup=keyboard
            )
            await update.message.reply_text("📸 Η απόδειξή σου καταχωρήθηκε! Θα ενημερωθείς μόλις εγκριθεί.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Σφάλμα κατά την προώθηση στον admin: {e}")
    else:
        await update.message.reply_text("❌ Παρακαλώ στείλε screenshot ως εικόνα.")

async def button_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if user.id != ADMIN_USER_ID:
        await query.edit_message_caption(caption="⛔ Δεν έχεις άδεια να εγκρίνεις χρήστες.")
        return
    if query.data.startswith("approve_"):
        approved_user_id = int(query.data.split("_")[1])
        try:
            await context.bot.send_message(
                chat_id=approved_user_id,
                text="✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!\n\n" + INVITE_LINK
            )
            await query.edit_message_caption(
                caption="✅ Ο χρήστης εγκρίθηκε, καταχωρήθηκε και έλαβε το invite."
            )
        except Exception as e:
            await query.edit_message_caption(
                caption=f"⚠️ Σφάλμα κατά την έγκριση χρήστη: {e}"
            )

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, screenshot_handler))
    app.add_handler(CallbackQueryHandler(button_approve))
    app.run_polling()
