import os
from telegram import LabeledPrice  # Add this import

PROVIDER_TOKEN = os.getenv('PAYMENT_PROVIDER_TOKEN')  # From Railway env

# Your existing get_user_data() unchanged, but premium now unlocks features

# Credit command (exact your screenshot)
async def credit(update: Update, context):
    user_id = update.effective_user.id
    update_last_active(user_id)
    credits, _, _, _, _, ref_code, _ = get_user_data(user_id)
    text = f"""💎 Your current Credit: {credits}

❓ How can I get Credit?

1️⃣ Invite friends (Free)
Share your personal invite link ⚡ (/link) with friends and earn 50 Credit for each referral.

2️⃣ Buy Credit
Choose one of the plans below 👇"""
    keyboard = [
        [InlineKeyboardButton("💎 280 Credits → ⭐ 100", callback_data='buy_280')],
        [InlineKeyboardButton("💎 500 Credits → ⭐ 151", callback_data='buy_500')],
        [InlineKeyboardButton("💎 1300 Credits → ⭐ 222", callback_data='buy_1300')],
        [InlineKeyboardButton("💎 2500 Credits → ⭐ 318", callback_data='buy_2500')],
        [InlineKeyboardButton("💎 6200 Credits VIP 🎉 → ⭐ 740", callback_data='buy_6200')]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# Buy callback - FULL PAYMENTS
async def buy_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    plan = query.data.split('_')[1]
    
    plans = {
        '280': {'title': '280 Credits', 'desc': 'Basic plan', 'credits': 280, 'price': 100, 'payload': f'{user_id}_280'},
        '500': {'title': '500 Credits', 'desc': 'Popular', 'credits': 500, 'price': 151, 'payload': f'{user_id}_500'},
        '1300': {'title': '1300 Credits', 'desc': 'Pro', 'credits': 1300, 'price': 222, 'payload': f'{user_id}_1300'},
        '2500': {'title': '2500 Credits', 'desc': 'Elite', 'credits': 2500, 'price': 318, 'payload': f'{user_id}_2500'},
        '6200': {'title': '6200 Credits VIP 🎉', 'desc': 'VIP: Unlimited + priority', 'credits': 6200, 'price': 740, 'payload': f'{user_id}_vip', 'is_vip': True}
    }
    
    if plan not in plans:
        await query.edit_message_text("Invalid plan.")
        return
    
    p = plans[plan]
    prices = [LabeledPrice(p['title'], p['price'] * 100)]  # Paise/rupees
    
    await context.bot.send_invoice(
        chat_id=user_id,
        title=p['title'],
        description=p['desc'],
        payload=p['payload'],
        provider_token=PROVIDER_TOKEN,
        currency='INR',  # Change to USD if needed
        prices=prices,
        start_parameter=f"buy_{plan}"
    )
    await query.edit_message_text("Payment sent! Complete to get credits/VIP.")

# Pre-checkout (validate)
async def precheckout_callback(update: Update, context):
    query = update.pre_checkout_query
    if not query.invoice_payload.startswith(str(query.from_user.id)):
        await query.answer(ok=False, error_message="Wrong user.")
    else:
        await query.answer(ok=True)

# Successful payment - give credits + VIP
async def successful_payment_callback(update: Update, context):
    user_id = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    _, plan = payload.split('_')
    
    plans = {'280': 280, '500': 500, '1300': 1300, '2500': 2500, 'vip': 6200}
    credits_add = plans.get(plan, 0)
    
    # Add credits
    cursor.execute('UPDATE users SET credits = credits + ? WHERE user_id = ?', (credits_add, user_id))
    if plan == 'vip':
        cursor.execute('UPDATE users SET is_premium = TRUE WHERE user_id = ?', (user_id,))
        cursor.execute('UPDATE users SET gender_choices_used = 0 WHERE user_id = ?', (user_id,))  # Reset
    
    conn.commit()
    
    msg = f"✅ Paid! +{credits_add} credits"
    if plan == 'vip': msg += "\n🎉 VIP activated (unlimited choices + DMs)!"
    await update.message.reply_text(msg, reply_markup=get_main_menu())

# Update your chat_option_callback to check premium properly (already there)
# In try_match_all, add VIP priority: premium users first in queues

# Add these handlers to your main:
# application.add_handler(CallbackQueryHandler(buy_callback, pattern='^buy_'))
# application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
# application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

