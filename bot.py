
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


TOKEN = '8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA'

# Database setup
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        video_calls_used INTEGER DEFAULT 0,
        audio_calls_used INTEGER DEFAULT 0,
        is_premium BOOLEAN DEFAULT FALSE
    )
''')
conn.commit()

# In-memory storage (use DB for production, but keeping queues in memory for simplicity)
user_states = {}  # {user_id: {'state': 'idle'|'waiting'|'matched'|'calling', 'partner_id': None, 'preference': 'girls'|'boys'}}
waiting_queues = {'girls': [], 'boys': []}  # Queues for waiting users

# Handler for /start
async def start(update: Update, context):
    user_id = update.effective_user.id
    init_user(user_id)
    user_states[user_id] = {'state': 'idle', 'partner_id': None, 'preference': None}
    await update.message.reply_text(
        "Welcome to Anonymous Chat Bot! Use the menu below to get started.",
        reply_markup=get_main_menu()
    )

# Initialize user in DB if not exists
def init_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()

# Get user data from DB
def get_user_data(user_id):
    cursor.execute('SELECT video_calls_used, audio_calls_used, is_premium FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() or (0, 0, False)

# Update call count
def increment_call_count(user_id, call_type):
    if call_type == 'video':
        cursor.execute('UPDATE users SET video_calls_used = video_calls_used + 1 WHERE user_id = ?', (user_id,))
    elif call_type == 'audio':
        cursor.execute('UPDATE users SET audio_calls_used = audio_calls_used + 1 WHERE user_id = ?', (user_id,))
    conn.commit()

# Check if can make call
def can_make_call(user_id, call_type):
    video_used, audio_used, is_premium = get_user_data(user_id)
    if is_premium:
        return True
    if call_type == 'video' and video_used < 5:
        return True
    if call_type == 'audio' and audio_used < 10:
        return True
    return False

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
    
    # Add to queue
    waiting_queues[preference].append(user_id)
    
    # Try to match
    await try_match(user_id, context)
    if user_states[user_id]['state'] == 'waiting':
        await query.edit_message_text("Waiting for a match... Use /stop to cancel.")

# Attempt to match a user
async def try_match(user_id, context):
    preference = user_states[user_id]['preference']
    opposite_queue = 'boys' if preference == 'girls' else 'girls'
    
    if waiting_queues.get(opposite_queue):
        partner_id = waiting_queues[opposite_queue].pop(0)
        if partner_id == user_id:
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
    await query.edit_message_text(f"You rated thumbs {rating}! Thanks for feedback.")
    await context.bot.send_message(query.from_user.id, "Back to main menu.", reply_markup=get_main_menu())

# Callback for report
async def report_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Report submitted. Thanks!")

# Callback for call button
async def call_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = user_states.get(user_id, {}).get('state')
    if state != 'matched':
        await query.edit_message_text("You need to be in a chat to call.")
        return
    await query.edit_message_text("Choose call type:", reply_markup=get_call_options_menu())

# Callback for call options (video/audio)
async def call_option_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    call_type = query.data  # 'video' or 'audio'
    partner_id = user_states[user_id]['partner_id']
    
    if can_make_call(user_id, call_type):
        increment_call_count(user_id, call_type)
        # Placeholder for starting the call
        # NOTE: Actual call implementation requires external integration (e.g., pytgcalls for group voice chats or WebRTC for anonymous P2P).
        # For example, create a temporary group and start voice chat using pytgcalls (requires userbot).
        # See: https://github.com/pytgcalls/pytgcalls
        # Here, we just notify for demo purposes.
        await context.bot.send_message(user_id, f"{call_type.capitalize()} call started with partner! (Placeholder - integrate actual call here)")
        await context.bot.send_message(partner_id, f"Your partner started a {call_type} call! (Placeholder - join here)")
    else:
        await query.edit_message_text("You've reached your free limit. Upgrade to premium for more calls.")
        # Add premium purchase logic here, e.g., send invoice using Telegram Payments.

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
        [InlineKeyboardButton("⚠️ Report", callback_data='report')],
        [InlineKeyboardButton("📞 Call", callback_data='call')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_rating_menu():
    keyboard = [
        [InlineKeyboardButton("👍 Thumbs Up", callback_data='up'), InlineKeyboardButton("👎 Thumbs Down", callback_data='down')]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_call_options_menu():
    keyboard = [
        [InlineKeyboardButton("📹 Video Call", callback_data='video')],
        [InlineKeyboardButton("🔊 Audio Call", callback_data='audio')]
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
    application.add_handler(CallbackQueryHandler(call_callback, pattern='^call$'))
    application.add_handler(CallbackQueryHandler(call_option_callback, pattern='^(video|audio)$'))
    application.add_handler(MessageHandler(filters.Regex('^⚡ Find a Partner$'), find_partner))
    application.add_handler(MessageHandler(filters.Regex('^(👻 Match with girls|😊 Match with boys)$'), find_partner))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()
