import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from config import TOKEN, ADMIN_USERNAME, INVITE_LINK, PAYMENT_MESSAGE

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PAYMENT_MESSAGE)

# /approve handler
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != ADMIN_USERNAME:
        await update.message.reply_text("❌ Δεν έχεις άδεια για αυτή την εντολή.")
        return
    try:
        user_id = int(context.args[0])
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ Η πληρωμή σου εγκρίθηκε! Καλώς ήρθες!

" + INVITE_LINK
        )
        await update.message.reply_text("🟢 Χρήστης προσκλήθηκε.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Σφάλμα: {e}")

# Καταχώριση handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("approve", approve))

# Webhook (sync με init)
@app.route("/webhook", methods=["POST"])
def webhook():
    print("===> Webhook called")
    update = Update.de_json(request.get_json(force=True), application.bot)
    async def process():
        print("===> Initializing app")
        await application.initialize()
        print("===> Processing update")
        await application.process_update(update)
    asyncio.run(process())
    return "OK"

if __name__ == "__main__":
    print("===> Starting Flask app on port 8080")
    app.run(host="0.0.0.0", port=8080)