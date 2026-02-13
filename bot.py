import os
import logging
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['📱 Commands', 'ℹ️ Info'], 
        ['🎥 Videos', '❤️ Support']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ @Heartwaychatbot LIVE 24/7!\n\n"
        "Choose a button:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **Help Menu**\n\n"
        "• /start - 🎬 Main menu\n"
        "• /help - ❓ Help\n"
        "• /info - ℹ️ Info\n\n"
        "**@Heartwaychatbot** ❤️"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ **Bot Info**\n\n"
        "• **Name**: @Heartwaychatbot\n"
        "• **Status**: 🟢 24/7 Online\n"
        "• **Hosted**: Railway\n"
        "• **Version**: v2.0\n\n"
        "**Educational bot by Heartway** 🎓"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "📱 Commands":
        await update.message.reply_text(
            "📋 **All Commands:**\n"
            "• /start - 🎬 Main Menu\n"
            "• /help - ❓ Help\n"
            "• /info - ℹ️ Info"
        )
    elif text == "ℹ️ Info":
        await info_command(update, context)
    elif text == "🎥 Videos":
        await update.message.reply_text(
            "📹 **Videos Coming Soon!**\n\n"
            "Subscribe @Heartwaychatbot for updates! ❤️"
        )
    elif text == "❤️ Support":
        await update.message.reply_text(
            "💖 **Support Heartway**\n\n"
            "**Share bot**: @Heartwaychatbot\n\n"
            "Thank you! 🙏"
        )
    else:
        await update.message.reply_text("❓ Use buttons below!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    
    app.run_polling()

if __name__ == "__main__":
    main()
