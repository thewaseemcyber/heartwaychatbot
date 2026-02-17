
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA'

# In-memory storage (use DB for production)
user_states = {}  # {user_id: {'state': 'idle'|'waiting'|'matched', 'partner_id': None, 'preference': 'girls'|'boys'}}
waiting_queues = {'girls': [], 'boys': []}  # Queues for waiting users

# Handler for /start
async def start(update: Update, context):
    user_id = update.effective_user.id
    user_states[user_id] = {'state': 'idle', 'partner_id': None, 'preference': None}
    await update.message.reply_text(
        "Welcome to Anonymous Chat Bot! Use the menu below to get started.",
        reply_markup=get_main_menu()
    )

# Handler for /find (or button "Find a Partner")
async def find_partner(update: Update, context):
    user_id = update.effective_user.id
    if user_states.get(user_id, {}).get('state') != 'idle':
        await update.message.reply_text("You're already in a chat or waiting. Use /stop to reset.")
        return
    await update.message.reply_text(
        "Choose your match preference:",
        reply_markup=get_preference_menu()
    )

# Callback for preference selection
async def preference_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    preference = query.data  # 'girls' or 'boys'
    user_states[user_id] = {'state': 'waiting', 'partner_id': None, 'preference': preference}
    
    # Add to queue (queue for what they want to match with)
    waiting_queues[preference].append(user_id)
    
    # Try to match
    await try_match(user_id, context)
    if user_states[user_id]['state'] == 'waiting':
        await query.edit_message_text("Waiting for a match... Use /stop to cancel.")

# Attempt to match a user
async def try_match(user_id, context):
    preference = user_states[user_id]['preference']
    opposite_queue = 'boys' if preference == 'girls' else 'girls'  # Assume binary for simplicity; extend as needed
    
    if waiting_queues.get(opposite_queue):
        partner_id = waiting_queues[opposite_queue].pop(0)
        if partner_id == user_id:  # Avoid self-match
            waiting_queues[opposite_queue].append(partner_id)
            return
        
        # Match them
        user_states[user_id]['state'] = 'matched'
        user_states[user_id]['partner_id'] = partner_id
        user_states[partner_id]['state'] = 'matched'
        user_states[partner_id]['partner_id'] = user_id
        
        # Notify both
        await context.bot.send_message(user_id, "Matched! Start chatting anonymously.", reply_markup=get_chat_menu())
        await context.bot.send_message(partner_id, "Matched! Start chatting anonymously.", reply_markup=get_chat_menu())

# Handler for messages (proxy if matched)
async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    state = user_states.get(user_id, {}).get('state')
    
    if state == 'matched':
        partner_id = user_states[user_id]['partner_id']
        await context.bot.send_message(partner_id, update.message.text)  # Forward anonymously
    else:
        await update.message.reply_text("Send /find to start matching.")

# Handler for /stop (leave chat)
async def stop(update: Update, context):
    user_id = update.effective_user.id
    state = user_states.get(user_id, {}).get('state')
    
    if state in ['waiting', 'matched']:
        if state == 'waiting':
            preference = user_states[user_id]['preference']
            waiting_queues[preference].remove(user_id)
        elif state == 'matched':
            partner_id = user_states[user_id]['partner_id']
            await context.bot.send_message(partner_id, "Your partner left the chat.", reply_markup=get_main_menu())
            user_states[partner_id]['state'] = 'idle'
            user_states[partner_id]['partner_id'] = None
        
        user_states[user_id]['state'] = 'idle'
        user_states[user_id]['partner_id'] = None
        await update.message.reply_text("You left the chat. Rate your partner?", reply_markup=get_rating_menu())
    else:
        await update.message.reply_text("Nothing to stop. Use /find to start.")

# Callback for rating (thumbs up/down)
async def rating_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    rating = query.data  # 'up' or 'down'
    # Here, you could store rating anonymously for algo improvement (e.g., in DB)
    await query.edit_message_text(f"You rated thumbs {rating}! Thanks for feedback.")
    await context.bot.send_message(query.from_user.id, "Back to main menu.", reply_markup=get_main_menu())

# Callback for report
async def report_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    # In production, log report with details for moderation
    await query.edit_message_text("Report submitted. Thanks!")

# Menus
def get_main_menu():
    keyboard = [
        [KeyboardButton("⚡ Find a Partner")],
        [KeyboardButton("👻 Match with girls"), KeyboardButton("😊 Match with boys")],
        [KeyboardButton("👤 My Profile"), KeyboardButton("⚙️ Settings")],
        [KeyboardButton("💎 Premium")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_preference_menu():
    keyboard = [
        [InlineKeyboardButton("👻 Match with girls", callback_data='girls')],
        [InlineKeyboardButton("😊 Match with boys", callback_data='boys')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_chat_menu():
    keyboard = [
        [InlineKeyboardButton("👍", callback_data='up'), InlineKeyboardButton("👎", callback_data='down')],
        [InlineKeyboardButton("⚠️ Report", callback_data='report')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_rating_menu():
    keyboard = [
        [InlineKeyboardButton("👍 Thumbs Up", callback_data='up'), InlineKeyboardButton("👎 Thumbs Down", callback_data='down')]
    ]
    return InlineKeyboardMarkup(keyboard)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('find', find_partner))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(preference_callback, pattern='^(girls|boys)$'))
    application.add_handler(CallbackQueryHandler(rating_callback, pattern='^(up|down)$'))
    application.add_handler(CallbackQueryHandler(report_callback, pattern='^report$'))
    application.add_handler(MessageHandler(filters.Regex('^⚡ Find a Partner$'), find_partner))  # Handle button as command
    application.add_handler(MessageHandler(filters.Regex('^(👻 Match with girls|😊 Match with boys)$'), find_partner))  # Direct match buttons
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Proxy messages

    application.run_polling()
