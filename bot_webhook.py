from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.ext import AIORateLimiter
from config import TOKEN, ADMIN_USERNAME, INVITE_LINK, PAYMENT_MESSAGE

app = Flask(__name__)
bot = Bot(token=TOKEN)
application = Application.builder().token(TOKEN).rate_limiter(AIORateLimiter()).build()

user_screenshots = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PAYMENT_MESSAGE)

async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        user_screenshots[user.id] = file_id
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📤 Το screenshot ελήφθη. Περιμένει έγκριση.")
        await context.bot.send_photo(chat_id=ADMIN_USERNAME, photo=file_id, caption=f"👤 @{user.username} | ID: {user.id}")
    else:
        await update.message.reply_text("❌ Παρακαλώ στείλε screenshot ως φωτογραφία.")

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text("⛔ Δεν έχεις δικαίωμα έγκρισης.")
        return
    if not context.args:
        await update.message.reply_text("❗ Χρήση: /approve <user_id>")
        return
    try:
        user_id = int(context.args[0])
        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!

{INVITE_LINK}"
        )
        await update.message.reply_text("🟢 Χρήστης προσκλήθηκε.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Σφάλμα: {e}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("approve", approve))
application.add_handler(MessageHandler(filters.PHOTO, handle_screenshot))

@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await application.process_update(update)
    return "OK"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)