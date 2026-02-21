import logging
import sqlite3
import math
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes

# States for profile creation
PHOTO, NAME, AGE, GENDER, BIO = range(5)

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
        referral_code TEXT,
        has_profile BOOLEAN DEFAULT FALSE
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        profile_name TEXT,
        profile_photo_file_id TEXT,
        age INTEGER,
        gender TEXT,
        bio TEXT
    )
''')
conn.commit()

# In-memory storage
user_states = {}  # {user_id: {'state': 'idle'|'waiting'|'matched'|'profile_photo', 'partner_id': None, 'preference': None, 'profile_state': 0}}
waiting_queues = {'random': [], 'boys': [], 'girls': []}
online_users = {}  # {user_id: last_active_time}

def init_user(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    if not cursor.fetchone():
        referral_code = str(user_id)[:8]
        cursor.execute('INSERT INTO users (user_id, referral_code) VALUES (?, ?)', (user_id, referral_code))
        conn.commit()

def update_last_active(user_id):
    cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
    conn.commit()
    online_users[user_id] = datetime.now()

def get_user_data(user_id):
    cursor.execute('SELECT credits, is_premium, gender_choices_used, latitude, longitude, referral_code, has_profile FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() or (0, False, 0, None, None, None, False)

def get_profile_data(user_id):
    cursor.execute('SELECT profile_name, profile_photo_file_id, age, gender, bio FROM profiles WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def save_profile(user_id, photo_file_id=None, name=None, age=None, gender=None, bio=None):
    if photo_file_id: cursor.execute('INSERT OR REPLACE INTO profiles (user_id, profile_photo_file_id, profile_name, age, gender, bio) VALUES (?, ?, ?, ?, ?, ?)', (user_id, photo_file_id, name, age, gender, bio))
    else: cursor.execute('INSERT OR REPLACE INTO profiles (user_id, profile_name, age, gender, bio) VALUES (?, ?, ?, ?, ?)', (user_id, name, age, gender, bio))
    cursor.execute('UPDATE users SET has_profile = TRUE WHERE user_id = ?', (user_id,))
    conn.commit()

def increment_gender_choice(user_id):
    cursor.execute('UPDATE users SET gender_choices_used = gender_choices_used + 1 WHERE user_id = ?', (user_id,))
    conn.commit()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_display_name(user_id):
    profile = get_profile_data(user_id)
    if profile and profile[0]:
        name, age, gender = profile[0], profile[2], profile[3]
        return f"{name}, {age}{'M' if gender == 'boy' else 'F'}"
    return "No Profile"

# Profile creation handlers
async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_last_active(user_id)
    await update.message.reply_text("Create your profile (required for chats):\n1. Send photo")
    return PHOTO

async def profile_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    photo_file_id = update.message.photo[-1].file_id
    context.user_data['profile_photo'] = photo_file_id
    await update.message.reply_text("What's your name?")
    return NAME

async def profile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['profile_name'] = update.message.text.strip()
    await update.message.reply_text("Your age? (e.g., 24)")
    return AGE

async def profile_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if not 13 <= age <= 100:
            raise ValueError
        context.user_data['profile_age'] = age
    except:
        await update.message.reply_text("Invalid age (13-100). Try again.")
        return AGE
    keyboard = [[InlineKeyboardButton("Boy", callback_data='boy')], [InlineKeyboardButton("Girl", callback_data='girl')]]
    await update.message.reply_text("Your gender?", reply_markup=InlineKeyboardMarkup(keyboard))
    return GENDER

async def profile_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['profile_gender'] = query.data
    await query.edit_message_text("Tell about yourself (bio):")
    return BIO

async def profile_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = context.user_data
    profile_name = f"{data['profile_name']}"
    save_profile(user_id, data.get('profile_photo'), profile_name, data['profile_age'], data['profile_gender'], update.message.text.strip())
    await update.message.reply_text(f"✅ Profile saved!\nDisplay: {get_display_name(user_id)}\n\nBack to menu.", reply_markup=get_main_menu())
    context.user_data.clear()
    return ConversationHandler.END

async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Profile creation cancelled.", reply_markup=get_main_menu())
    context.user_data.clear()
    return ConversationHandler.END

# Menus
def get_main_menu():
    keyboard = [
        [KeyboardButton("💬 New Anonymous Chat!")],
        [KeyboardButton("👀 Browse People"), KeyboardButton("📍 Nearby People")],
        [KeyboardButton("✏️ My Profile"), KeyboardButton("💎 Credit"), KeyboardButton("😕 Help")],
        [KeyboardButton("⚠️ Refer Friends")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_chat_options_menu():
    keyboard = [
        [InlineKeyboardButton("🎲 Random", callback_data='random')],
        [InlineKeyboardButton("😊 Boy", callback_data='boys'), InlineKeyboardButton("👧 Girl", callback_data='girls')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Other handlers (start, new_chat, etc. - fixed)
async def start(update: Update, context):
    user_id = update.effective_user.id
    init_user(user_id)
    update_last_active(user_id)
    user_states[user_id] = {'state': 'idle', 'partner_id': None, 'preference': None}
    has_profile = get_user_data(user_id)[6]
    text = "Welcome!" if has_profile else "Create profile first: /profile"
    await update.message.reply_text(text, reply_markup=get_main_menu())

async def new_chat(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    if user_states.get(user_id, {}).get('state') != 'idle':
        await update.message.reply_text("Finish current chat: /stop")
        return
    has_profile = get_user_data(user_id)[6]
    if not has_profile:
        await update.message.reply_text("Create profile first: /profile")
        return
    await update.message.reply_text("Choose preference:", reply_markup=get_chat_options_menu())

async def chat_option_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    update_last_active(user_id)
    preference = query.data
    _, is_premium, gender_choices_used, _, _, _, has_profile = get_user_data(user_id)
    if not has_profile:
        await query.edit_message_text("Create /profile first!")
        return
    if preference != 'random' and (gender_choices_used >= 5 and not is_premium):
        await query.edit_message_text("5 free choices used. Random or premium.")
        return
    if preference != 'random':
        increment_gender_choice(user_id)
    # Add to queue ONLY - no auto match
    user_states[user_id] = {'state': 'waiting', 'partner_id': None, 'preference': preference}
    waiting_queues[preference].append(user_id)
    await query.edit_message_text(f"✅ Added to {preference} queue. Waiting...\n/stop to cancel.")
    # Try match after adding
    await try_match_all(context)

async def try_match_all(context):
    # Check all queues for matches
    for queue_key in list(waiting_queues.keys()):
        queue = waiting_queues[queue_key]
        if not queue:
            continue
        user_id = queue[0]
        preference = user_states[user_id]['preference']
        if preference == 'random':
            opposite_queue = waiting_queues['boys'] + waiting_queues['girls'] + waiting_queues['random']
            opposite_queue = [uid for uid in opposite_queue if uid != user_id]
        else:
            opposite = 'girls' if preference == 'boys' else 'boys'
            opposite_queue = waiting_queues[opposite] + waiting_queues['random']
            opposite_queue = [uid for uid in opposite_queue if uid != user_id]
        if opposite_queue:
            partner_id = opposite_queue[0]
            if waiting_queues.get(preference): waiting_queues[preference].pop(0)
            if partner_id in waiting_queues.get(user_states[partner_id]['preference'], []):
                partner_pref = user_states[partner_id]['preference']
                waiting_queues[partner_pref].pop(0)
            user_states[user_id]['state'] = 'matched'
            user_states[user_id]['partner_id'] = partner_id
            user_states[partner_id]['state'] = 'matched'
            user_states[partner_id]['partner_id'] = user_id
            display_u = get_display_name(user_id)
            display_p = get_display_name(partner_id)
            await context.bot.send_message(user_id, f"✅ Matched with {display_p}!\nChat now:", reply_markup=get_chat_menu())
            await context.bot.send_message(partner_id, f"✅ Matched with {display_u}!\nChat now:", reply_markup=get_chat_menu())

# Message handler
async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    state = user_states.get(user_id, {}).get('state')
    if state == 'matched':
        partner_id = user_states[user_id]['partner_id']
        display_name = get_display_name(user_id)
        await context.bot.send_message(partner_id, f"💬 {display_name}: {update.message.text}")
    else:
        await update.message.reply_text("Use 💬 New Anonymous Chat!", reply_markup=get_main_menu())

async def stop(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    state = user_states.get(user_id, {}).get('state')
    if state == 'waiting':
        pref = user_states[user_id]['preference']
        if user_id in waiting_queues.get(pref, []):
            waiting_queues[pref].remove(user_id)
    elif state == 'matched':
        partner_id = user_states[user_id]['partner_id']
        display_name = get_display_name(user_id)
        await context.bot.send_message(partner_id, f"{display_name} left.", reply_markup=get_main_menu())
        user_states[partner_id]['state'] = 'idle'
        user_states[partner_id]['partner_id'] = None
    user_states[user_id] = {'state': 'idle', 'partner_id': None, 'preference': None}
    await update.message.reply_text("Chat ended.", reply_markup=get_main_menu())

# Browse/nearby - show profiles
async def browse_people(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    now = datetime.now()
    online_list = [uid for uid, ts in online_users.items() if now - ts < timedelta(minutes=5)]
    text = f"👥 {len(online_list)} online:\n\n"
    for uid in online_list[:10]:  # Top 10
        text += f"• {get_display_name(uid)}\n"
    text += "\nPremium: /dm @username"
    await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode='Markdown')

async def nearby_people(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    _, _, lat, lon, _, _, _ = get_user_data(user_id)
    if lat is None:
        keyboard = [[KeyboardButton("📍 Share Location", request_location=True)]]
        await update.message.reply_text("Share location?", reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True))
        return
    cursor.execute('SELECT user_id, latitude, longitude FROM users WHERE latitude IS NOT NULL AND user_id != ?', (user_id,))
    nearby = []
    for row in cursor.fetchall():
        uid, ulat, ulon = row
        dist = haversine(lat, lon, ulat, ulon)
        if dist < 50:
            nearby.append((uid, dist))
    nearby.sort(key=lambda x: x[1])
    text = f"📍 {len(nearby)} nearby:\n\n"
    for uid, dist in nearby[:10]:
        text += f"• {get_display_name(uid)} ({dist:.1f}km)\n"
    await update.message.reply_text(text, reply_markup=get_main_menu(), parse_mode='Markdown')

async def handle_location(update: Update, context):
    user_id = update.effective_user.id
    lat, lon = update.message.location.latitude, update.message.location.longitude
    cursor.execute('UPDATE users SET latitude = ?, longitude = ? WHERE user_id = ?', (lat, lon, user_id))
    conn.commit()
    await update.message.reply_text("📍 Saved!", reply_markup=get_main_menu())

# Chat menu callbacks (simple)
def get_chat_menu():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⚠️ Report", callback_data='report'), InlineKeyboardButton("/stop", callback_data='stop')]])

async def chat_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    if query.data == 'report':
        await query.edit_message_text("Report sent.")
    elif query.data == 'stop':
        await stop(query, context)

# Simplified other commands (credit, etc. unchanged but stubbed)
async def credit(update: Update, context): await update.message.reply_text("💎 Credits coming soon!", reply_markup=get_main_menu())
async def help_command(update: Update, context): await update.message.reply_text("💬 New Chat → Wait in queue → Match!", reply_markup=get_main_menu())

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    # Profile conv handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('profile', profile_start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, profile_photo)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_age)],
            GENDER: [CallbackQueryHandler(profile_gender, pattern='^(boy|girl)$')],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_bio)],
        },
        fallbacks=[CommandHandler('cancel', profile_cancel)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('profile', profile_start))
    application.add_handler(CommandHandler('credit', credit))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CallbackQueryHandler(chat_option_callback, pattern='^(random|boys|girls)$'))
    application.add_handler(CallbackQueryHandler(chat_callback, pattern='^(report|stop)$'))
    application.add_handler(MessageHandler(filters.Regex('^💬 New Anonymous Chat!$'), new_chat))
    application.add_handler(MessageHandler(filters.Regex('^(👀 Browse People|📍 Nearby People|✏️ My Profile|💎 Credit|😕 Help|⚠️ Refer Friends)$'), lambda u,c: start(u,c)))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()



