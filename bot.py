)
        return
        
    if state == "name":
        profile['name'] = text[:20]
        profile_states[user_id] = "gender"
        await update.message.reply_text("🔤 Gender (Boy/Girl):")
        
    elif state == "gender":
        profile['gender'] = text
        profile_states[user_id] = "region"
        await update.message.reply_text("🌍 Region (e.g. Kashmir):")
        
    elif state == "region":
        profile['region'] = text
        profile_states[user_id] = "age"
        await update.message.reply_text("🎂 Age (e.g. 24):")
        
    elif state == "age":
        if text.isdigit():
            profile['age'] = text
            profile_states[user_id] = "city"
            await update.message.reply_text("🏙️ City (e.g. Srinagar):")
        else:
            await update.message.reply_text("❌ Numbers only!")
            
    elif state == "city":
        profile['city'] = text
        profile_states[user_id] = "timezone"
        await update.message.reply_text("🌐 Timezone (e.g. IST):")
        
    elif state == "timezone":
        profile['timezone'] = text
        profile['status'] = "Online 💚"
        del profile_states[user_id]
        await update.message.reply_text(
            "✅ Profile Saved!

"
            f"👤 {profile['name']} ({profile['age']})
"
            "✨ Ready for VIP chats!"
        )

async def active_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_vip = user_id in vip_users
    
    if not is_vip:
        await update.message.reply_text(
            "🔒 VIP ONLY

"
            "Choose specific users from Active Chats

"
            "💎 Get VIP to connect by choice!"
        )
        keyboard = [['💎 Get VIP']]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await update.message.reply_text("Tap Get VIP 👆", reply_markup=reply_markup)
        return
    
    # Show REAL usernames from created profiles
    active_profiles = []
    for uid, profile in user_profiles.items():
        if profile.get('status') == 'Online 💚' and uid != user_id:
            active_profiles.append(f"👤 {profile['name']} ({profile['age']}, {profile['city']}) 💚")
    
    if active_profiles:
        chat_list = "
".join(active_profiles[:5])  # Show top 5
        await update.message.reply_text(
            f"👥 VIP Active Chats ({len(active_profiles)} online)

"
            f"{chat_list}

"
            "💎 VIP: Tap any name to chat!
"
            "*Message them directly* ✨",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "👥 No active chats yet

"
            "💎 VIP users will appear here!
"
            "Create profile → Get VIP → Chat!"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🌟 Find Chat Partner":
        await update.message.reply_text("🎉 Auto matching... 💕")
        
    elif text == "👥 Active Chats":
        await active_chats(update, context)
        
    elif text == "✏️ Edit Profile":
        await edit_profile(update, context)
        
    elif text == "📱 View My Profile":
        await view_profile(update, context)
        
    elif text == "💎 Get VIP":
        await get_vip(update, context)
        
    elif text == "🔚 Leave Chat":
        await update.message.reply_text("💔 Left chat")
    else:
        await handle_profile_input(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.run_polling()

if name == "main":
    main()
