# v14.0 - REAL-TIME FEATURES
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import time

# Real-time data (in-memory)
profiles = {}
waiting_boys = []
waiting_girls = []
active_chats = {}
chat_history = {}  # {chat_id: [{"user": name, "msg": text, "time": ts}]}
typing_status = {}  # {user_id: True/False}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ /start - New Match", callback_data="start")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("⭐ VIP", callback_data="vip")],
        [InlineKeyboardButton("/stop - End", callback_data="stop")]
    ])

async def cmd_start(update, context):
    user_id = str(update.message.from_user.id)
    
    if user_id not in profiles:
        await update.message.reply_text(
            "👤 `Mir boy 24 Srinagar`",
            reply_markup=main_menu()
        )
        return
    
    profile = profiles[user_id]
    
    # End existing chat
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        typing_status.pop(user_id, None)
        typing_status.pop(partner_id, None)
    
    gender = profile['gender']
    
    # REAL-TIME MATCHING
    if gender == 'boy' and waiting_girls:
        partner_id = waiting_girls.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        chat_id = f"{min(user_id, partner_id)}-{max(user_id, partner_id)}"
        chat_history[chat_id] = []
        
        partner_profile = profiles[partner_id]
        await update.message.reply_text(
            f"💕 *REAL-TIME MATCH!*\n\n"
            f"✅ *{partner_profile['name']}* ({partner_profile['gender'].title()})\n"
            f"📍 *{partner_profile['city']}*\n\n"
            f"✨ *Typing indicator LIVE!*\n"
            f"📱 *Messages instant!*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Chat", callback_data="chat")],
                [InlineKeyboardButton("/stop", callback_data="stop")]
            ]),
            parse_mode='Markdown'
        )
        return
    elif gender == 'girl' and waiting_boys:
        partner_id = waiting_boys.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        chat_id = f"{min(user_id, partner_id)}-{max(user_id, partner_id)}"
        chat_history[chat_id] = []
        
        partner_profile = profiles[partner_id]
        await update.message.reply_text(
            f"💕 *REAL-TIME MATCH!*\n\n"
            f"✅ *{partner_profile['name']}* ({partner_profile['gender'].title()})\n"
            f"📍 *{partner_profile['city']}*\n\n"
            f"✨ *Typing LIVE! Messages instant!*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💬 Chat", callback_data="chat")],
                [InlineKeyboardButton("/stop", callback_data="stop")]
            ]),
            parse_mode='Markdown'
        )
        return
    
    # Add to queue
    if gender == 'boy':
        waiting_boys.append(user_id)
    else:
        waiting_girls.append(user_id)
    
    await update.message.reply_text(
        f"🔍 *{profile['name']}* matching...\n"
        f"⏱️ *Real-time queue*",
        reply_markup=main_menu()
    )

async def cmd_stop(update, context):
    user_id = str(update.message.from_user.id)
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        typing_status.pop(user_id, None)
        typing_status.pop(partner_id, None)
        
        chat_id = f"{min(user_id, partner_id)}-{max(user_id, partner_id)}"
        chat_history.pop(chat_id, None)
        
        await update.message.reply_text(
            "✅ *Chat ended*\n\n✨ /start new match",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "❌ No chat\n\n💕 /start",
            reply_markup=main_menu()
        )

async def cmd_report(update, context):
    await update.message.reply_text(
        "⚠️ *Report*\n\n1. Inappropriate\n2. Harassment\n3. Spam\n\n*Send:*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Reported", callback_data="done")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back")]
        ])
    )

async def handle_message(update, context):
    user_id = str(update.message.from_user.id)
    text = update.message.text.strip()
    
    # Profile creation
    parts = text.split()
    if len(parts) >= 4 and user_id not in profiles:
        try:
            profiles[user_id] = {
                'name': parts[0],
                'gender': parts[1].lower(),
                'age': int(parts[2]),
                'city': ' '.join(parts[3:])
            }
            await update.message.reply_text(
                f"✅ *{parts[0]} ready!*\n\n✨ /start",
                reply_markup=main_menu()
            )
            return
        except:
            pass
    
    # REAL-TIME CHAT
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        partner_profile = profiles[partner_id]
        
        chat_id = f"{min(user_id, partner_id)}-{max(user_id, partner_id)}"
        if chat_id not in chat_history:
            chat_history[chat_id] = []
        
        # Add to history
        chat_history[chat_id].append({
            "user": profiles[user_id]['name'],
            "msg": text,
            "time": time.time()
        })
        
        # Send to partner with typing effect simulation
        typing_status[partner_id] = True
        await context.bot.send_chat_action(chat_id=partner_id, action="typing")
        time.sleep(1)  # Typing delay
        
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"💬 *{profiles[user_id]['name']} ({profiles[user_id]['gender'].title()}):*\n\n{text}",
            parse_mode='Markdown'
        )
        typing_status[partner_id] = False
        
        return
    
    await update.message.reply_text(
        "**Heartway Chat**\n\n"
        "**Commands:**\n`/start /stop /report`\n\n"
        "`Mir boy 24 Srinagar`",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

async def btn_handler(update, context):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'profile':
        user_id = str(query.from_user.id)
        profile = profiles.get(user_id)
        if profile:
            await query.edit_message_text(
                f"👤 *{profile['name']}*\n🔸 *{profile['gender']}*\n"
                f"📅 *{profile['age']}* | 📍 *{profile['city']}*\n\n"
                "**Real-time chat ready!**",
                reply_markup=main_menu(),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("👤 `Mir boy 24 Srinagar`", parse_mode='Markdown')
    elif query.data == 'vip':
        await query.edit_message_text(
            "⭐ **VIP Real-time**\n\n"
            "⚡ Priority matching\n"
            "💬 Live typing indicator\n"
            "📱 Instant delivery\n"
            "📸 Photo sharing\n\n*₹99/week*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back")]]),
            parse_mode='Markdown'
        )
    elif query.data == 'chat':
        await query.edit_message_text(
            "💬 **Real-time Chat Active**\n\n"
            "✨ Typing indicators\n"
            "⚡ Instant messages\n\n**/stop to end**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("/stop", callback_data="stop")]]),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "**Commands:**\n`/start /stop /report`",
            reply_markup=main_menu(),
            parse_mode='Markdown'
        )

if __name__ == "__main__":
    print("🚀 @Heartwaychatbot v14.0 - REAL-TIME!")
    app = Application.builder().token("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CallbackQueryHandler(btn_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ REAL-TIME FEATURES LIVE!")
    app.run_polling()


