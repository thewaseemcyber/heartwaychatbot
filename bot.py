import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import os

# Replace with your bot token from @BotFather
TOKEN = "8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA"
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Enable logging
logging.basicConfig(level=logging.INFO)

# Main menu reply keyboard (persistent buttons at bottom)
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Stats"), KeyboardButton(text="🆘 Help")],
        [KeyboardButton(text="🔄 Reset")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Inline keyboard example (buttons under a message)
def get_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👍 Like", callback_data="like")],
        [InlineKeyboardButton(text="👎 Dislike", callback_data="dislike")],
        [InlineKeyboardButton(text="🔗 More Info", url="https://core.telegram.org/bots")]
    ])

# Command: /start - Shows welcome with main menu
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Welcome to Anonymous Bot!\n\nUse buttons below or type /help for commands.",
        reply_markup=main_keyboard
    )

# Command: /help - Lists all commands
@dp.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
Available Commands:
/start - Main menu
/help - This help
/stats - Bot stats
/quiz - Quick quiz with buttons

Use bottom buttons for quick actions!
    """
    await message.answer(help_text)

# Command: /stats - Simple stats (anonymous, no DB needed)
@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    await message.answer(
        "📊 Stats:\nUsers: 42\nMessages: 1,234\nUptime: 99.9%",
        reply_markup=get_inline_keyboard()
    )

# Command: /quiz - Inline buttons example
@dp.message(Command("quiz"))
async def cmd_quiz(message: Message):
    await message.answer(
        "❓ Quiz: What is 2+2?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="3", callback_data="wrong1")],
            [InlineKeyboardButton(text="4", callback_data="correct")],
            [InlineKeyboardButton(text="5", callback_data="wrong2")]
        ])
    )

# Handle reply keyboard button clicks (text buttons)
@dp.message(F.text.in_(["📊 Stats", "🆘 Help", "🔄 Reset"]))
async def handle_menu_buttons(message: Message):
    if message.text == "📊 Stats":
        await cmd_stats(message)
    elif message.text == "🆘 Help":
        await cmd_help(message)
    elif message.text == "🔄 Reset":
        await message.answer("🔄 Reset complete!", reply_markup=main_keyboard)

# Handle inline button callbacks (no new message spam)
@dp.callback_query()
async def handle_callback(callback: CallbackQuery):
    if callback.data == "correct":
        await callback.message.edit_text("✅ Correct! 2+2=4", reply_markup=None)
    elif callback.data in ["wrong1", "wrong2", "like", "dislike"]:
        action = "👍" if callback.data == "like" else "👎"
        await callback.answer(f"{action} Thanks for feedback!", show_alert=True)
    await callback.answer()  # Acknowledge callback

# Run the bot
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())




