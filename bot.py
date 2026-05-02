from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)
import sqlite3
import os

# ================= DATABASE =================
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    category TEXT,
    has_cards TEXT,
    want_cards TEXT,
    exchange_code TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ratings (
    user_id INTEGER,
    total_rating INTEGER,
    rating_count INTEGER
)
""")

conn.commit()

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
PAGE_SIZE = 5

CARDS = {
    "gold": [
        "Evacuation Master", "Melody Strongest Team", "Raging Rush Strongest Team",
        "Jujutsu Kaisen", "Ryumen Sukuna", "Suguru Geto",
        "Elite Collector", "Jester of Fate", "Ancient Secret: Arise"
    ],
    "silver": [
        "Music Hall", "Racing Hall", "Dynamic Slide Rail",
        "Parachute Challenge", "Racing Challenge", "S-Rank Vault",
        "Satoru Gojo", "Yuji Itadori", "Megumi Fushiguro",
        "Nue", "Nobara Kugisaki", "Battleground Pillar",
        "Golden Age", "Arcade Time", "Rhythm Hero", "Vibrant World",
        "Dinoground", "Ocean Odyssey", "Golden Dynasty", "Temporal Vault",
        "Ray", "Your Old Friend", "Fool Juggling", "Sacred Fire Trial",
        "Scorpian Crate", "Ancient Secret Battle"
    ],
    "grey": [
        "A-Rank Vault", "B-Rank Vault", "Special Lucky Spin",
        "Energy Shield", "Spatial Distortion Zone 1", "Spatial Distortion Zone 2",
        "Floating Thrusters", "Cathy", "Cursed Corpse Bear",
        "Inverted Spear of Heaven", "Garand", "Tracked Amphicarrier"
    ]
}

# ================= HELPERS =================
def build_keyboard(cards, prefix, page, selected):
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    sliced = cards[start:end]

    keyboard = []

    for card in sliced:
        mark = "✅ " if card in selected else ""
        keyboard.append([InlineKeyboardButton(mark + card, callback_data=f"{prefix}_{card}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"page_{prefix}_{page-1}"))
    if end < len(cards):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"page_{prefix}_{page+1}"))

    if nav:
        keyboard.append(nav)

    keyboard.append([InlineKeyboardButton("✅ Done", callback_data=f"done_{prefix}")])
    return keyboard

def get_rating_text(user_id):
    cursor.execute("SELECT total_rating, rating_count FROM ratings WHERE user_id=?", (user_id,))
    row = cursor.fetchone()

    if row:
        avg = row[0] / row[1]
        return f"\n⭐ Rating: {avg:.1f} ({row[1]} reviews)"
    return "\n⭐ No ratings yet"

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟡 Golden Cards", callback_data="category_gold")],
        [InlineKeyboardButton("⚪ Silver Cards", callback_data="category_silver")],
        [InlineKeyboardButton("⚫ Grey Cards", callback_data="category_grey")]
    ]

    await update.message.reply_text(
        "Welcome! Choose a category:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= CATEGORY =================
async def handle_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category = query.data.split("_")[1]

    context.user_data["category"] = category
    context.user_data["has_cards"] = []
    context.user_data["page"] = 0

    keyboard = build_keyboard(CARDS[category], "have", 0, [])

    await query.edit_message_text(
        "Select cards you HAVE:\n\nSelected: None",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= HAVE =================
async def handle_have(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card = query.data.replace("have_", "")
    selected = context.user_data["has_cards"]

    if card in selected:
        selected.remove(card)
    else:
        selected.append(card)

    page = context.user_data["page"]
    category = context.user_data["category"]

    keyboard = build_keyboard(CARDS[category], "have", page, selected)

    text = "Select cards you HAVE:\n\nSelected:\n" + ("\n".join(selected) if selected else "None")

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= WANT =================
async def done_have(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["want_cards"] = []
    context.user_data["page"] = 0

    category = context.user_data["category"]

    keyboard = build_keyboard(CARDS[category], "want", 0, [])

    await query.edit_message_text(
        "Select cards you WANT:\n\nSelected: None",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_want(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    card = query.data.replace("want_", "")
    selected = context.user_data["want_cards"]

    if card in selected:
        selected.remove(card)
    else:
        selected.append(card)

    page = context.user_data["page"]
    category = context.user_data["category"]

    keyboard = build_keyboard(CARDS[category], "want", page, selected)

    text = "Select cards you WANT:\n\nSelected:\n" + ("\n".join(selected) if selected else "None")

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ================= PAGINATION =================
async def handle_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, prefix, page = query.data.split("_")
    page = int(page)

    context.user_data["page"] = page
    category = context.user_data["category"]

    selected = context.user_data["has_cards"] if prefix == "have" else context.user_data["want_cards"]

    keyboard = build_keyboard(CARDS[category], prefix, page, selected)

    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

# ================= DONE WANT =================
async def done_want(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="code_yes")],
        [InlineKeyboardButton("No", callback_data="code_no")]
    ]

    await query.edit_message_text(
        "Do you have an external exchange code?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= CODE =================
async def handle_code_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "code_yes":
        context.user_data["waiting_for_code"] = True
        await query.message.reply_text("Enter your code:")
    else:
        context.user_data["exchange_code"] = None
        await save_user(update, context)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("waiting_for_code"):
        context.user_data["exchange_code"] = update.message.text
        context.user_data["waiting_for_code"] = False
        await save_user(update, context)

# ================= SAVE =================
async def save_user(update, context):
    user_id = update.effective_user.id

    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    cursor.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
        (
            user_id,
            context.user_data["category"],
            ",".join(context.user_data["has_cards"]),
            ",".join(context.user_data["want_cards"]),
            context.user_data.get("exchange_code")
        )
    )
    conn.commit()

    await match_users(update, context)

# ================= MATCH =================
async def match_users(update, context):
    user = update.effective_user
    user_id = user.id

    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    me = cursor.fetchone()

    cursor.execute("SELECT * FROM users WHERE user_id!=?", (user_id,))
    others = cursor.fetchall()

    for other in others:
        if me[1] != other[1]:
            continue

        if set(me[2].split(",")) & set(other[3].split(",")) and \
           set(me[3].split(",")) & set(other[2].split(",")):

            other_id = other[0]
            chat = await context.bot.get_chat(other_id)

            msg_me = f"🎉 Match Found!\nYou matched with: {chat.first_name}"
            msg_me += get_rating_text(other_id)

            msg_other = f"🎉 Match Found!\nYou matched with: {user.first_name}"
            msg_other += get_rating_text(user_id)

            if other[4]:
                msg_me += f"\nCode: {other[4]}"
            if me[4]:
                msg_other += f"\nCode: {me[4]}"

            await context.bot.send_message(user_id, msg_me)
            await context.bot.send_message(other_id, msg_other)

            # rating buttons
            keyboard = [[
                InlineKeyboardButton("⭐1", callback_data=f"rate_{other_id}_1"),
                InlineKeyboardButton("⭐2", callback_data=f"rate_{other_id}_2"),
                InlineKeyboardButton("⭐3", callback_data=f"rate_{other_id}_3"),
                InlineKeyboardButton("⭐4", callback_data=f"rate_{other_id}_4"),
                InlineKeyboardButton("⭐5", callback_data=f"rate_{other_id}_5"),
            ]]

            await context.bot.send_message(
                user_id, "Rate this user:", reply_markup=InlineKeyboardMarkup(keyboard)
            )

            return

    await context.bot.send_message(user_id, "No match found yet.")

# ================= RATING =================
async def rate_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, target_id, rating = query.data.split("_")
    target_id = int(target_id)
    rating = int(rating)

    cursor.execute("SELECT total_rating, rating_count FROM ratings WHERE user_id=?", (target_id,))
    row = cursor.fetchone()

    if row:
        total, count = row
        cursor.execute("UPDATE ratings SET total_rating=?, rating_count=? WHERE user_id=?",
                       (total + rating, count + 1, target_id))
    else:
        cursor.execute("INSERT INTO ratings VALUES (?, ?, ?)", (target_id, rating, 1))

    conn.commit()

    await query.edit_message_text("✅ Rating submitted!")

# ================= APP =================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_category, pattern="^category_"))
app.add_handler(CallbackQueryHandler(handle_have, pattern="^have_"))
app.add_handler(CallbackQueryHandler(done_have, pattern="done_have"))
app.add_handler(CallbackQueryHandler(handle_want, pattern="^want_"))
app.add_handler(CallbackQueryHandler(done_want, pattern="done_want"))
app.add_handler(CallbackQueryHandler(handle_code_choice, pattern="^code_"))
app.add_handler(CallbackQueryHandler(handle_page, pattern="^page_"))
app.add_handler(CallbackQueryHandler(rate_user, pattern="^rate_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

app.run_polling()