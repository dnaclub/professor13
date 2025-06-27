from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

# Βάλε το νέο σου TOKEN εδώ ή άφησε να το παίρνει από config.py!
TOKEN = os.getenv("TOKEN", "8080558645:AAFNVY_gFZWSINjJ6kIdHTFz4KBcSti6R48")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Λάβαμε μήνυμα /start από:", update.effective_user.id)
    await update.message.reply_text("✅ Το bot είναι ΕΝΕΡΓΟ και επικοινωνεί! (Minimal Test)")

if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
