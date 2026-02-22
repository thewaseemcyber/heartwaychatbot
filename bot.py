# Add to DB tables
cursor.execute('''
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        photo_file_id TEXT,
        name TEXT NOT NULL,
        age INTEGER,
        gender TEXT,  -- 'boy'/'girl'
        city TEXT,
        bio TEXT,
        gps_enabled BOOLEAN DEFAULT FALSE,
        filter_age_min INTEGER DEFAULT 13,
        filter_age_max INTEGER DEFAULT 100,
        filter_gender TEXT DEFAULT 'any'  -- 'any'/'boy'/'girl'
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS likes (
        user_id INTEGER,
        liked_user_id INTEGER,
        PRIMARY KEY (user_id, liked_user_id)
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS blocked (
        user_id INTEGER,
        blocked_user_id INTEGER,
        PRIMARY KEY (user_id, blocked_user_id)
    )
''')
conn.commit()

# Profile states (extended)
PHOTO, NAME, AGE, GENDER, CITY, BIO, FILTERS = range(7)

# Save full profile
def save_full_profile(user_id, **kwargs):
    cursor.execute('''
        INSERT OR REPLACE INTO profiles (user_id, photo_file_id, name, age, gender, city, bio, 
        gps_enabled, filter_age_min, filter_age_max, filter_gender) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, kwargs.get('photo'), kwargs.get('name'), kwargs.get('age'), kwargs.get('gender'),
          kwargs.get('city'), kwargs.get('bio'), kwargs.get('gps', False),
          kwargs.get('min_age', 13), kwargs.get('max_age', 100), kwargs.get('filter_gender', 'any')))
    cursor.execute('UPDATE users SET has_profile = TRUE WHERE user_id = ?', (user_id,))
    conn.commit()

def get_full_profile(user_id):
    cursor.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

async def show_profile(update: Update, context):
    user_id = update.effective_user.id
    profile = get_full_profile(user_id)
    if not profile:
        await update.message.reply_text("Create profile: /profile")
        return
    
    photo_id, name, age, gender, city, bio, gps = profile[1:8]
    display = f"""👤 {name}
⚥ {'Boy' if gender=='boy' else 'Girl'}
📍 {city}
🕐 Age: {age}

📝 {bio or 'No bio'}

{'📍 My GPS: Like' if gps else '📍 My GPS: Inactive'}
"""
    
    keyboard = [
        [InlineKeyboardButton("✏️ Edit Profile", callback_data='edit_profile')],
        [InlineKeyboardButton("📍 Edit GPS", callback_data='toggle_gps')],
        [InlineKeyboardButton("👥 Liked Users", callback_data='liked_list'), InlineKeyboardButton("🚫 Blocked Users", callback_data='blocked_list')],
        [InlineKeyboardButton("⚙️ Advanced Settings", callback_data='filters')]
    ]
    if get_user_data(user_id)[1]:  # Premium
        keyboard.append([InlineKeyboardButton("💬 Contact Users", callback_data='contact_list')])
    
    if photo_id:
        await context.bot.send_photo(user_id, photo_id, caption=display, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(display, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Profile callbacks
async def profile_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == 'edit_profile':
        await query.edit_message_text("Edit profile: Send new photo or /profile")
        return
    elif query.data == 'toggle_gps':
        cursor.execute('UPDATE profiles SET gps_enabled = NOT gps_enabled WHERE user_id = ?', (user_id,))
        conn.commit()
        await show_profile(query, context)
        return
    elif query.data == 'liked_list':
        cursor.execute('SELECT liked_user_id FROM likes WHERE user_id = ?', (user_id,))
        likes = [get_display_name(uid[0]) for uid in cursor.fetchall()]
        text = f"👍 Liked ({len(likes)}):\n" + '\n'.join(likes[:10]) if likes else "No likes"
    elif query.data == 'blocked_list':
        cursor.execute('SELECT blocked_user_id FROM blocked WHERE user_id = ?', (user_id,))
        blocked = [get_display_name(uid[0]) for uid in cursor.fetchall()]
        text = f"🚫 Blocked ({len(blocked)}):\n" + '\n'.join(blocked[:10]) if blocked else "No blocks"
    elif query.data == 'contact_list' and get_user_data(user_id)[1]:
        text = "💬 Premium: DM any user (/dm @name)"
    elif query.data == 'filters':
        profile = get_full_profile(user_id)
        text = f"⚙️ Filters:\nMin age: {profile[8]}, Max: {profile[9]}\nGender: {profile[10]}\n\nEdit: /setfilter min max gender"
    
    await query.edit_message_text(text, parse_mode='Markdown')

# Enhanced profile creation (add city + filters)
async def profile_city(update: Update, context):
    context.user_data['profile_city'] = update.message.text.strip()
    await update.message.reply_text("Bio?")
    return BIO

async def profile_bio(update: Update, context):  # Updated
    context.user_data['profile_bio'] = update.message.text.strip()
    await update.message.reply_text("Filters?\nSend: min_age max_age gender\n(e.g., '18 30 girl' or 'any')\nOr 'skip'")
    return FILTERS

async def profile_filters(update: Update, context):
    user_id = update.effective_user.id
    data = context.user_data
    try:
        parts = update.message.text.split()
        min_age, max_age, fgender = 13, 100, 'any'
        if parts[0] != 'skip':
            min_age, max_age = int(parts[0]), int(parts[1])
            fgender = parts[2] if len(parts) > 2 else 'any'
        save_full_profile(user_id, **data, min_age=min_age, max_age=max_age, filter_gender=fgender)
    except:
        save_full_profile(user_id, **data)  # Default filters
    
    await update.message.reply_text("✅ Profile created!", reply_markup=get_main_menu())
    context.user_data.clear()
    return ConversationHandler.END

# Filter matching (in try_match_all, before matching)
def matches_filter(user_id, potential_partner_id):
    profile_u = get_full_profile(user_id)
    profile_p = get_full_profile(potential_partner_id)
    if not profile_u or not profile_p: return False
    p_age, p_gender = profile_p[3], profile_p[4]
    return (profile_u[8] <= p_age <= profile_u[9] and 
            (profile_u[10] == 'any' or profile_u[10] == p_gender))

# Update try_match_all:
# Before partner_id = opposite_queue[0]
# if not matches_filter(user_id, partner_id): continue  # Skip non-matching

# New commands
async def setfilter(update: Update, context):
    # /setfilter 18 30 girl
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /setfilter min max [boy/girl/any]")
        return
    try:
        min_age, max_age = int(context.args[0]), int(context.args[1])
        fgender = context.args[2] if len(context.args) > 2 else 'any'
        cursor.execute('UPDATE profiles SET filter_age_min=?, filter_age_max=?, filter_gender=? WHERE user_id=?',
                      (min_age, max_age, fgender, update.effective_user.id))
        conn.commit()
        await update.message.reply_text(f"✅ Filters: {min_age}-{max_age} {fgender}")
    except:
        await update.message.reply_text("Invalid: /setfilter 18 30 girl")

# Like/Block in chat (add to get_chat_menu)
def get_chat_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👍 Like", callback_data='like'), InlineKeyboardButton("🚫 Block", callback_data='block')],
        [InlineKeyboardButton("⚠️ Report", callback_data='report'), InlineKeyboardButton("/stop", callback_data='stop')]
    ])

# Chat callbacks with like/block
async def chat_callback(update: Update, context):
    # ... existing ...
    if query.data == 'like':
        partner_id = user_states[query.from_user.id]['partner_id']
        cursor.execute('INSERT OR IGNORE INTO likes (user_id, liked_user_id) VALUES (?, ?)', 
                      (query.from_user.id, partner_id))
        conn.commit()
        await query.answer("👍 Liked!")
    elif query.data == 'block':
        partner_id = user_states[query.from_user.id]['partner_id']
        cursor.execute('INSERT OR IGNORE INTO blocked (user_id, blocked_user_id) VALUES (?, ?)', 
                      (query.from_user.id, partner_id))
        conn.commit()
        await stop(query, context)
        await query.answer("🚫 Blocked!")

# Update handlers
application.add_handler(CommandHandler('setfilter', setfilter))
application.add_handler(CallbackQueryHandler(profile_callback, pattern='^(edit_profile|toggle_gps|liked_list|blocked_list|contact_list|filters)$'))
# Update profile conv_handler states to include CITY, BIO→FILTERS
# In profile_gender → profile_city (chain)



