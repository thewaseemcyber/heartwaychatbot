import os
import logging
import random
from datetime import datetime, timedelta
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Global storage
user_profiles = {}
active_chats = {}  # {user1: user2, user2: user1}
reported_users = {}
blocked_users = {}
vip_users = set()

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

async def profile_setup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_profiles[user_id] = {"step": "username", "created": datetime.now()}
    
    await update.message.reply_text(
        "✏️ **Create Profile**\n\n"
        "1️⃣ **Username** (max 20 chars):",
        reply_markup=ReplyKeyboardMarkup([['❌ Cancel']], resize_keyboard=True, one_time_keyboard=True)
    )

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_profiles and "username" in user_profiles[user_id]:
        profile = user_profiles[user_id]
        await update.message.reply_text(
            f"👤 **{profile['username']}**\n"
            f"🎂 {profile['age']} • {profile['gender']}\n"
            f"❤️ {profile['interests']}\n"
            f"📝 {profile['bio']}\n\n"
            f"**Status**: {'💎 VIP' if user_id in vip_users else 'Free'}",
            parse_mode='Markdown'
        )
        keyboard = [['✏️ Edit Profile', '✅ Share Profile'], ['💎 Upgrade VIP']]
        await update.message.reply_text("Profile options:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    else:
        await profile_setup(update, context)

async def new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if already in chat
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await update.message.reply_text(
            f"💬 **Already chatting with** {user_profiles[partner_id]['username']}\n"
            f"Use 🔚 End Chat to switch partner",
            parse_mode='Markdown'
        )
        return
    
    # Find partner (demo matching)
    available_users = [uid for uid, profile in user_profiles.items() if uid != user_id and uid not in active_chats]
    if available_users:
        partner_id = random.choice(available_users)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        partner_name = user_profiles[partner_id]['username']
        await update.message.reply_text(
            f"🎉 **Connected to {partner_name}!**\n\n"
            f"💝 **Chat Background Animation Started**\n"
            f"💕 Type messages to chat anonymously!\n\n"
            f"[HEART ANIMATION ACTIVE]",
            parse_mode='Markdown'
        )
        # Notify partner
        try:
            await context.bot.send_message(
                partner_id, 
                f"💝 **New chat started!**\n\n"
                f"**Anonymous**: Let's chat! 💕\n\n"
                f"[HEART BACKGROUND ACTIVE]",
                parse_mode='Markdown'
            )
        except:
            pass
    else:
        keyboard = [['🔄 Try Again', '❌ Cancel']]
        await update.message.reply_text(
            "🔄 **No partners available**\n\n"
            "Try again in few minutes?",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

async def search_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['Male', 'Female', 'Any'], ['18-25', '26-35', 'VIP Only']]
    await update.message.reply_text(
        "🔍 **Search People**\n\n"
        "Choose search filters:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚠️ **Report User**\n\n"
        "**Reasons**:\n"
        "• Spam/Ads → 20 day ban\n"
        "• Abuse → 15 day suspend\n"
        "• Wrong profile → Warning\n\n"
        "**Enter reason** (or /cancel):",
        reply_markup=ReplyKeyboardMarkup([['/cancel']], resize_keyboard=True)
    )

async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in vip_users:
        await update.message.reply_text("💎 **You're already VIP!**\n\n**VIP Features**:\n• Gender choice\n• Priority matching\n• No ads")
    else:
        await update.message.reply_text(
            "💎 **VIP Membership**\n\n"
            "**₹99/month**\n\n"
            "✅ Gender selection\n"
            "✅ Priority matching\n"
            "✅ No limits\n\n"
            "**Pay via UPI**: heartway@paytm\n**/vip activate**"
        )

async def end_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        del active_chats[user_id]
        if partner_id in active_chats:
            del active_chats[partner_id]
        
        await update.message.reply_text(
            "💔 **You are disconnected**\n\n"
            "*Heartbreak sound plays*\n\n"
            "Tap 🌟 New Chat to find new partner!",
            parse_mode='Markdown'
        )
    else:
        await show_main_menu(update)

async def call_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['📹 Video Call', '📞 Audio Call'], ['❌ Cancel']]
    await update.message.reply_text(
        "📱 **Start Call**\n\n"
        "Choose call type:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Profile creation flow (simplified)
    if user_id in user_profiles and "step" in user_profiles[user_id]:
        step = user_profiles[user_id]["step"]
        if step == "username":
            user_profiles[user_id]["username"] = text[:20]
            user_profiles[user_id]["step"] = "complete"
            await update.message.reply_text(
                f"✅ **Profile created!**\n\n"
                f"👤 **{text[:20]}**\n"
                f"✨ Ready for anonymous chat!"
            )
            await show_main_menu(update)
        return
    
    # Main menu handling
    if text == "🌟 New Chat":
        await new_chat(update, context)
    elif text == "✏️ My Profile":
        await my_profile(update, context)
    elif text == "🔍 Search People":
        await search_people(update, context)
    elif text == "👥 Browse People":
        await update.message.reply_text("👥 **1247 users online**\n**Tap profile to chat**")
    elif text == "📞 Call":
        await call_command(update, context)
    elif text == "💎 VIP":
        await vip_command(update, context)
    elif text == "⚠️ Report":
        await report_user(update, context)
    elif text == "🔚 End Chat":
        await end_chat(update, context)
    elif text in ["/vip", "VIP Only"]:
        await vip_command(update, context)
    else:
        # Chat messages (if in active chat)
        if user_id in active_chats:
            partner_id = active_chats[user_id]
            if partner_id in user_profiles:
                await update.message.reply_text(
                    f"💕 **Sent** (Heart animation)\n\n"
                    f"**Partner typing...**\n"
                    f"**{user_profiles[partner_id]['username']}**: Nice! 😊\n\n"
                    f"[Background hearts pulsing]"
                )
            else:
                await update.message.reply_text("💕 **Message sent!** [Partner will reply soon]")
        else:
            await show_main_menu(update)

async def show_main_menu(update: Update, context=None):
    keyboard = [
        ['🌟 New Chat', '🔍 Search People'],
        ['👥 Browse People', '✏️ My Profile'],
        ['📞 Call', '💎 VIP'],
        ['⚠️ Report', '🔚 End Chat']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎭 **@Heartwaychatbot**\n\n"
        "Choose from menu 👇",
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

