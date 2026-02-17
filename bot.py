

import logging
import sqlite3
import asyncio
from pyrogram import Client
from pyrogram.raw.functions.messages import StartBot
from pyrogram.raw.functions.channels import CreateChannel
from pyrogram.raw.types import InputPeerChannel
from pytgcalls import PyTgCalls, StreamType
from pytgcalls.types import AudioVideoPiped
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)




TOKEN = '8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA'
API_ID = your_api_id  # From my.telegram.org
API_HASH = 'your_api_hash'
SESSION_NAME = 'userbot_session'  # From generate_session.py

# Userbot setup
userbot = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)
tgcalls = PyTgCalls(userbot)

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

# In-memory storage
user_states = {}  # {user_id: {'state': 'idle'|'waiting'|'matched', 'partner_id': None, 'preference': 'girls'|'boys', 'group_id': None}}
waiting_queues = {'girls': [], 'boys': []}

# ... (keep all previous functions: init_user, get_user_data, increment_call_count, can_make_call, start, find_partner, preference_callback, try_match, handle_message, stop, rating_callback, report_callback, get_main_menu, get_preference_menu, get_chat_menu, get_rating_menu, get_call_options_menu)

# Updated call_option_callback to use userbot for calls
async def call_option_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    call_type = query.data  # 'video' or 'audio'
    partner_id = user_states[user_id]['partner_id']
    
    if can_make_call(user_id, call_type):
        increment_call_count(user_id, call_type)
        
        # Create temporary supergroup via userbot
        group = await userbot.invoke(CreateChannel(title='Anonymous Call', about='Temporary call group'))
        group_id = group.chats[0].id
        
        # Add both users to group (anonymity note: usernames visible)
        await userbot.add_chat_members(group_id, [user_id, partner_id])
        
        # Export invite link (for users to join if needed)
        invite_link = await userbot.export_chat_invite_link(group_id)
        
        # Start group call
        await tgcalls.join_group_call(
            group_id,
            AudioVideoPiped('silent_audio.mp3' if call_type == 'audio' else 'silent_video.mp4'),  # Placeholder stream; replace with actual if needed
            stream_type=StreamType().local_stream,
            enable_video=(call_type == 'video')
        )
        
        user_states[user_id]['group_id'] = group_id
        user_states[partner_id]['group_id'] = group_id
        
        # Notify both
        msg = f"{call_type.capitalize()} call started! Join the voice chat in the group: {invite_link}\n(Note: Usernames may be visible for anonymity reasons.)"
        await context.bot.send_message(user_id, msg)
        await context.bot.send_message(partner_id, msg)
    else:
        await query.edit_message_text("You've reached your free limit. Upgrade to premium for more calls.")

if __name__ == '__main__':
    # Start userbot and tgcalls
    asyncio.get_event_loop().run_until_complete(userbot.start())
    asyncio.get_event_loop().run_until_complete(tgcalls.start())
    
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers (same as before)
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
