import logging
import sqlite3
import math
from datetime import datetime, timedelta
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
        credits INTEGER DEFAULT 0,
        is_premium BOOLEAN DEFAULT FALSE,
        gender_choices_used INTEGER DEFAULT 0,
        latitude REAL,
        longitude REAL,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        referral_code TEXT
    )
''')
conn.commit()

# In-memory storage
user_states = {}  # {user_id: {'state': 'idle'|'waiting'|'matched', 'partner_id': None, 'preference': None}}
waiting_queues = {'random': [], 'boys': [], 'girls': []}
online_users = {}  # {user_id: last_active_time}

# Initialize user
def init_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        referral_code = str(user_id)[:8]  # Simple code
        cursor.execute('INSERT INTO users (user_id, referral_code) VALUES (?, ?)', (user_id, referral_code))
        conn.commit()

# Update last active
def update_last_active(user_id):
    cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
    conn.commit()
    online_users[user_id] = datetime.now()

# Get user data
def get_user_data(user_id):
    cursor.execute('SELECT credits, is_premium, gender_choices_used, latitude, longitude, referral_code FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() or (0, False, 0, None, None, None)

# Increment gender choice
def increment_gender_choice(user_id):
    cursor.execute('UPDATE users SET gender_choices_used = gender_choices_used + 1 WHERE user_id = ?', (user_id,))
    conn.commit()

# Haversine distance
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# Handler for /start
async def start(update: Update, context):
    user_id = update.effective_user.id
    init_user(user_id)
    update_last_active(user_id)
    user_states[user_id] = {'state': 'idle', 'partner_id': None, 'preference': None}
    await update.message.reply_text("Welcome! Use the menu to start.", reply_markup=get_main_menu())

# Handler for new chat
async def new_chat(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    init_user(user_id)
    if user_states.get(user_id, {}).get('state') != 'idle':
        await update.message.reply_text("Finish current chat with /stop.")
        return
    await update.message.reply_text("New Anonymous Chat! Choose who you want to chat with:", reply_markup=get_chat_options_menu())

# Chat option callback
async def chat_option_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_active(user_id)
    preference = query.data
    _, is_premium, gender_choices_used, _, _, _ = get_user_data(user_id)
    if preference != 'random' and (gender_choices_used >= 5 and not is_premium):
        await query.edit_message_text("You've used your 5 free gender-specific choices. Upgrade to premium or use random.")
        return
    if preference != 'random':
        increment_gender_choice(user_id)
    user_states[user_id] = {'state': 'waiting', 'partner_id': None, 'preference': preference}
    waiting_queues[preference].append(user_id)
    await try_match(user_id, context)
    if user_states[user_id]['state'] == 'waiting':
        await query.edit_message_text("Waiting for a match... /stop to cancel.")

# Match logic (same as before)
async def try_match(user_id, context):
    preference = user_states[user_id]['preference']
    if preference == 'random':
        opposite_queue = waiting_queues['boys'] + waiting_queues['girls'] + waiting_queues['random']
    else:
        opposite = 'girls' if preference == 'boys' else 'boys'
        opposite_queue = waiting_queues[opposite] + waiting_queues['random']
    if opposite_queue:
        partner_id = opposite_queue.pop(0)
        if partner_id == user_id: return
        user_states[user_id]['state'] = 'matched'
        user_states[user_id]['partner_id'] = partner_id
        user_states[partner_id]['state'] = 'matched'
        user_states[partner_id]['partner_id'] = user_id
        await context.bot.send_message(user_id, "Matched! Chat anonymously.", reply_markup=get_chat_menu())
        await context.bot.send_message(partner_id, "Matched! Chat anonymously.", reply_markup=get_chat_menu())

# Message handler
async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    state = user_states.get(user_id, {}).get('state')
    if state == 'matched':
        partner_id = user_states[user_id]['partner_id']
        await context.bot.send_message(partner_id, update.message.text)
    else:
        await update.message.reply_text("Use /newchat to start.")

# Stop handler (same)
async def stop(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    state = user_states.get(user_id, {}).get('state')
    if state in ['waiting', 'matched']:
        if state == 'waiting':
            waiting_queues[user_states[user_id]['preference']].remove(user_id)
        elif state == 'matched':
            partner_id = user_states[user_id]['partner_id']
            await context.bot.send_message(partner_id, "Partner left.", reply_markup=get_main_menu())
            user_states[partner_id]['state'] = 'idle'
            user_states[partner_id]['partner_id'] = None
        user_states[user_id]['state'] = 'idle'
        user_states[user_id]['partner_id'] = None
        await update.message.reply_text("Left chat. Rate?", reply_markup=get_rating_menu())
    else:
        await update.message.reply_text("No active chat.", reply_markup=get_main_menu())

# Rating and report (same)
async def rating_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Thanks for rating!")
    await context.bot.send_message(query.from_user.id, "Back to menu.", reply_markup=get_main_menu())

async def report_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Report submitted!")

# Browse people
async def browse_people(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    _, is_premium, _, _, _, _ = get_user_data(user_id)
    # Get online users (last active < 5 min)
    now = datetime.now()
    online_list = [uid for uid, ts in online_users.items() if now - ts < timedelta(minutes=5)]
    text = f"{len(online_list)} people online.\n"
    for uid in online_list:
        username = (await context.bot.get_chat(uid)).username or "Anonymous"
        text += f"- @{username}\n"
    text += "\nProfiles visible. Premium can DM."
    if is_premium:
        text += "\nUse /dm <username> to message."
    await update.message.reply_text(text, reply_markup=get_main_menu())

# Nearby people
async def nearby_people(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    _, is_premium, lat, lon, _, _ = get_user_data(user_id)
    if lat is None or lon is None:
        keyboard = [[KeyboardButton("Share Location", request_location=True)]]
        await update.message.reply_text("Share location for nearby.", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return
    cursor.execute('SELECT user_id, latitude, longitude FROM users WHERE latitude IS NOT NULL AND user_id != ?', (user_id,))
    nearby = []
    for row in cursor.fetchall():
        uid, ulat, ulon = row
        dist = haversine(lat, lon, ulat, ulon)
        if dist < 50:  # 50km
            nearby.append((uid, dist))
    nearby.sort(key=lambda x: x[1])
    text = f"{len(nearby)} nearby people.\n"
    for uid, dist in nearby:
        username = (await context.bot.get_chat(uid)).username or "Anonymous"
        text += f"- @{username} ({dist:.1f}km)\n"
    text += "\nProfiles visible. Premium can DM."
    if is_premium:
        text += "\nUse /dm <username> to message."
    await update.message.reply_text(text, reply_markup=get_main_menu())

# Handle location
async def handle_location(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    cursor.execute('UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?', (lat, lon, user_id))
    conn.commit()
    await update.message.reply_text("Location saved! Now finding nearby.", reply_markup=get_main_menu())
    await nearby_people(update, context)  # Auto show

# Credit
async def credit(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    credits, _, _, _, _, ref_code = get_user_data(user_id)
    text = f"💎 Your current Credit: {credits}\n\n? How can I get Credit?\n\n1 Invite friends (Free)\nShare your personal invite link ⚡ (/link) with friends and earn 50 Credit for each referral.\n\n2 Buy Credit\nChoose one of the plans below 👇"
    keyboard = [
        [InlineKeyboardButton("💎 280 Credits → ⭐ 100", callback_data='buy_280')],
        [InlineKeyboardButton("💎 500 Credits → ⭐ 151", callback_data='buy_500')],
        [InlineKeyboardButton("💎 1300 Credits → ⭐ 222", callback_data='buy_1300')],
        [InlineKeyboardButton("💎 2500 Credits → ⭐ 318", callback_data='buy_2500')],
        [InlineKeyboardButton("💎 6200 Credits VIP 🎉 → ⭐ 740", callback_data='buy_6200')]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# Buy callback (placeholder - integrate payments)
async def buy_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    # Example: Use Telegram payments - send_invoice
    await query.edit_message_text("Payment processing... (Implement send_invoice here)")

# Profile, help, refer (placeholders)
async def profile(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    await update.message.reply_text("Your profile: Edit coming soon!", reply_markup=get_main_menu())

async def help_command(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    await update.message.reply_text("Help: /newchat start, /stop end.", reply_markup=get_main_menu())

async def refer_friends(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    _, _, _, _, _, ref_code = get_user_data(user_id)
    await update.message.reply_text(f"Share: t.me/yourbot?start={ref_code} for 50 credits per referral!", reply_markup=get_main_menu())

# DM command (premium only)
async def dm(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    _, is_premium, _, _, _, _ = get_user_data(user_id)
    if not is_premium:
        await update.message.reply_text("Premium only.")
        return
    if not context.args:
        await update.message.reply_text("Use /dm <username> <message>")
        return
    username = context.args[0].lstrip('@')
    message = ' '.join(context.args[1:])
    try:
        target = await context.bot.get_chat(f'@{username}')
        await context.bot.send_message(target.id, f"DM from anonymous: {message}")
        await update.message.reply_text("Sent!")
    except:
        await update.message.reply_text("User not found.")

# Link command for referral
async def link(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    _, _, _, _, _, ref_code = get_user_data(user_id)
    await update.message.reply_text(f"Your link: t.me/yourbot?start={ref_code}")

# Handle referrals in /start
async def handle_referral(update: Update, context):
    if context.args and context.args[0].isdigit():
        ref_code = context.args[0]
        cursor.execute('SELECT user_id FROM users WHERE referral_code = ?', (ref_code,))
        referrer = cursor.fetchone()
        if referrer:
            referrer_id = referrer[0]
            cursor.execute('UPDATE users SET credits = credits + 50 WHERE user_id = ?', (referrer_id,))
            conn.commit()
            await context.bot.send_message(referrer_id, "Referral success! +50 credits.")
    await start(update, context)

# Menus (same)
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
        [InlineKeyboardButton("👍", callback_data='up'), InlineKeyboardButton("👎", callback_data='down')]
    ]
    return InlineKeyboardMarkup(keyboard)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', handle_referral))
    application.add_handler(CommandHandler('newchat', new_chat))
    application.add_handler(CommandHandler('browse', browse_people))
    application.add_handler(CommandHandler('nearby', nearby_people))
    application.add_handler(CommandHandler('credit', credit))
    application.add_handler(CommandHandler('profile', profile))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('refer', refer_friends))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('dm', dm))
    application.add_handler(CommandHandler('link', link))
    application.add_handler(CallbackQueryHandler(chat_option_callback, pattern='^(random|boys|girls)$'))
    application.add_handler(CallbackQueryHandler(rating_callback, pattern='^(up|down)$'))
    application.add_handler(CallbackQueryHandler(report_callback, pattern='^report$'))
    application.add_handler(CallbackQueryHandler(buy_callback, pattern='^buy_'))
    application.add_handler(MessageHandler(filters.Regex('^💬 New Anonymous Chat!$'), new_chat))
    application.add_handler(MessageHandler(filters.Regex('^👀 Browse People$'), browse_people))
    application.add_handler(MessageHandler(filters.Regex('^📍 Nearby People$'), nearby_people))
    application.add_handler(MessageHandler(filters.Regex('^💎 Credit$'), credit))
    application.add_handler(MessageHandler(filters.Regex('^👤 Profile$'), profile))
    application.add_handler(MessageHandler(filters.Regex('^😕 Help$'), help_command))
    application.add_handler(MessageHandler(filters.Regex('^⚠️ Refer to Friends \(Free Credit\)$'), refer_friends))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()


