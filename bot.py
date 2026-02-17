# Perfect memory storage
profiles = {}
waiting_boys = []
waiting_girls = []
active_chats = {}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💌 Write message", callback_data="write")],
        [InlineKeyboardButton("🔍 Find partner", callback_data="find")],
        [InlineKeyboardButton("👫 Friends", callback_data="friends")]
    ])

def top_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💖 Search by gender", callback_data="gender_search")],
        [InlineKeyboardButton("🔍 Find a partner", callback_data="find_partner")],
        [InlineKeyboardButton("👫 Friends", callback_data="friends")]
    ])

def profile_vip_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("⭐ VIP access", callback_data="vip")]
    ])

async def start(update, context):
    await update.message.reply_text(
        "💕 *Heartway Chat*\n\n"
        "👤 *Create profile first:*\n"
        "`Mir boy 24 Srinagar`",
        reply_markup=main_menu()
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
                "✅ *Profile ready!*\n\n"
                "💕 *Perfect interface loaded!*",
                reply_markup=top_menu()
            )
            return
        except:
            pass
    
    # Forward chat message
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text=f"💬 *{profiles[user_id]['name']}:*\n\n{text}"
            )
        except:
            pass
        return
    
    await update.message.reply_text(
        "**Heartway Chat**\n\n"
        "`Mir boy 24 Srinagar`\n\n"
        "*Commands: /start /stop /report*",
        reply_markup=main_menu()
    )

async def btn_find_partner(update, context):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    if user_id not in profiles:
        await query.edit_message_text(
            "👤 *First create profile:*\n\n"
            "`Mir boy 24 Srinagar`",
            reply_markup=main_menu()
        )
        return
    
    profile = profiles[user_id]
    gender = profile['gender']
    
    # Clear old chat
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
    
    # Find match
    if gender == 'boy' and waiting_girls:
        partner_id = waiting_girls.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        await query.edit_message_text(
            f"💕 *MATCH FOUND!*\n\n"
            f"✅ Connected to *Girl*\n"
            f"✨ Chat started!\n\n"
            f"*💌 Write message below*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💖 Search by gender", callback_data="gender_search")],
                [InlineKeyboardButton("/stop - End chat", callback_data="stop")]
            ])
        )
        return
    elif gender == 'girl' and waiting_boys:
        partner_id = waiting_boys.pop(0)
        active_chats[user_id] = partner_id
        active_chats[partner_id] = user_id
        
        await query.edit_message_text(
            f"💕 *MATCH FOUND!*\n\n"
            f"✅ Connected to *Boy*\n"
            f"✨ Chat started!\n\n"
            f"*💌 Write message below*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💖 Search by gender", callback_data="gender_search")],
                [InlineKeyboardButton("/stop - End chat", callback_data="stop")]
            ])
        )
        return
    
    # Add to queue
    if gender == 'boy':
        waiting_boys.append(user_id)
    else:
        waiting_girls.append(user_id)
    
    await query.edit_message_text(
        f"🔍 *Finding partner...*\n\n"
        f"👤 *{profile['name']}* ({profile['gender'].title()})\n"
        f"⏳ *Real-time matching*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Try again", callback_data="find_partner")],
            [InlineKeyboardButton("⬅️ Menu", callback_data="menu")]
        ])
    )

async def btn_gender_search(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💖 *Search by Gender*\n\n"
        "**VIP Feature**\n\n"
        "🔸 *Boys only*\n"
        "🔸 *Girls only*\n\n"
        "*Upgrade VIP to unlock!*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⭐ VIP access", callback_data="vip")],
            [InlineKeyboardButton("⬅️ Back", callback_data="find_partner")]
        ])
    )

async def btn_profile(update, context):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    
    profile = profiles.get(user_id)
    if profile:
        await query.edit_message_text(
            f"👤 *{profile['name']}*\n"
            f"🔸 *{profile['gender'].title()}*\n"
            f"📅 *{profile['age']}*\n"
            f"📍 *{profile['city']}*\n\n"
            "**Ready for matching!**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Find partner", callback_data="find_partner")],
                [InlineKeyboardButton("⬅️ Menu", callback_data="menu")]
            ])
        )
    else:
        await query.edit_message_text("👤 `Mir boy 24 Srinagar`", parse_mode='Markdown')

async def btn_vip(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "⭐ *VIP Access*\n\n"
        "💎 *₹99/week*\n"
        "✨ *Search by gender*\n"
        "📸 *Send photos*\n"
        "⚡ *Priority matching*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Get VIP", callback_data="vip_buy")],
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")]
        ])
    )

async def btn_back(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💕 *Heartway Chat*",
        reply_markup=top_menu()
    )

async def btn_placeholder(update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🚀 *Feature coming soon!*",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Back", callback_data="menu")]
        ])
    )

async def cmd_stop(update, context):
    user_id = str(update.message.from_user.id)
    if user_id in active_chats:
        partner_id = active_chats.pop(user_id)
        active_chats.pop(partner_id, None)
        await update.message.reply_text(
            "✅ *Chat ended!*\n\n🔍 *Find new partner*",
            reply_markup=top_menu()
        )
    else:
        await update.message.reply_text("❌ *No active chat*", reply_markup=top_menu())

if __name__ == "__main__":
    print("🚀 @Heartwaychatbot v15.0 - PERFECT INTERFACE!")
    app = Application.builder().token("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", cmd_stop))
    
    app.add_handler(CallbackQueryHandler(btn_find_partner, pattern="^find_partner$"))
    app.add_handler(CallbackQueryHandler(btn_gender_search, pattern="^gender_search$"))
    app.add_handler(CallbackQueryHandler(btn_profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(btn_vip, pattern="^vip$"))
    app.add_handler(CallbackQueryHandler(btn_back, pattern="^(menu|back)$"))
    app.add_handler(CallbackQueryHandler(btn_placeholder))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ EXACT INTERFACE MATCH!")
    app.run_polling()



