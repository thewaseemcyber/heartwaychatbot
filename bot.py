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
        "🎭 **Welcome to @Heartwaychatbot v4.0**\n\n"
        "Choose from the menu 👇",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    responses = {
        "🌟 New Chat": "🎉 **Connected to anonymous user!**\n\n💕 **Chat started** - Type your message!\n[Heart animation active]",
        "🔍 Search People": "🔍 **Search Results**\n\n👤 1,247 users online\n• Male: 678 | Female: 569\n**Tap user to chat** ✨",
        "👥 Browse People": "👥 **Online Users**\n\n1. @CoolStudent (20,M) 2. @MovieFan (24,F)\n**Tap name to start chat**",
        "✏️ My Profile": "👤 **Your Profile**\n\n**@YourName** | 22 • Male\n❤️ Coding, Movies\n📝 *Srinagar Student*\n\n**✏️ Edit | ✅ Share**",
        "📞 Call": "📱 **Start Call**\n\n📹 **Video Call** | 📞 **Audio Call**\n**Tap to connect**",
        "💎 VIP": "💎 **VIP ₹99/month**\n\n✅ Gender choice\n✅ Priority match\n✅ Unlimited chat\n**UPI: heartway@paytm**",
        "⚠️ Report": "⚠️ **Report User**\n\n• Ads/Spam → **20 day BAN**\n• Abuse → **15 day SUSPEND**\n**Type reason:**",
        "🔚 End Chat": "💔 **DISCONNECTED**\n\n*Heartbreak sound plays*\n**Tap 🌟 New Chat**",
        "📹 Video Call": "📹 **Video call connecting...**\n**Partner joining**",
        "📞 Audio Call": "📞 **Audio call started**\n**Partner connected** 🎵"
    }
    
    if text in responses:
        await update.message.reply_text(responses[text], parse_mode='Markdown')
    else:
        await start(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()

