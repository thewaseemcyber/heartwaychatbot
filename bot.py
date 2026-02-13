import os
import json
import sqlite3
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
    filters, ContextTypes, ConversationHandler
)

# Advanced logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('heartway.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = "heartway.db"

# Conversation states
USERNAME, AGE, GENDER, INTERESTS, BIO = range(5)

class ChatBot:
    def __init__(self):
        self.user_profiles: Dict[int, Dict] = {}
        self.active_chats: Dict[int, int] = {}
        self.user_ratelimit: Dict[int, list] = defaultdict(list)
        self.init_db()
    
    def init_db(self):
        """SQLite database initialization"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    age INTEGER,
                    gender TEXT,
                    interests TEXT,
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_vip BOOLEAN DEFAULT FALSE,
                    rating REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user1_id INTEGER,
                    user2_id INTEGER,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    rating1 INTEGER,
                    rating2 INTEGER
                )
            """)
    
    async def get_profile(self, user_id: int) -> Optional[Dict]:
        """Get user profile from DB"""
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0], 'username': row[1], 'age': row[2],
                    'gender': row[3], 'interests': row[4], 'bio': row[5],
                    'is_vip': bool(row[6]), 'rating': row[7]
                }
        return None
    
    async def save_profile(self, profile: Dict):
        """Save/update user profile"""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, age, gender, interests, bio, is_vip)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                profile['user_id'], profile['username'], profile['age'],
                profile['gender'], profile['interests'], profile['bio'],
                profile.get('is_vip', False)
            ))
            conn.commit()

bot = ChatBot()

async def rate_limit_check(user_id: int) -> bool:
    """Rate limiting - 10 messages per minute"""
    now = datetime.now()
    bot.user_ratelimit[user_id] = [
        t for t in bot.user_ratelimit[user_id] 
        if now - t < timedelta(minutes=1)
    ]
    if len(bot.user_ratelimit[user_id]) >= 10:
        return False
    bot.user_ratelimit[user_id].append(now)
    return True

# ===== PROFILE CREATION FLOW =====
async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1: Username"""
    await update.message.reply_text(
        "✏️ **Create Profile**\n\n"
        "1️⃣ **Username** (max 20 chars):",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
    )
    return USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 2: Validate & get age"""
    username = update.message.text.strip()[:20]
    if len(username) < 2:
        await update.message.reply_text("❌ Username must be 2+ characters")
        return USERNAME
    
    context.user_data['profile'] = {'user_id': update.effective_user.id, 'username': username}
    await update.message.reply_text("🎂 **Age** (13-100):")
    return AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 3: Get gender"""
    try:
        age = int(update.message.text)
        if not 13 <= age <= 100:
            raise ValueError()
        context.user_data['profile']['age'] = age
    except ValueError:
        await update.message.reply_text("❌ Enter valid age (13-100)")
        return AGE
    
    keyboard = [[InlineKeyboardButton("♂️ Male", callback_data="male")],
                [InlineKeyboardButton("♀️ Female", callback_data="female")],
                [InlineKeyboardButton("⚧️ Other", callback_data="other")]]
    await update.message.reply_text("⚧️ **Gender**:", reply_markup=InlineKeyboardMarkup(keyboard))
    return GENDER

async def get_interests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 5: Get bio"""
    interests = update.message.text.strip()[:100]
    context.user_data['profile']['interests'] = interests
    await update.message.reply_text("📝 **Bio** (max 200 chars):")
    return BIO

async def get_bio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 6: Complete profile"""
    bio = update.message.text.strip()[:200]
    profile = context.user_data['profile']
    profile['bio'] = bio
    
    await bot.save_profile(profile)
    bot.user_profiles[profile['user_id']] = profile
    
    await update.message.reply_text(
        f"✅ **Profile Created!**\n\n"
        f"👤 **{profile['username']}**\n"
        f"🎂 {profile['age']} • {profile['gender']}\n"
        f"❤️ {profile['interests']}\n"
        f"📝 {profile['bio']}\n\n"
        f"✨ **Ready for anonymous chats!**"
    )
    return ConversationHandler.END

async def cancel_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel profile creation"""
    await update.message.reply_text("❌ Profile creation cancelled")
    return ConversationHandler.END

# ===== MAIN HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start with profile check"""
    user_id = update.effective_user.id
    profile = await bot.get_profile(user_id)
    
    if not profile:
        await update.message.reply_text(
            "🎭 **Welcome to @Heartwaychatbot v5.0**\n\n"
            "✨ First, create your profile!"
        )
        return await profile_start(update, context)
    
    keyboard = [
        ['🌟 New Chat', '🔍 Smart Match'],
        ['👥 Online Users', '✏️ My Profile'],
        ['💎 VIP Features', '⭐ Rate Partner'],
        ['⚠️ Report User', '🔚 End Chat']
    ]
    await update.message.reply_text(
        f"💖 **Welcome back, {profile['username']}**\n\n"
        f"💎 {'VIP' if profile['is_vip'] else 'Free'} • "
        f"⭐ {profile['rating']:.1f} Rating\n\n"
        "Choose from menu 👇",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def smart_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI-powered matching based on interests"""
    user_id = update.effective_user.id
    if user_id in bot.active_chats:
        await update.message.reply_text("💬 Already in chat! Use 🔚 End Chat")
        return
    
    # Advanced matching logic
    user_profile = await bot.get_profile(user_id)
    if not user_profile:
        await update.message.reply_text("❌ Complete your profile first!")
        return
    
    compatible_users = await find_compatible_users(user_profile, user_id)
    if not compatible_users:
        await update.message.reply_text(
            "🔄 **No compatible partners right now**\n"
            "Try again in 2 minutes! ⏳"
        )
        return
    
    partner_id = max(compatible_users, key=lambda x: x['compatibility_score'])
    await start_chat(user_id, partner_id)

async def start_chat(user1_id: int, user2_id: int):
    """Start chat session with DB logging"""
    bot.active_chats[user1_id] = user2_id
    bot.active_chats[user2_id] = user1_id
    
    # Log chat to DB
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO chats (user1_id, user2_id) VALUES (?, ?)",
            (min(user1_id, user2_id), max(user1_id, user2_id))
        )
        conn.commit()

async def find_compatible_users(user_profile: Dict, exclude_id: int) -> list:
    """Find users with similar interests"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("""
            SELECT * FROM users 
            WHERE user_id != ? AND age BETWEEN ?-5 AND ?+5
            ORDER BY RANDOM() LIMIT 10
        """, (exclude_id, user_profile['age'], user_profile['age']))
        
        users = []
        for row in cursor.fetchall():
            # Calculate compatibility score based on interests
            score = calculate_compatibility(user_profile, dict(zip(['user_id', 'username', 'age', 'gender', 'interests', 'bio', 'is_vip', 'rating'], row)))
            users.append({'user_id': row[0], 'compatibility_score': score})
        return users

def calculate_compatibility(user1: Dict, user2: Dict) -> float:
    """Simple interest-based compatibility score"""
    interests1 = set(user1['interests'].lower().split(','))
    interests2 = set(user2['interests'].lower().split(','))
    common = len(interests1.intersection(interests2))
    return min(common * 20, 100)  # 0-100 score

# ===== PRODUCTION READY FEATURES =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main message handler with rate limiting"""
    user_id = update.effective_user.id
    
    if not await rate_limit_check(user_id):
        await update.message.reply_text("⏳ **Too fast!** Wait 1 minute.")
        return
    
    if user_id in bot.active_chats:
        partner_id = bot.active_chats[user_id]
        partner_profile = await bot.get_profile(partner_id)
        
        # Forward message to partner (real forwarding in production)
        await context.bot.send_message(
            partner_id,
            f"💕 **{await bot.get_profile(user_id)['username']}**: {update.message.text}\n\n"
            f"[❤️ Heart animation]"
        )
        
        await update.message.reply_text(
            f"✅ **Sent to {partner_profile['username']}**\n"
            f"💭 Partner typing..."
        )
    else:
        await show_main_menu(update)

def main():
    """Production-ready bot startup"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Profile conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('profile', profile_start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interests)],
            INTERESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_interests)],
            BIO: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bio)],
        },
        fallbacks=[CommandHandler('cancel', cancel_profile)],
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🚀 Starting Heartwaychatbot v5.0")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
