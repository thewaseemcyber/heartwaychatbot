from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conversation states
CREATE_PROFILE, ENTER_NAME, ENTER_GENDER, ENTER_AGE, ENTER_CITY = range(5)

# Global storage (like v7.2 memory system)
profiles = {}  # {user_id: {"name": "Mir", "gender": "boy", "age": 24, "city": "Srinagar"}}
waiting_users = {"boys": [], "girls": []}

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ My Profile", callback_data="profile")],
        [InlineKeyboardButton("🌟 New Chat", callback_data="new_chat")],
        [InlineKeyboardButton("💎 VIP", callback_data="vip")],
        [InlineKeyboardButton("◀️ Cancel", callback_data="cancel")]
    ])

# ===== CONVERSATION HANDLER =====
async def start_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for profile creation"""
    await update.message.reply_text(
        "✏️ *Create Your Profile*\n\n"
        "👤 Enter your **name**:\n*Example: Mir*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
    )
    return ENTER_NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store name and ask for gender"""
    context.user_data['name'] = update.message.text.strip()
    await update.message.reply_text(
        "🔸 Enter your **gender**:\n*boy / girl*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
    )
    return ENTER_GENDER

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store gender and ask for age"""
    gender = update.message.text.strip().lower()
    if gender not in ['boy', 'girl']:
        await update.message.reply_text("❌ Please send *boy* or *girl*", parse_mode='Markdown')
        return ENTER_GENDER
    
    context.user_data['gender'] = gender
    await update.message.reply_text(
        "📅 Enter your **age**:\n*Example: 24*",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
    )
    return ENTER_AGE

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store age and ask for city"""
    try:
        age = int(update.message.text.strip())
        if age < 13 or age > 100:
            await update.message.reply_text("❌ Age must be 13-100", parse_mode='Markdown')
            return ENTER_AGE
        context.user_data['age'] = age
        
        await update.message.reply_text(
            "📍 Enter your **city**:\n*Example: Srinagar*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])
        )
        return ENTER_CITY
    except ValueError:
        await update.message.reply_text("❌ Please send a valid number", parse_mode='Markdown')
        return ENTER_AGE

async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save complete profile"""
    user_id = update.message.from_user.id
    city = update.message.text.strip()
    
    # Save complete profile
    profiles[user_id] = {
        'name': context.user_data['name'],
        'gender': context.user_data['gender'],
        'age': context.user_data['age'],
        'city': city
    }
    
    profile = profiles[user_id]
    await update.message.reply_text(
        f"✅ *Profile Created Successfully!*\n\n"
        f"👤 *{profile['name']}*\n"
        f"🔸 *{profile['gender'].title()}*\n"
        f"📅 *{profile['age']} years*\n"
        f"📍 *{profile['city']}*\n\n"
        f"✨ *Ready for real matching!* 🌟",
        parse_mode='Markdown',
        reply_markup=main_menu()
    )
    
    # Clear user data
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    query = update.callback_query
    await query.answer("Cancelled")
    await query.edit_message_text(
        "💕 *Heartway Chat*\n\nChoose an option:",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )
    context.user_data.clear()
    return ConversationHandler.END

# ===== MAIN BOT FEATURES =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💕 *Welcome to Heartway Chat v8.0* 😍\n\n"
        "✨ Srinagar's #1 anonymous chat app!\n"
        "• Create profile → Find matches → Chat instantly!",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if user_id in profiles:
        profile = profiles[user_id]
        await query.edit_message_text(
            f"✅ *Your Profile:*\n\n"
            f"👤 *{profile['name']}*\n🔸 *{profile['gender'].title()}*\n"
            f"📅 *{profile['age']}*\n📍 *{profile['city']}*\n\n"
            f"✨ *Ready for matching!*",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Edit Profile", callback_data="createprofile")],
                [InlineKeyboardButton("◀️ Main Menu", callback_data="main")]
            ]),
            parse_mode='Markdown'
        )
    else:
        await query.edit_message_text(
            "❌ No profile found!\n\n"
            "Tap 'Create Profile' to get started ✨",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✏️ Create Profile", callback_data="createprofile")],
                [InlineKeyboardButton("◀️ Main Menu", callback_data="main")]
            ]),
            parse_mode='Markdown'
        )

async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💕 *Heartway Chat*",
        reply_markup=main_menu(),
        parse_mode='Markdown'
    )

# ===== MAIN APPLICATION =====
def main():
    # Create application
    application = Application.builder().token("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()
    
    # Conversation handler for profile creation
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('createprofile', start_profile),
            CallbackQueryHandler(start_profile, pattern="^createprofile$")
        ],
        states={
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ENTER_GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            ENTER_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            ENTER_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern="^cancel$")],
        allow_reentry=True
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(show_profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^main$"))
    
    print("🚀 @Heartwaychatbot v8.0 LIVE - ConversationHandler!")
    application.run_polling()

if __name__ == '__main__':
    main()
