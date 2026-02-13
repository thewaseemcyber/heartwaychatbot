import os
from telegram.ext import Application, CommandHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
app = Application.builder().token(BOT_TOKEN).build()

async def start(update, context):
    await update.message.reply_text("✅ @Heartwaychatbot LIVE 24/7!")

async def help_command(update, context):
    await update.message.reply_text("🆘 **Help Menu**\n\n/start - Main menu\n/help - Show this help\n\n**@Heartwaychatbot** ❤️")

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.run_polling()
