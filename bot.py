import os
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['🌟 New Chat', '🔍 Search People'],
        ['👥 Browse People', '✏️ My Profile'],
        ['📞 Call', '💎 VIP'],
        ['⚠️ Report', '🔚 End Chat']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎭 Welcome to @Heartwaychatbot v4.0

"
        "Choose from the menu 👇",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🌟 New Chat":
        await update.message.reply_text(
            "🎉 Connected to anonymous user!

"
            "💕 Chat started - Type your message!
"
            "[Heart animation active]"
        )
        
    elif text == "🔍 Search People":
        await update.message.reply_text(
            "🔍 Search Results

"
            "👤 1,247 users online
"
            "• Male: 678 | Female: 569
"
            "• Age 18-35

"
            "Tap user to chat ✨"
        )
        
    elif text == "👥 Browse People":
        await update.message.reply_text(
            "👥 Online Users

"
            "1. @CoolStudent23 (20, Male)
"
            "2. @MovieLover (24, Female)
"
            "3. @CricketFan (22, Male)

"
            "Tap name to start chat"
        )
        
    elif text == "✏️ My Profile":
        await update.message.reply_text(
            "👤 Your Profile

"
            "@YourUsername
"
            "🎂 Age: 22 • Male
"
            "❤️ Interests: Coding, Movies
"
            "📝 *Student from Srinagar*

"
            "✏️ Edit Profile | ✅ Share"
        )
        
    elif text == "📞 Call":
        keyboard = [['📹 Video Call', '📞 Audio Call'], ['❌ Cancel']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "📱 Start Call

"
            "Choose call type:",
            reply_markup=reply_markup
        )
        
    elif text == "💎 VIP":
        await update.message.reply_text(
            "💎 VIP Features ₹99/month

"
            "✅ Choose gender
"
            "✅ Priority matching
"
            "✅ Unlimited chats
"
            "✅ No ads

"
            "Pay: heartway@paytm"
        )
        
    elif text == "⚠️ Report":
        await update.message.reply_text(
            "⚠️ Report User

"
            "• Spam/Ads → 20 day ban
"
            "• Abuse → 15 day suspend
"
            "Describe issue:"
        )
        
    elif text == "🔚 End Chat":
        await update.message.reply_text(
            "💔 Disconnected!

"
            "*Heartbreak sound*
"
            "Tap 🌟 New Chat for new partner!"
        )
        
    else:
        await start(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.run_polling()

if name == "main":
    main()
