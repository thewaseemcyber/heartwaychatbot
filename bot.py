import os
import logging
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['🌟 New Chat', '👥 Browse People'],
        ['📍 Nearby People', '💎 Credits'],
        ['👤 Profile', '❓ Help']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎭 **Welcome to @Heartwaychatbot**\n\n"
        "Choose from the menu below 👇",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🌟 New Chat":
        keyboard = [['✅ Start Chat', '❌ Cancel']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text(
            "🔄 **Finding chat partner...**\n\n"
            "Waiting for someone to join...\n\n"
            "Tap Start when ready:",
            reply_markup=reply_markup
        )
    elif text == "👥 Browse People":
        await update.message.reply_text("👥 **1,247 users online**\n\n**Coming Soon™** ✨")
    elif text == "📍 Nearby People":
        await update.message.reply_text("📍 **Nearby People**\n\n**Srinagar, Jammu & Kashmir**\n\n**Feature Coming Soon** 🚀")
    elif text == "💎 Credits":
        await update.message.reply_text("💎 **Your Credits: 25**\n\n• Free daily: 5 credits\n• Refer friends: +10")
    elif text == "👤 Profile":
        await update.message.reply_text("👤 **Your Profile**\n\n**Anonymous User**\n• Level 1\n• 3 Chats Today")
    elif text == "❓ Help":
        await update.message.reply_text("❓ **Help**\n\n• 🌟 New Chat\n• 👥 Browse People\n• 💎 Credits\n• 👤 Profile")
    elif text == "✅ Start Chat":
        await update.message.reply_text("🎉 **Chat Started!**\n\n**Anonymous:** Hi there! 👋")
    elif text == "❌ Cancel":
        await update.message.reply_text("❌ **Search cancelled**\n\nTap 🌟 New Chat to try again!")
    else:
        # Show main menu
        keyboard = [
            ['🌟 New Chat', '👥 Browse People'],
            ['📍 Nearby People', '💎 Credits'],
            ['👤 Profile', '❓ Help']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🎭 **Welcome to @Heartwaychatbot**\n\n"
            "Choose from the menu below 👇",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
