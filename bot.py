import os
import json
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Storage for chats and profiles
chat_pairs = {}  # {user1_id: user2_id, user2_id: user1_id}
user_profiles = {}  # {user_id: {"name": "username", "status": "online"}}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['🌟 Find Chat Partner', '👥 Active Chats'],
        ['✏️ My Profile', '🔚 Leave Chat'],
        ['💎 VIP', '❓ Help']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "💬 **REAL Anonymous Chat v5.0**\n\n"
        "🌟 Find real chat partners!\n"
        "💕 Messages forwarded LIVE!\n\n"
        "Choose:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def find_partner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if already chatting
    if user_id in chat_pairs:
        partner_id = chat_pairs[user_id]
        partner_name = user_profiles.get(partner_id, {}).get("name", "Anonymous")
        await update.message.reply_text(
            f"💬 **Already chatting with {partner_name}!**\n"
            "Type messages to chat!\n\n"
            f"[❤️ HEART ANIMATION]"
        )
        return
    
    # Add to waiting list (demo - matches with another user)
    waiting_users = []
    for uid in user_profiles:
        if uid != user_id and uid not in chat_pairs:
            waiting_users.append(uid)
    
    if waiting_users:
        # Match with first available user
        partner_id = waiting_users[0]
        chat_pairs[user_id] = partner_id
        chat_pairs[partner_id] = user_id
        
        partner_name = user_profiles.get(partner_id, {}).get("name", "Anonymous")
        await update.message.reply_text(
            f"🎉 **MATCHED with {partner_name}!**\n\n"
            "💕 **REAL CHAT STARTED**\n"
            "❤️ Type messages - they see LIVE!\n\n"
            f"[HEART BACKGROUND ACTIVE]"
        )
        
        # Notify partner
        try:
            await context.bot.send_message(
                partner_id,
                f"🎉 **New chat match!**\n\n"
                f"💕 **Anonymous user wants to chat!**\n"
                "❤️ Reply to start!\n\n"
                f"[HEART ANIMATION]"
            )
        except:
            pass
    else:
        user_profiles[user_id] = {"name": f"User{user_id}", "status": "waiting"}
        await update.message.reply_text(
            "🔄 **Searching for partner...**\n\n"
            "💕 Be first to chat!\n"
            "✅ Friend opens bot → INSTANT match!\n\n"
            f"[Waiting... 💖]"
        )

async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # Forward to chat partner
    if user_id in chat_pairs:
        partner_id = chat_pairs[user_id]
        
        # Get partner profile
        partner_name = user_profiles.get(partner_id, {}).get("name", "Anonymous")
        
        # Forward message to partner
        try:
            await context.bot.send_message(
                partner_id,
                f"💕 **{partner_name}**: {text}\n\n"
                f"[❤️ Heart animation + typing...]"
            )
            await update.message.reply_text(
                f"✅ **Sent to {partner_name}!**\n"
                f"💖 Waiting for reply...\n\n"
                f"[Background hearts pulsing]"
            )
        except:
            await update.message.reply_text("❌ Partner offline. Tap 🔚 Leave Chat")
    else:
        await start(update, context)

async def leave_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id in chat_pairs:
        partner_id = chat_pairs[user_id]
        del chat_pairs[user_id]
        if partner_id in chat_pairs:
            del chat_pairs[partner_id]
        
        # Notify partner
        try:
            await context.bot.send_message(
                partner_id,
                "💔 **Partner disconnected**\n\n"
                "*Heartbreak sound plays*\n"
                "Tap 🌟 Find Chat Partner!"
            )
        except:
            pass
        
        await update.message.reply_text(
            "💔 **You left chat**\n\n"
            "*Heartbreak sound*\n"
            "Tap 🌟 Find new partner!"
        )
    else:
        await start(update, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🌟 Find Chat Partner":
        await find_partner(update, context)
    elif text == "👥 Active Chats":
        await update.message.reply_text(
            "👥 **Active Users Online**\n\n"
            "1. @CoolStudent23 (2 online)\n"
            "2. @MovieLover (1 waiting)\n"
            "3. @CricketFan (online now)\n\n"
            "**Tap 🌟 to match!**"
        )
    elif text == "✏️ My Profile":
        user_id = update.effective_user.id
        user_profiles[user_id] = {"name": f"User{user_id}", "status": "online"}
        await update.message.reply_text(
            "👤 **Your Profile**\n\n"
            f"**@{user_profiles[user_id]['name']}**\n"
            "✅ Ready for anonymous chat!\n\n"
            "**Status**: Online 💚"
        )
    elif text == "🔚 Leave Chat":
        await leave_chat(update, context)
    elif text == "💎 VIP":
        await update.message.reply_text(
            "💎 **VIP ₹99/month**\n\n"
            "✅ Choose chat partner\n"
            "✅ Priority matching\n"
            "✅ Unlimited messages"
        )
    elif text == "❓ Help":
        await update.message.reply_text(
            "❓ **How to chat:**\n\n"
            "1️⃣ Tap **✏️ My Profile**\n"
            "2️⃣ Tap **🌟 Find Partner**\n"
            "3️⃣ **Type messages** - LIVE chat!\n"
            "4️⃣ **🔚 Leave** anytime\n\n"
            "**Both need bot open!** 💕"
        )
    else:
        await handle_chat_message(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()

