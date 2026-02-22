"""
@Heartwaychatbot v25.0 - NO SELF-MATCHING FIXED!
REAL 2+ USERS ONLY matching
"""

import logging
import sqlite3
import os
import math
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, 
    ConversationHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv('BOT_TOKEN', '8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA')

# Database
conn = sqlite3.connect('heartway.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, credits INTEGER DEFAULT 0, has_profile INTEGER DEFAULT 0,
    lat REAL, lon REAL, gps_enabled INTEGER DEFAULT 0, last_active TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY, photo_id TEXT, name TEXT, age INTEGER, 
    gender TEXT, city TEXT, bio TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS likes (
    user_id INTEGER, liked_id INTEGER, PRIMARY KEY(user_id, liked_id)
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS blocked (
    user_id INTEGER, blocked_id INTEGER, PRIMARY KEY(user_id, blocked_id)
)''')
conn.commit()

PHOTO, NAME_INP, AGE_INP, GENDER_SEL, CITY_INP, BIO_INP = range(6)

waiting_users = {'random': [], 'boys': [], 'girls': []}
active_chats = {}
online_users = {}

def check_profile_exists(uid):
    cursor.execute('SELECT 1 FROM profiles WHERE user_id = ?', (uid,))
    return cursor.fetchone() is not None

def get_user_data(uid):
    cursor.execute('SELECT credits, has_profile, lat, lon, gps_enabled, last_active FROM users WHERE user_id = ?', (uid,))
    data = cursor.fetchone()
    if not data:
        cursor.execute('INSERT INTO users (user_id) VALUES (?)', (uid,))
        conn.commit()
        return (0, 0, None, None, 0, None)
    return data

def get_profile(uid):
    cursor.execute('SELECT photo_id, name, age, gender, city, bio FROM profiles WHERE user_id = ?', (uid,))
    return cursor.fetchone()

def save_profile(uid, photo_id, name, age, gender, city, bio):
    cursor.execute('''INSERT OR REPLACE INTO profiles 
        (user_id, photo_id, name, age, gender, city, bio) 
        VALUES (?, ?, ?, ?, ?, ?, ?)''', (uid, photo_id, name, age, gender, city, bio))
    cursor.execute('UPDATE users SET has_profile = 1 WHERE user_id = ?', (uid,))
    conn.commit()

def get_display_name(uid):
    prof = get_profile(uid)
    if prof and prof[1]:
        name, age, gender = prof[1], prof[2], prof[3]
        return f"{name}, {age}{'M' if gender=='boy' else 'F'}"
    return "No Profile"

def update_online(uid):
    online_users[uid] = datetime.now()
    cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ?', 
                  (datetime.now().isoformat(), uid))
    conn.commit()

def get_online_users():
    now = datetime.now()
    cursor.execute('SELECT user_id FROM users WHERE last_active > ? AND has_profile = 1', 
                  ((now - timedelta(minutes=5)).isoformat(),))
    return [row[0] for row in cursor.fetchall()]

# === KEYBOARDS ===
def main_keyboard():
    return ReplyKeyboardMarkup([
        ['💬 New Chat'],
        ['👀 Browse People', '📍 Nearby People'],
        ['✏️ My Profile', '💎 Credits'], 
        ['❓ Help']
    ], resize_keyboard=True)

def chat_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('👍 Like', callback_data='like'), InlineKeyboardButton('🚫 Block', callback_data='block')],
        [InlineKeyboardButton('⚠️ Report', callback_data='report'), InlineKeyboardButton('🔚 Stop', callback_data='stop')]
    ])

def preference_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🎲 Random', callback_data='random')],
        [InlineKeyboardButton('👦 Boy', callback_data='boys'), InlineKeyboardButton('👧 Girl', callback_data='girls')]
    ])

# === PROFILE CREATION ===
async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    if check_profile_exists(uid):
        await show_profile(update, context)
        return ConversationHandler.END
    await update.message.reply_text('📸 Send profile photo:')
    return PHOTO

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['photo'] = update.message.photo[-1].file_id
    await update.message.reply_text('👤 Your name:')
    return NAME_INP

async def name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text('🕐 Your age (13-100):')
    return AGE_INP

async def age_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        age = int(update.message.text)
        if 13 <= age <= 100:
            context.user_data['age'] = age
            kb = [[InlineKeyboardButton('👦 Boy', callback_data='boy')], 
                  [InlineKeyboardButton('👧 Girl', callback_data='girl')]]
            await update.message.reply_text('⚥ Gender:', reply_markup=InlineKeyboardMarkup(kb))
            return GENDER_SEL
        await update.message.reply_text('❌ Age 13-100 only:')
        return AGE_INP
    except:
        await update.message.reply_text('❌ Enter number:')
        return AGE_INP

async def gender_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['gender'] = query.data
    await query.edit_message_text('📍 Your city:')
    return CITY_INP

async def city_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['city'] = update.message.text.strip()
    await update.message.reply_text('📝 Short bio:')
    return BIO_INP

async def bio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = update.effective_user.id
    data = context.user_data
    save_profile(uid, data['photo'], data['name'], data['age'], 
                data['gender'], data['city'], update.message.text.strip())
    await show_profile(update, context)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('❌ Cancelled.', reply_markup=main_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    prof = get_profile(uid)
    
    if not prof or not prof[1]:
        await update.message.reply_text('❌ No profile. Use /profile', reply_markup=main_keyboard())
        return
    
    photo_id, name, age, gender, city, bio = prof
    text = f"""👤 {name}
⚥ {'Boy' if gender == 'boy' else 'Girl'}
📍 {city}
🕐 Age: {age}

📝 {bio or 'No bio'}

👥 Liked List | 🚫 Blocked
⚙️ Advanced Settings"""

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton('✏️ Edit Profile', callback_data='edit')],
        [InlineKeyboardButton('👥 Liked List', callback_data='liked_list'), InlineKeyboardButton('🚫 Blocked', callback_data='blocked_list')],
        [InlineKeyboardButton('⚙️ Advanced Settings', callback_data='settings')]
    ])
    
    if photo_id:
        await context.bot.send_photo(uid, photo_id, caption=text, reply_markup=kb, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode='Markdown')

# === PROFILE BUTTONS ===
async def profile_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    
    if query.data == 'liked_list':
        cursor.execute('SELECT liked_id FROM likes WHERE user_id = ?', (uid,))
        likes = cursor.fetchall()
        if likes:
            text = '👥 Liked users:\n' + '\n'.join([get_display_name(l[0]) for l in likes[:5]])
        else:
            text = '👥 No liked users yet'
        await query.edit_message_text(text)
        
    elif query.data == 'blocked_list':
        cursor.execute('SELECT blocked_id FROM blocked WHERE user_id = ?', (uid,))
        blocks = cursor.fetchall()
        if blocks:
            text = '🚫 Blocked users:\n' + '\n'.join([get_display_name(b[0]) for b in blocks[:5]])
        else:
            text = '🚫 No blocked users'
        await query.edit_message_text(text)
        
    elif query.data == 'settings':
        await query.edit_message_text('⚙️ Settings coming soon!')
    elif query.data == 'edit':
        await query.edit_message_text('✏️ Edit: /profile')

# === FIXED MATCHING - NO SELF-MATCH ===
async def new_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_online(uid)
    
    if uid in active_chats:
        await update.message.reply_text('❌ Already in chat! /stop first.', reply_markup=main_keyboard())
        return
        
    if not check_profile_exists(uid):
        await update.message.reply_text('❌ Create /profile first!', reply_markup=main_keyboard())
        return
    
    await update.message.reply_text('Choose preference:', reply_markup=preference_keyboard())

async def chat_preference(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    pref = query.data
    
    # FIXED: Remove user from ALL queues first
    for queue in waiting_users.values():
        if uid in queue:
            queue.remove(uid)
    
    waiting_users[pref].append(uid)
    
    # Show queue status
    total_waiting = len(waiting_users[pref]) - 1  # exclude self
    await query.edit_message_text(f'✅ In {pref} queue\n👥 {total_waiting} others waiting...\n/stop to cancel')
    
    # Try match
    await try_real_match(context)

async def try_real_match(context: ContextTypes.DEFAULT_TYPE):
    """🚨 FIXED: NO SELF-MATCH + NEEDS 2+ DIFFERENT USERS"""
    for pref, queue in waiting_users.items():
        if len(queue) >= 2:
            # Take first 2 users
            u1 = queue.pop(0)
            u2 = queue.pop(0)
            
            # 🚨 CRITICAL: Check different users
            if u1 != u2 and get_profile(u1) and get_profile(u2):
                active_chats[u1] = u2
                active_chats[u2] = u1
                
                name1 = get_display_name(u1)
                name2 = get_display_name(u2)
                
                await context.bot.send_message(u1, f'✅ MATCHED with {name2}! 🎉', reply_markup=chat_keyboard())
                await context.bot.send_message(u2, f'✅ MATCHED with {name1}! 🎉', reply_markup=chat_keyboard())
                return True
            else:
                # Put back if invalid
                queue.insert(0, u2)
                queue.insert(0, u1)
    return False

# === REAL USER LISTS ===
async def browse_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_online(update.effective_user.id)
    online = get_online_users()
    
    if not online:
        await update.message.reply_text('👥 No users online', reply_markup=main_keyboard())
        return
    
    text = f'👥 {len(online)} online:\n\n'
    for uid in online[:10]:
        if uid != update.effective_user.id:  # Exclude self
            text += f'• {get_display_name(uid)}\n'
    
    await update.message.reply_text(text, reply_markup=main_keyboard())

async def nearby_people(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('📍 Nearby coming soon!', reply_markup=main_keyboard())

# === COMMANDS ===
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_online(uid)
    if check_profile_exists(uid):
        await update.message.reply_text('🎉 Welcome back!', reply_markup=main_keyboard())
    else:
        await update.message.reply_text('🎉 Welcome! Create /profile', reply_markup=main_keyboard())

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in active_chats:
        partner = active_chats.pop(uid)
        active_chats.pop(partner, None)
        try:
            await context.bot.send_message(partner, '💔 Partner left chat.', reply_markup=main_keyboard())
        except:
            pass
    await update.message.reply_text('🔚 Chat ended.', reply_markup=main_keyboard())

# === CHAT MESSAGES ===
async def chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_online(uid)
    
    # Active chat
    if uid in active_chats:
        partner = active_chats[uid]
        name = get_display_name(uid)
        try:
            await context.bot.send_message(partner, f'💬 *{name}*: {update.message.text}', parse_mode='Markdown')
        except:
            await update.message.reply_text('Partner disconnected.', reply_markup=main_keyboard())
            active_chats.pop(uid, None)
            active_chats.pop(partner, None)
        return
    
    # Keyboard buttons
    text = update.message.text
    if text == '💬 New Chat':
        await new_chat_handler(update, context)
    elif text == '✏️ My Profile':
        await profile_start(update, context)
    elif text == '💎 Credits':
        await update.message.reply_text('💎 Credits coming soon!', reply_markup=main_keyboard())
    elif text == '👀 Browse People':
        await browse_people(update, context)
    elif text == '📍 Nearby People':
        await nearby_people(update, context)
    elif text == '❓ Help':
        await update.message.reply_text('💬 New Chat → Wait → Match → Chat!\nNeeds 2+ users!', reply_markup=main_keyboard())

# === ALL CALLBACKS ===
async def all_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data
    
    update_online(uid)
    
    if data in ['random', 'boys', 'girls']:
        await chat_preference(update, context)
    elif data == 'like':
        partner = active_chats.get(uid)
        if partner and partner != uid:
            cursor.execute('INSERT OR IGNORE INTO likes (user_id, liked_id) VALUES (?, ?)', (uid, partner))
            conn.commit()
            await query.answer('👍 Liked!')
    elif data == 'block':
        partner = active_chats.get(uid)
        if partner and partner != uid:
            cursor.execute('INSERT OR IGNORE INTO blocked (user_id, blocked_id) VALUES (?, ?)', (uid, partner))
            conn.commit()
            active_chats.pop(uid, None)
            active_chats.pop(partner, None)
            await query.answer('🚫 Blocked!')
    elif data == 'stop':
        await cmd_stop(query, context)
    elif data in ['liked_list', 'blocked_list', 'settings', 'edit']:
        await profile_buttons(update, context)

# === MAIN APP ===
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    
    profile_handler = ConversationHandler(
        entry_points=[CommandHandler('profile', profile_start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO, photo_handler)],
            NAME_INP: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_handler)],
            AGE_INP: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler)],
            GENDER_SEL: [CallbackQueryHandler(gender_handler)],
            CITY_INP: [MessageHandler(filters.TEXT & ~filters.COMMAND, city_handler)],
            BIO_INP: [MessageHandler(filters.TEXT & ~filters.COMMAND, bio_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel_profile)]
    )
    
    app.add_handler(profile_handler)
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('stop', cmd_stop))
    app.add_handler(CallbackQueryHandler(all_callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat_message))
    
    print('🚀 @Heartwaychatbot v25.0 LIVE - NO SELF-MATCH!')
    app.run_polling()
