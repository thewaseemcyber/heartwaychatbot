import os
import json
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Storage
user_profiles = {}
chat_pairs = {}
profile_states = {}
vip_users = set()
active_chats_list = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['🌟 New Chat', '🔍 Search People'],
        ['👥 Active Chats', '✏️ My Profile'],
        ['📞 Call', '💎 VIP'],
        ['⚠️ Report', '🔚 End Chat']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "💬 **@Heartwaychatbot v6.5**\n\n"
        "✨ **Pro Anonymous Chat**\n\n"
        "Choose:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def get_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vip_text = """
🔓 **Unlock Premium Plan**

**What you'll get:**
• **Search by Partner's Age**: Find partners within your age range
• **Interest-based Matching**: Get matched with people who share your interests  
• **Gender-based Matching**: Choose whether you want to chat with boys or girls
• **Send Photos, GIFs**: Unrestricted users can share media
• **Unlimited Matching Chats**: Match efficiently

**Select duration for better discount:**
₹50 | ₹99 | ₹250 | ₹500 | ₹1000
"""
    
    keyboard = [['💎 Become VIP Free', '❌ Back']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(vip_text, parse_mode='Markdown', reply_markup=reply_markup)

async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile_states[user_id] = "name"
    user_profiles[user_id] = user_profiles.get(user_id, {})
    
    keyboard = [['❌ Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "✏️ **Create/Edit Profile**\n\n"
        "📝 **Name** (e.g. Mir):",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_profiles or not user_profiles[user_id]:
        await edit_profile(update, context)
        return
    
    profile = user_profiles[user_id]
    is_vip = user_id in vip_users
    
    profile_text = f"""
👤 **{profile.get('name', 'Anonymous')}**

• **Gender**: {profile.get('gender', 'Not set')} {profile.get('region', '')}
• **Age**: {profile.get('age', 'Not set')} 
• **City**: {profile.get('city', 'Not set')}
• **Timezone**: {profile.get('timezone', 'Not set')}

**Currently**: {profile.get('status', 'Online 💚')}

💎 {'VIP' if is_vip else 'Free'}
"""
    
    await update.message.reply_text(profile_text, parse_mode='Markdown')

async def handle_profile_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in profile_states:
        return
    
    state = profile_states[user_id]
    profile = user_profiles[user_id]
    
    if text == "❌ Cancel":
        del profile_states[user_id]
        await start(update, context)
        return
        
    if text == "💎 Become VIP Free":
        vip_users.add(user_id)
        await update.message.reply_text(
            "🎉 **VIP ACTIVATED FREE!**\n\n"
            "✅ **All Premium Features UNLOCKED**\n"
            "• Age/Gender filters\n"
            "• Send photos/videos\n"
            "• Choose specific users\n\n"
            "**👥 Active Chats now available!** ✨"
        )
        return
        
    if state == "name":
        profile['name'] = text[:20]
        profile_states[user_id] = "gender"
        await update.message.reply_text("🔤 **Gender** (Boy/Girl):")
    elif state == "gender":
        profile['gender'] = text
        profile_states[user_id] = "region"
        await update.message.reply_text("🌍 **Region** (e.g. Kashmir):")
    elif state == "region":
        profile['region'] = text
        profile_states[user_id] = "age"
        await update.message.reply_text("🎂 **Age** (e.g. 24):")
    elif state == "age":
        if text.isdigit():
            profile['age'] = text
            profile_states[user_id] = "city"
            await update.message.reply_text("🏙️ **City** (e.g. Srinagar):")
        else:
            await update.message.reply_text("❌ Numbers only!")
    elif state == "city":
        profile['city'] = text
        profile_states[user_id] = "timezone"
        await update.message.reply_text("🌐 **Timezone** (e.g. IST):")
    elif state == "timezone":
        profile['timezone'] = text
        profile['status'] = "Online 💚"
        del profile_states[user_id]
        await update.message.reply_text(
            "✅ **Profile Saved!**\n\n"
            f"👤 **{profile['name']}** ({profile['age']}, {profile['city']})\n"
            "✨ **Now visible in Active Chats!**"
        )

async def active_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_vip = user_id in vip_users
    
    if not is_vip:
        await update.message.reply_text(
            "🔒 **VIP ONLY - Active Chats**\n\n"
            "💎 **VIP users** can:\n"
            "• See all online users\n"
            "• Chat with chosen users\n\n"
            "**Get VIP to unlock!**"
        )
        return
    
    # Show REAL usernames from created profiles
    active_profiles = []
    for uid, profile in user_profiles.items():
        if profile.get('status') == 'Online 💚' and uid != user_id:
            active_profiles.append(f"👤 **{profile['name']}** ({profile['age']}, {profile['city']}) 💚")
    
    if active_profiles:
        chat_list = "\n".join(active_profiles[:8])
        await update.message.reply_text(
            f"👥 **VIP Active Chats** ({len(active_profiles)} online)\n\n"
            f"{chat_list}\n\n"
            "💎 **VIP**: Reply with username to chat!\n"
            "*e.g. 'Mir'* ✨",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("👥 **No active VIP users yet**\n**Create profile → Get VIP!**")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # ORIGINAL 10 BUTTONS
    if text == "🌟 New Chat":
        await update.message.reply_text("🎉 **Auto matching...** 💕 [Heart animation]")
    elif text == "🔍 Search People":
        await update.message.reply_text("🔍 **1,247 users online**\n• Filter by age/gender/region (VIP)")
    elif text == "👥 Active Chats":
        await active_chats(update, context)
    elif text == "✏️ My Profile":
        await edit_profile(update, context)
    elif text == "📞 Call":
        await update.message.reply_text("📱 **Video/Audio call ready!**\n💎 VIP users get priority calls")
    elif text == "💎 VIP":
        await get_vip(update, context)
    elif text == "⚠️ Report":
        await update.message.reply_text("⚠️ **Report User**\n• Spam → 20d ban\n• Abuse → 15d suspend")
    elif text == "🔚 End Chat":
        await update.message.reply_text("💔 **Disconnected!** *Heartbreak sound*")
    else:
        await handle_profile_input(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
