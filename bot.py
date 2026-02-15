
# anon_heartway_bot.py
# Requirements: python-telegram-bot==20.7, aiosqlite
# Usage: python anon_heartway_bot.py

import asyncio
import aiosqlite
import re
import time
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ========== CONFIG ==========
BOT_TOKEN =("8530545620:AAFvx6jwfKJ5Q5avQyFwpXVze9-M29087cA").build()

DB_PATH = "heartway.db"
ADMIN_IDS = {123456789}   # <- replace with your Telegram user id(s)
REPORTS_TO_AUTO_BAN = 3
STRIKES_TO_AUTO_BAN = 3
MESSAGE_RATE_SECONDS = 1.0  # minimal seconds between messages per user
BAD_WORDS = {"badword1","badword2"}  # fill with lowercase words to block
# ============================

# in-memory rate limiter
last_message_time = {}
# a lock for queue / matching operations to avoid race conditions
queue_lock = asyncio.Lock()

# ---------- Utilities ----------
def normalize_text(text: str) -> str:
    return re.sub(r"\W+", " ", (text or "").lower()).strip()

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                gender TEXT DEFAULT NULL,
                pref TEXT DEFAULT 'any',
                vip INTEGER DEFAULT 0,
                banned INTEGER DEFAULT 0,
                strikes INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS waiting (
                user_id INTEGER PRIMARY KEY,
                joined_at INTEGER,
                vip INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS active_chats (
                user_id INTEGER PRIMARY KEY,
                partner_id INTEGER
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reporter INTEGER,
                reported INTEGER,
                reason TEXT,
                ts INTEGER
            )
        """)
        await db.commit()

# ---------- DB helpers ----------
async def ensure_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            await db.execute("INSERT INTO users(user_id) VALUES (?)", (user_id,))
            await db.commit()

async def set_user_field(user_id: int, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id, gender, pref, vip, banned, strikes FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row  # tuple or None

async def is_banned(user_id: int):
    u = await get_user(user_id)
    return u and u[4] == 1

# ---------- Queue / matching ----------
async def add_to_waiting(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # check not already in waiting or active
        cur = await db.execute("SELECT user_id FROM waiting WHERE user_id = ?", (user_id,))
        if await cur.fetchone():
            return
        cur = await db.execute("SELECT user_id FROM active_chats WHERE user_id = ?", (user_id,))
        if await cur.fetchone():
            return
        # vip status
        cur = await db.execute("SELECT vip FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        vip = int(row[0]) if row else 0
        await db.execute("INSERT OR REPLACE INTO waiting(user_id, joined_at, vip) VALUES (?, ?, ?)",
                         (user_id, int(time.time()), vip))
        await db.commit()

async def remove_from_waiting(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM waiting WHERE user_id = ?", (user_id,))
        await db.commit()

async def set_active_chat(a:int, b:int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO active_chats(user_id, partner_id) VALUES (?, ?)", (a,b))
        await db.execute("INSERT OR REPLACE INTO active_chats(user_id, partner_id) VALUES (?, ?)", (b,a))
        await db.commit()

async def clear_active_chat(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT partner_id FROM active_chats WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row:
            partner = row[0]
            await db.execute("DELETE FROM active_chats WHERE user_id IN (?, ?)", (user_id, partner))
            await db.commit()
            return partner
    return None

async def get_partner(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT partner_id FROM active_chats WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return row[0] if row else None

async def find_match_for(user_id: int):
    """Find a partner from waiting queue respecting prefs & vip priority"""
    async with aiosqlite.connect(DB_PATH) as db:
        # get user's prefs
        cur = await db.execute("SELECT gender, pref, vip FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if not row:
            return None
        gender, pref, vip = row
        # query waiting users ordered by vip desc, joined_at asc
        cur = await db.execute("SELECT user_id FROM waiting ORDER BY vip DESC, joined_at ASC")
        rows = await cur.fetchall()
        for (cand_id,) in rows:
            if cand_id == user_id:
                continue
            # skip banned / already active
            cur2 = await db.execute("SELECT banned, gender, pref FROM users WHERE user_id = ?", (cand_id,))
            crow = await cur2.fetchone()
            if not crow:
                continue
            banned, c_gender, c_pref = crow
            if banned == 1:
                continue
            # check mutual preferences
            ok_for_user = (pref == 'any') or (c_gender == pref)
            ok_for_cand = (c_pref == 'any') or (c_gender is None) or (c_pref == gender)
            # note: if candidate's gender is None we treat carefully — skip if ambiguous
            if ok_for_user and ok_for_cand:
                return cand_id
    return None

# ---------- Moderation ----------
async def add_report(reporter:int, reported:int, reason:str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO reports(reporter, reported, reason, ts) VALUES (?, ?, ?, ?)",
                         (reporter, reported, reason or "", int(time.time())))
        # increment strikes
        cur = await db.execute("SELECT strikes FROM users WHERE user_id = ?", (reported,))
        r = await cur.fetchone()
        strikes = r[0] + 1 if r else 1
        await db.execute("UPDATE users SET strikes = ? WHERE user_id = ?", (strikes, reported))
        # auto-ban if exceeds
        if strikes >= STRIKES_TO_AUTO_BAN:
            await db.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (reported,))
        await db.commit()
        return strikes

# ---------- Handlers ----------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await ensure_user(user_id)
    await update.message.reply_text(
        "Welcome to Heartway Chat.\n"
        "Set gender with /setgender male|female|other\n"
        "Set preference with /setpref male|female|any\n"
        "Use /search to find a partner. Use /end to end chat."
    )

async def cmd_setgender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /setgender male|female|other")
        return
    g = context.args[0].lower()
    if g not in ("male","female","other"):
        await update.message.reply_text("Choose male, female, or other.")
        return
    await ensure_user(user_id)
    await set_user_field(user_id, "gender", g)
    await update.message.reply_text(f"Your gender set to {g}.")

async def cmd_setpref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /setpref male|female|any")
        return
    p = context.args[0].lower()
    if p not in ("male","female","any"):
        await update.message.reply_text("Choose male, female or any.")
        return
    await ensure_user(user_id)
    await set_user_field(user_id, "pref", p)
    await update.message.reply_text(f"Your preference set to {p}.")

async def cmd_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # placeholder: manual or payment flow. For now show instruction
    await update.message.reply_text("VIP gives priority matching. To become VIP, contact admin or use /buyvip (not implemented).")

async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await ensure_user(user_id)
    if await is_banned(user_id):
        await update.message.reply_text("You are banned from this service.")
        return
    # check if already in chat
    partner = await get_partner(user_id)
    if partner:
        await update.message.reply_text("You are already in a chat. Use /end to leave or /next to find someone else.")
        return
    async with queue_lock:
        # add to waiting
        await add_to_waiting(user_id)
        await update.message.reply_text("Searching for partner... (VIP users prioritized)")
        # try to find match
        partner_id = await find_match_for(user_id)
        if partner_id:
            # make them active
            await set_active_chat(user_id, partner_id)
            # remove both from waiting
            await remove_from_waiting(user_id)
            await remove_from_waiting(partner_id)
            await context.bot.send_message(chat_id=partner_id, text="Partner found! Say hi 👋")
            await context.bot.send_message(chat_id=user_id, text="Partner found! Say hi 👋")

async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner = await clear_active_chat(user_id)
    if partner:
        await context.bot.send_message(chat_id=partner, text="Partner left the chat.")
        await update.message.reply_text("Chat ended.")
    else:
        # if in waiting, remove
        await remove_from_waiting(user_id)
        await update.message.reply_text("You were not in a chat (or removed from queue).")

async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner = await clear_active_chat(user_id)
    if partner:
        await context.bot.send_message(chat_id=partner, text="Partner skipped you.")
    # start searching again
    await cmd_search(update, context)

async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    partner = await get_partner(user_id)
    if not partner:
        await update.message.reply_text("You are not in a chat.")
        return
    reason = " ".join(context.args) if context.args else ""
    strikes = await add_report(user_id, partner, reason)
    await update.message.reply_text(f"Report received. Partner now has {strikes} strike(s).")
    if strikes >= STRIKES_TO_AUTO_BAN:
        await context.bot.send_message(chat_id=partner, text="You have been auto-banned due to reports.")

# Admin commands
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id>")
        return
    target = int(context.args[0])
    await set_user_field(target, "banned", 1)
    await update.message.reply_text(f"Banned {target}.")

async def cmd_unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /unban <user_id>")
        return
    target = int(context.args[0])
    await set_user_field(target, "banned", 0)
    await update.message.reply_text(f"Unbanned {target}.")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in ADMIN_IDS:
        await update.message.reply_text("Admin only.")
        return
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM waiting")
        waiting = (await cur.fetchone())[0]
        cur = await db.execute("SELECT COUNT(*) FROM active_chats")
        active = (await cur.fetchone())[0] // 2
        await update.message.reply_text(f"Users: {total}\nWaiting: {waiting}\nActive pairs: {active}")

# message handler (text & media)
async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    uid = update.effective_user.id
    # rate limit
    now = time.time()
    last = last_message_time.get(uid, 0)
    if now - last < MESSAGE_RATE_SECONDS:
        await update.message.reply_text("You're sending messages too fast. Slow down.")
        return
    last_message_time[uid] = now

    # check ban
    if await is_banned(uid):
        await update.message.reply_text("You are banned.")
        return

    partner = await get_partner(uid)
    # check for bad words only when not in chat? or always
    text = (msg.text or msg.caption or "")
    norm = normalize_text(text)
    for bad in BAD_WORDS:
        if bad in norm:
            await set_user_field(uid, "strikes", (await get_user(uid))[5] + 1 if await get_user(uid) else 1)
            await update.message.reply_text("Your message contained disallowed words. You received a strike.")
            # if exceeds, ban
            u = await get_user(uid)
            strikes = u[5] if u else 1
            if strikes >= STRIKES_TO_AUTO_BAN:
                await set_user_field(uid, "banned", 1)
                await update.message.reply_text("You have been banned due to repeated violations.")
            return

    if not partner:
        await update.message.reply_text("No partner. Use /search to find someone.")
        return

    # Forward media or text using copy_message for preserving metadata
    try:
        # copy_message works for many message types
        await context.bot.copy_message(chat_id=partner, from_chat_id=uid, message_id=msg.message_id)
    except Exception as e:
        # fallback: send text only
        if text:
            await context.bot.send_message(chat_id=partner, text=text)
        else:
            await update.message.reply_text("Couldn't forward this message type.")

# startup
async def on_startup(app):
    await init_db()
    print("DB initialized and bot starting...")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("setgender", cmd_setgender))
    app.add_handler(CommandHandler("setpref", cmd_setpref))
    app.add_handler(CommandHandler("vip", cmd_vip))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("end", cmd_end))
    app.add_handler(CommandHandler("next", cmd_next))
    app.add_handler(CommandHandler("report", cmd_report))
    # admin
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("unban", cmd_unban))
    app.add_handler(CommandHandler("stats", cmd_stats))

    # messages (all non-command)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, forward_message))

    app.post_init(on_startup)
    app.run_polling()

if __name__ == "__main__":
    main()



