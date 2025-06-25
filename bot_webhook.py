import os
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.ext import AIORateLimiter
from config import TOKEN, ADMIN_USERNAME, INVITE_LINK, PAYMENT_MESSAGE

import logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
bot = Bot(token=TOKEN)

application = Application.builder().token(TOKEN).rate_limiter(AIORateLimiter()).build()

user_screenshots = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(PAYMENT_MESSAGE)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        user_id = update.effective_user.id
        username = update.effective_user.username
        caption = f"📸 Νέα απόδειξη από @{username} (ID: {user_id})"
        user_screenshots[user_id] = True
        await bot.send_photo(chat_id=ADMIN_USERNAME, photo=update.message.photo[-1].file_id, caption=caption)
        await update.message.reply_text("📨 Ελήφθη η απόδειξή σου! Θα σε ειδοποιήσουμε σύντομα.")
    else:
        await update.message.reply_text(PAYMENT_MESSAGE)

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != ADMIN_USERNAME.replace("@", ""):
        await update.message.reply_text("❌ Δεν έχεις δικαίωμα για αυτή την εντολή.")
        return
    if not context.args:
        await update.message.reply_text("Χρήση: /approve <user_id>")
        return
    user_id = int(context.args[0])
    try:
        await bot.send_message(chat_id=user_id, text=f"✅ Επιβεβαιώθηκε η πληρωμή σου! Μπες στο κανάλι: {INVITE_LINK}")
        await update.message.reply_text(f"Ο χρήστης {user_id} προσκλήθηκε.")
    except Exception as e:
        await update.message.reply_text(f"Σφάλμα: {str(e)}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("approve", approve))
application.add_handler(MessageHandler(filters.ALL, handle_message))

@app.route("/webhook", methods=["POST"])
async def webhook() -> str:
    update = Update.de_json(request.get_json(force=True), bot)
    await application.process_update(update)
    return "OK"

if __name__ == "__main__":
    app.run(port=8080)