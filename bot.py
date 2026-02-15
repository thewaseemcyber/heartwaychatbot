print("✅ Srinagar's #1 Anonymous Chat")
    
    app = Application.builder().token("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(start_chat, pattern="^start_chat$"))
    app.add_handler(CallbackQueryHandler(vip, pattern="^vip$"))
    app.add_handler(CallbackQueryHandler(back, pattern="^back$"))
    app.add_handler(CallbackQueryHandler(vip_placeholder, pattern="^(vip_age|vip_interest|vip_media|vip_unlimited|vip_99|vip_259|vip_599|vip_free|vip_free_trial|messages)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ v10.0 LIVE - Tikible Clone Perfect!")
    app.run_polling()

if name == "main":
    main()
