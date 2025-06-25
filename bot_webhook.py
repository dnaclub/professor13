from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.ext import AIORateLimiter
import logging
import os

# Ρυθμίσεις bot
TOKEN = "8080558645:AAEOMT4XeXtiK2Tj9AmxL9rLCMjE5l4Y-P8"

# Ρύθμιση logging
logging.basicConfig(level=logging.INFO)

# Flask app
app = Flask(__name__)
bot = Bot(token=TOKEN)

# Telegram application
application = Application.builder().token(TOKEN).rate_limiter(AIORateLimiter()).build()

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Γεια σου! Το bot είναι online και λειτουργεί.")

# Καταχώριση handler
application.add_handler(CommandHandler("start", start))

# Webhook route
@app.route("/webhook", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    await application.process_update(update)
    return "OK"

# Εκκίνηση Flask server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
