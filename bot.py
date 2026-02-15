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
        profile['status'] = "Online 💚"
        del profile_states[user_id]
        await update.message.reply_text(
            "✅ Profile Created!

"
            f"👤 {profile['name']} ({profile['age']}, {profile['city']})
"
            "✨ Ready for anonymous chat!"
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🌟 New Chat":
        await update.message.reply_text("🎉 Connected to random user! 💕")
    elif text == "🔍 Search People":
        await update.message.reply_text("🔍 1,247 users online
💎 VIP = Advanced filters")
    elif text == "✏️ My Profile":
        await edit_profile(update, context)
    elif text == "📞 Call":
        await update.message.reply_text("📱 Video/Audio call ready!")
    elif text == "💎 VIP":
        await get_vip(update, context)
    elif text == "⚠️ Report":
        await update.message.reply_text("⚠️ Spam=20d ban | Abuse=15d suspend")
    elif text == "🔚 End Chat":
        await update.message.reply_text("💔 Disconnected! 💔")
    else:
        await handle_profile_input(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    app.run_polling()

if name == "main":
    main()

