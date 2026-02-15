"""
@Heartwaychatbot v11.0 - SIMPLEST + Tikible Style
ONLY 3 COMMANDS: /start /stop /report
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import json
import os

DATA_FILE = 'heartway_data.json'

def load_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {"profiles": {}, "waiting_boys": [], "waiting_girls": [], "active_chats": {}}

def save_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass

# Tikible style menu
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Start Chat", callback_data="start_chat")],
        [InlineKeyboardButton("👤 My Profile", callback_data="profile")],
        [InlineKeyboardButton("⭐ VIP", callback_data="vip")],
        [InlineKeyboardButton("💌 Messages", callback_data="messages")]
    ])

# EXACT Tikible VIP screen
def vip_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Age Matching", callback_data="vip_age")],
        [InlineKeyboardButton("❤️ Interest Matching", callback_data="vip_interest")],
        [InlineKeyboardButton("📸 Send Photos", callback_data="vip_media")],
        [InlineKeyboardButton("💬 Unlimited Msg", callback_data="vip_unlimited")],
        [],
        [InlineKeyboardButton("💎 ₹99 / 1 week", callback_data="vip_99")],
        [InlineKeyboardButton("💎 ₹259 / 4-6 months", callback_data="vip_259")],
        [InlineKeyboardButton("⭐ ₹599 / 12 months", callback_data="vip_599")],
        [InlineKeyboardButton("👑 ₹1000 VIP Free", callback_data="vip_free")],
        [],
        [InlineKeyboardButton("✨ Become VIP Free", callback_data="vip_free_trial")],
        [InlineKeyboardButton("⬅️ Menu", callback_data="back")]
    ])

# 1. /start - Start new match
async def start(update, context):
    user_id = str(update.message.from_user.id)
    data = load_data()
    profile = data["profiles"].get(user_id)
    
    if not profile:
        await update.message.reply_text(
            "👤 *Create profile first:*\n\n"
            "`Mir boy 24 Srinagar`\n\n"
            "💕 *Then use /start*",
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )
        return
    
    # Clear any active chat
    if user_id in data["active_chats"]:
        del data["active_chats"][user_id]
    
    # Start matching
    gender = profile['gender']
    if gender == "boy" and data["waiting_girls"]:
        partner_id = data["waiting_girls"].pop(0)
        data["active_chats"][user_id] = partner_id
        data["active_chats"][partner_id] = user_id
        save_data(data)
        
        partner_name = data["profiles"][partner_id]["name"]
        await update.message.reply_text(
            f"💕 *MATCH FOUND!*\n\n"
            f"✅ *Connected to {partner_name}*\n"
            f"✨ *Chat started! Use /stop to end*\n\n"
            f"*Send your message:*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Call", callback_data="call")],
                [InlineKeyboardButton("/stop - End Chat", callback_data="stop")]
            ])
        )
        return
    elif gender == "girl" and data["waiting_boys"]:
        partner_id = data["waiting_boys"].pop(0)
        data["active_chats"][user_id] = partner_id
        data["active_chats"][partner_id] = user_id
        save_data(data)
        
        partner_name = data["profiles"][partner_id]["name"]
        await update.message.reply_text(
            f"💕 *MATCH FOUND!*\n\n"
            f"✅ *Connected to {partner_name}*\n"
            f"✨ *Chat started! Use /stop to end*\n\n"
            "*Send your message:*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 Call", callback_data="call")],
                [InlineKeyboardButton("/stop - End Chat", callback_data="stop")]
            ])
        )
        return
    
    # Add to queue
    if gender == "boy":
        data["waiting_boys"].append(user_id)
    else:
        data["waiting_girls"].append(user_id)
    save_data(data)
    
    await update.message.reply_text(
        f"🔍 *Finding match for {profile['name']}...*\n\n"
        f"⏳ *Use /start anytime for new match*",
        reply_markup=main_menu()
    )

# 2. /stop - End current chat
async def stop(update, context):
    user_id = str(update.message.from_user.id)
    data = load_data()
    
    if user_id in data["active_chats"]:
        partner_id = data["active_chats"].pop(user_id)
        if partner_id in data["active_chats"]:
            data["active_chats"].pop(partner_id)
        save_data(data)
        await update.message.reply_text(
            "✅ *Chat ended!*\n\n"
            "✨ *Use /start for new match*",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "❌ *No active chat!*\n\n"
            "💕 *Use /start to begin*",
            reply_markup=main_menu()
        )

# 3. /report - Report after chat (Tikible style)
async def report(update, context):
    await update.message.reply_text(
        "⚠️ *Report User*\n\n"
        "*Why are you reporting?*\n\n"
        "1️⃣ Inappropriate content\n"
        "2️⃣ Harassment\n"
        "3️⃣ Spam\n"
        "4️⃣ Other\n\n"
        "*Send number or reason:*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Reported", callback_data="reported")],
            [InlineKeyboardButton("⬅️ Cancel", callback_data="back")]
        ])
    )

# Profile & VIP (Tikible style)
async def profile(update, context):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = load_data()
    profile = data["profiles"].get(user_id)
    
    if profile:
        await query.edit_message_text(
            f"👤 *{profile['name']}*\n🔸 *{profile['gender'].title()}*\n"
            f"📅 *{profile['age']}* | 📍 *{profile['city']}*\n\n"
            f"*Commands: /start /stop /report*",
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "👤 `Mir boy 24 Srinagar`",
            parse_mode='Markdown'
        )

async def vip(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✨ *Unlock Premium Benefits*\n"
        "*Enjoy premium plan!* ✨\n\n"
        "🔍 *Age based matching*\n"
        "❤️ *Interest matching*\n"
        "📸 *Send photos/videos*\n"
        "💬 *Unlimited messages*\n\n"
        "*Longer duration = greater discount*",
        reply_markup=vip_menu(),
        parse_mode='Markdown'
    )

async def back(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💕 *Heartway Chat*\n\n"
        "*Commands: /start /stop /report*",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

# Message forwarding during chat
async def handle_message(update, context):
    user_id = str(update.message.from_user.id)
    data = load_data()
    
    # Profile creation
    parts = update.message.text.split()
    if len(parts) >= 4 and not user_id in data["active_chats"]:
        try:
            data["profiles"][user_id] = {
                "name": parts[0], "gender": parts[1].lower(),
                "age": int(parts[2]), "city": " ".join(parts[3:])
            }
            save_data(data)
            await update.message.reply_text(
                f"✅ *{parts[0]} created!*\n\n*Use /start*",
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )
            return
        except:
            pass
    
    # Forward message to partner
    if user_id in data["active_chats"]:
        partner_id = data["active_chats"][user_id]
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"💬 *{data['profiles'][user_id]['name']}:* {update.message.text}",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text(
        "💕 *Heartway Chat*\n\n"
        "*Commands: /start /stop /report*",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

# Placeholder handlers
async def placeholder(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚀 *Feature coming soon!*\n\n"
        "*Use /start /stop /report*",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

# MAIN
if __name__ == "__main__":
    print("🚀 @Heartwaychatbot v11.0 LIVE!")
    print("✅ ONLY 3 COMMANDS: /start /stop /report")
    
    app = Application.builder().token("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()
    
    # ONLY 3 COMMANDS
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("report", report))
    
    # Buttons
    app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(vip, pattern="^vip$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(placeholder, pattern="^(start_chat|messages|vip_.*|reported|call)$"))
    
    # Messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Tikible style + 3 commands ONLY!")
    app.run_polling()

