import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Replace with your bot's token
TOKEN = '8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA'

# Handler for /start command
async def start(update: Update, context):
    user = update.effective_user
    # Simple welcome message
    await update.message.reply_text(
        f"Hello, {user.first_name}! I'm your anonymous bot. Use /help for commands.",
        reply_markup=get_reply_keyboard()  # Attach reply keyboard buttons
    )

# Handler for /help command
async def help_command(update: Update, context):
    help_text = "Available commands:\n/start - Start the bot\n/help - Show this help\n/buttons - Show inline buttons"
    await update.message.reply_text(help_text)

# Handler for /buttons command (shows inline buttons)
async def show_buttons(update: Update, context):
    await update.message.reply_text(
        "Click a button below:",
        reply_markup=get_inline_keyboard()  # Attach inline keyboard buttons
    )

# Callback for inline button presses
async def button_callback(update: Update, context):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    if query.data == 'action1':
        await query.edit_message_text("You clicked Button 1! Performing anonymous action...")
    elif query.data == 'action2':
        await query.edit_message_text("You clicked Button 2! Another secret feature.")

# Echo handler for non-command messages (optional, for testing anonymity)
async def echo(update: Update, context):
    await update.message.reply_text("Echo: " + update.message.text)

# Function to create reply keyboard buttons (persistent at bottom)
def get_reply_keyboard():
    keyboard = [
        ['/start', '/help'],  # Row 1
        ['/buttons']          # Row 2
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# Function to create inline keyboard buttons (attached to message)
def get_inline_keyboard():
    keyboard = [
        [InlineKeyboardButton("Button 1", callback_data='action1')],
        [InlineKeyboardButton("Button 2", callback_data='action2')]
    ]
    return InlineKeyboardMarkup(keyboard)

if __name__ == '__main__':
    # Build the application
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('buttons', show_buttons))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))  # Handles non-commands

    # Start polling for updates
    application.run_polling()


