
    
  
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
  app = Application.builder().token("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()

waiting_user = None
active_chats = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global waiting_user
    user_id = update.message.from_user.id

    if user_id in active_chats:
        await update.message.reply_text("You are already in chat!")
        return

    if waiting_user is None:
        waiting_user = user_id
        await update.message.reply_text("Waiting for partner...")
    else:
        active_chats[user_id] = waiting_user
        active_chats[waiting_user] = user_id
        
        await context.bot.send_message(chat_id=user_id, text="Partner found! Say hi 👋")
        await context.bot.send_message(chat_id=waiting_user, text="Partner found! Say hi 👋")
        
        waiting_user = None

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        await context.bot.send_message(chat_id=partner_id, text=update.message.text)
    else:
        await update.message.reply_text("Use /start to find a partner.")

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id in active_chats:
        partner_id = active_chats[user_id]
        
        del active_chats[partner_id]
        del active_chats[user_id]
        
        await context.bot.send_message(chat_id=partner_id, text="Partner left. Use /start again.")
        await update.message.reply_text("Searching new partner...")
        
        await start(update, context)
    else:
        await update.message.reply_text("You are not in chat.")

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("next", next_chat))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

app.run_polling()



