import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = '8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA'

# Database setup (for future expansions like credits)
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        credits INTEGER DEFAULT 0
    )
''')
conn.commit()

# In-memory storage
user_states = {}  # {user_id: {'state': 'idle'|'waiting'|'matched', 'partner_id': None, 'preference': None}}
waiting_queues = {'random': [], 'boys': [], 'girls': []}  # Extended for random

# Handler for /start and "New Anonymous Chat!"
async def new_chat(update: Update, context):
    user_id = update.effective_user.id
    init_user(user_id)
    user_states[user_id] = {'state': 'idle', 'partner_id': None, 'preference': None}
    await update.message.reply_text(
        "New Anonymous Chat! Choose who you want to chat with:",
        reply_markup=get_chat_options_menu()
    )

# Initialize user in DB
def init_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()

# Callback for chat options
async def chat_option_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    preference = query.data  # 'random', 'boys', 'girls'
    user_states[user_id] = {'state': 'waiting', 'partner_id': None, 'preference': preference}
    
    # Add to queue
    waiting_queues[preference].append(user_id)
    
    # Try to match (for random, pick from any)
    await try_match(user_id, context)
    if user_states[user_id]['state'] == 'waiting':
        await query.edit_message_text("Waiting for a match... Use /stop to cancel.", reply_markup=get_main_menu())

# Attempt to match
async def try_match(user_id, context):
    preference = user_states[user_id]['preference']
    if preference == 'random':
        opposite_queue = waiting_queues['boys'] + waiting_queues['girls'] + waiting_queues['random']
    else:
        opposite = 'girls' if preference == 'boys' else 'boys'
        opposite_queue = waiting_queues[opposite]
    
    if opposite_queue:
        partner_id = opposite_queue.pop(0)
        if partner_id == user_id:
            opposite_queue.append(partner_id)
            return
        
        user_states[user_id]['state'] = 'matched'
        user_states[user_id]['partner_id'] = partner_id
        user_states[partner_id]['state'] = 'matched'
        user_states[partner_id]['partner_id'] = user_id
        
        await context.bot.send_message(user_id, "Matched! Start chatting anonymously.", reply_markup=get_chat_menu())
        await context.bot.send_message(partner_id, "Matched! Start chatting anonymously.", reply_markup=get_chat_menu())

# Handler for messages (proxy if matched)
async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    state = user_states.get(user_id, {}).get('state')
    
    if state == 'matched':
        partner_id = user_states[user_id]['partner_id']
        await context.bot.send_message(partner_id, update.message.text)
    else:
        await update.message.reply_text("Use the menu to start a chat.")

# Handler for /stop
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
        await update.message.reply_text("Nothing to stop.", reply_markup=get_main_menu())

# Callback for rating
async def rating_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    rating = query.data
    await query.edit_message_text(f"You rated thumbs {rating}! Thanks.")
    await context.bot.send_message(query.from_user.id, "Back to main menu.", reply_markup=get_main_menu())

# Callback for report
async def report_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Report submitted. Thanks!")

# Placeholder handlers for other menu items
async def browse_people(update: Update, context):
    await update.message.reply_text("Browse People feature coming soon!", reply_markup=get_main_menu())

async def nearby_people(update: Update, context):
    await update.message.reply_text("Share your location to find nearby people.", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Share Location", request_location=True)]], one_time_keyboard=True))

async def handle_location(update: Update, context):
    await update.message.reply_text("Nearby matches found! (Simulation)", reply_markup=get_main_menu())

async def credit(update: Update, context):
    user_id = update.effective_user.id
    cursor.execute('SELECT credits FROM users WHERE user_id = ?', (user_id,))
    credits = cursor.fetchone()[0]
    await update.message.reply_text(f"You have {credits} credits.", reply_markup=get_main_menu())

async def profile(update: Update, context):
    await update.message.reply_text("Your profile: Edit coming soon!", reply_markup=get_main_menu())

async def help_command(update: Update, context):
    await update.message.reply_text("Help: Use menu to navigate. /stop to leave chat.", reply_markup=get_main_menu())

async def refer_friends(update: Update, context):
    await update.message.reply_text("Refer friends for free credits! Share this link: t.me/yourbotusername", reply_markup=get_main_menu())

# Menus
def get_main_menu():
    keyboard = [
        [KeyboardButton("💬 New Anonymous Chat!")],
        [KeyboardButton("👀 Browse People"), KeyboardButton("📍 Nearby People")],
        [KeyboardButton("💎 Credit"), KeyboardButton("👤 Profile"), KeyboardButton("😕 Help")],
        [KeyboardButton("⚠️ Refer to Friends (Free Credit)")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_chat_options_menu():
    keyboard = [
        [InlineKeyboardButton("🎲 Chat with a Random", callback_data='random')],
        [InlineKeyboardButton("😊 Chat with a Boy", callback_data='boys'), InlineKeyboardButton("👧 Chat with a Girl", callback_data='girls')]
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
    application.add_handler(CommandHandler('start', new_chat))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CallbackQueryHandler(chat_option_callback, pattern='^(random|boys|girls)$'))
    application.add_handler(CallbackQueryHandler(rating_callback, pattern='^(up|down)$'))
    application.add_handler(CallbackQueryHandler(report_callback, pattern='^report$'))
    application.add_handler(MessageHandler(filters.Regex('^💬 New Anonymous Chat!$'), new_chat))
    application.add_handler(MessageHandler(filters.Regex('^👀 Browse People$'), browse_people))
    application.add_handler(MessageHandler(filters.Regex('^📍 Nearby People$'), nearby_people))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.Regex('^💎 Credit$'), credit))
    application.add_handler(MessageHandler(filters.Regex('^👤 Profile$'), profile))
    application.add_handler(MessageHandler(filters.Regex('^😕 Help$'), help_command))
    application.add_handler(MessageHandler(filters.Regex('^⚠️ Refer to Friends \(Free Credit\)$'), refer_friends))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()
