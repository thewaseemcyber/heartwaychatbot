import os
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
app = Application.builder().token(BOT_TOKEN).build()

async def start(update, context):
    await update.message.reply_text("✅ **@Heartwaychatbot LIVE 24/7!** 🎉")

app.add_handler(CommandHandler("start", start))
app.run_polling()
