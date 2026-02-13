import logging
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['📱 Commands', 'ℹ️ Info'], ['🎥 Videos', '❤️ Support']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ @Heartwaychatbot LIVE 24/7!\n\n"
        "Choose a button below:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 **Help**\n\n"
        "• /start - Main menu\n"
        "• /info - Bot info\n"
        "• 📱 Commands - All commands\n"
        "• ℹ️ Info - About bot\n\n"
        "**Made by Heartway** ❤️",
        parse_mode='Markdown'
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ **Bot Info**\n\n"
        "• **Name**: @Heartwaychatbot\n"
        "• **Status**: 🟢 24/7 Online\n"
        "• **Hosted**: Railway\n"
        "• **Version**: 2.0\n\n"
        "**Your educational bot!** 🎓",
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "📱 Commands":
        await update.message.reply_text("📋 **All Commands:**\n/start - 🎬 Main Menu\n/help - ❓ Help\n/info - ℹ️ Info")
    elif text == "ℹ️ Info":
        await info_command(update, context)
    elif text == "🎥 Videos":
        await update.message.reply_text("📹 **Videos Coming Soon!**\n\nSubscribe for updates! ❤️")
    elif text == "❤️ Support":
        await update.message.reply_text("💖 **Support Heartway**\n\nShare bot: @Heartwaychatbot\n\nThank you! 🙏")
    else:
        await update.message.reply_text("❓ Unknown command. Use buttons below!")

def main():
    app = Application.builder().token("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    
    app.run_polling()

if __name__ == "__main__":
    main()

