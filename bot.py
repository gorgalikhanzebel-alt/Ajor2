import asyncio
import os
import logging
import random
import aiohttp
import uuid
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from pymongo import MongoClient
from aiohttp import web
from pytube import YouTube

TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

if not TOKEN or not MONGO_URI:
    logging.error("❌ متغیرهای محیطی تنظیم نشده‌اند!")
    exit(1)

client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_col = db["users"]
files_col = db["files"]
banned_col = db["banned"]

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

ADMIN_ID = int(os.getenv("ADMIN_ID", 466050034))
CHANNEL_ID = -1001277492702
CHANNEL_LINK = "https://t.me/ajor_pareh"
DEFAULT_CAPTION = "📌 عضویت در کانال ما: @ajor_pareh"
OPENROUTER_API_KEY = "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"

# ======== دیکشنری‌های سبک ========
GREETINGS = {"سلام": "سلام! 👋", "خوبی": "خوبم ممنون!", "چطوری": "خوبم!", "مرسی": "خواهش!", "خداحافظ": "خداحافظ! 👋", "صبح بخیر": "صبح بخیر! ☀️", "شب بخیر": "شب بخیر! 🌙", "خوش اومدی": "خوش اومدی! ✨", "درود": "درود! 🌹"}
JOKES = ["چرا مرغ از جاده رد شد؟ 😂", "پایتون بهترین زبان! 🐍", "پنگوئن گفت چقدر خنک! 😄", "ریاضیات غمگینه؟ بی‌جوابه!", "نارگیل تو رودخونه آب میشه!"]
QUOTES = ["به فکر فردا باش!", "بلند شدن دوباره!", "کد بزن لذت ببر!", "زندگی مثل شکلاته!", "بهترین زمان الان است!"]
FUNNY = ["چی میگی بچه خوشگل؟ 😏", "سیک تو بزن! 😂", "نمیفهمم حاجی!"]

guess_games = {}

# ======== توابع ========
async def is_admin(user_id): return user_id == ADMIN_ID
async def is_banned(user_id): return banned_col.find_one({"_id": user_id}) is not None
async def is_member(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except: return False

async def ask_ai(query):
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
            data = {"model": "google/gemini-2.0-flash-lite-001", "messages": [{"role": "user", "content": query}], "max_tokens": 300}
            async with session.post(url, headers=headers, json=data, timeout=10) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['choices'][0]['message']['content']
    except: pass
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.nexra.aryan.ir/v1/chat/gpt?text={query}"
            async with session.get(url, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "success" and data.get("data"):
                        return data["data"].strip()
    except: pass
    return None

def get_tehran_time():
    return datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)

# ======== منوها ========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎬 دانلود یوتیوب", callback_data="youtube")],
        [InlineKeyboardButton("🎮 بازی", callback_data="game")],
        [InlineKeyboardButton("💳 کیف پول", callback_data="wallet"), InlineKeyboardButton("💰 شارژ", callback_data="charge")],
        [InlineKeyboardButton("🛠 پشتیبانی", callback_data="support"), InlineKeyboardButton("👤 حساب", callback_data="profile_user")],
        [InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin_panel")]
    ])

def game_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎲 تاس", callback_data="dice"), InlineKeyboardButton("🎯 دارت", callback_data="dart")],
        [InlineKeyboardButton("🪨 سنگ‌کاغذ", callback_data="rps")],
        [InlineKeyboardButton("🔢 حدس عدد", callback_data="guess_game")],
        [InlineKeyboardButton("🪙 شیر یا خط", callback_data="coin_flip")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]
    ])

def rps_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🪨 سنگ", callback_data="rps_stone")],
        [InlineKeyboardButton("📄 کاغذ", callback_data="rps_paper")],
        [InlineKeyboardButton("✂️ قیچی", callback_data="rps_scissors")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_game")]
    ])

def coin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🪙 شیر", callback_data="coin_heads")],
        [InlineKeyboardButton("🪙 خط", callback_data="coin_tails")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_game")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📊 آمار", callback_data="stats")],
        [InlineKeyboardButton("📋 کاربران", callback_data="user_list")],
        [InlineKeyboardButton("📢 همگانی", callback_data="broadcast")],
        [InlineKeyboardButton("🔍 جستجو", callback_data="search_user")],
        [InlineKeyboardButton("🚫 مسدودها", callback_data="ban_management")],
        [InlineKeyboardButton("⚙️ گروه", callback_data="group_manage")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="back_main")]
    ])

def group_manage_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔒 قفل", callback_data="lock_group"), InlineKeyboardButton("🔓 باز", callback_data="unlock_group")],
        [InlineKeyboardButton("🚫 بن", callback_data="ban_user"), InlineKeyboardButton("✅ رفع بن", callback_data="unban_user")],
        [InlineKeyboardButton("🧹 پاک کردن", callback_data="clear_messages")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="admin_panel")]
    ])

def channel_check_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📢 عضویت", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ عضویت داشتم", callback_data="check_join")]
    ])

# ============================================
# ======== START ========
# ============================================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    if await is_banned(user_id):
        return await message.answer("🚫 مسدود هستید!")
    if message.text and message.text.startswith("/start file_"):
        file_uuid = message.text.split("_")[1]
        file_data = files_col.find_one({"uuid": file_uuid})
        if file_data:
            if not await is_member(user_id):
                return await message.answer(f"👋 {name}!\nبرای دریافت فایل، عضو کانال بشو:", reply_markup=channel_check_menu())
            file_id, file_type, caption = file_data["file_id"], file_data["type"], file_data.get("caption", DEFAULT_CAPTION)
            if file_type == "photo": await message.answer_photo(file_id, caption=caption)
            elif file_type == "video": await message.answer_video(file_id, caption=caption)
            else: await message.answer_document(file_id, caption=caption)
            return
        return await message.answer("❌ فایل یافت نشد.")
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id, "name": name, "joined_at": datetime.now()})
    if not await is_member(user_id):
        return await message.answer(f"👋 {name}!\nبرای استفاده، عضو کانال بشو:", reply_markup=channel_check_menu())
    await message.answer(f"🚀 سلام {name}!", reply_markup=main_menu())

@dp.callback_query(lambda c: c.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        return await callback.answer("🚫 مسدود!", show_alert=True)
    if await is_member(callback.from_user.id):
        await callback.message.edit_text("✅ ممنون!")
        await callback.message.answer("🚀 منوی اصلی:", reply_markup=main_menu())
    else:
        await callback.answer("❌ عضو نشدی!", show_alert=True)

# ============================================
# ======== یوتیوب ========
# ============================================
@dp.callback_query(lambda c: c.data == "youtube")
async def youtube(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("🎬 لینک یوتیوب را بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and ("youtube.com" in msg.text or "youtu.be" in msg.text))
async def get_youtube(message: types.Message):
    if await is_banned(message.from_user.id) or not await is_member(message.from_user.id):
        return await message.answer("⛔ دسترسی ندارید!")
    try:
        yt = YouTube(message.text)
        stream = yt.streams.get_highest_resolution()
        if stream:
            await message.answer_video(stream.url, caption=f"🎬 {yt.title}")
        else:
            await message.answer("❌ خطا!")
    except:
        await message.answer("❌ لینک نامعتبر!")

# ============================================
# ======== منو اصلی ========
# ============================================
@dp.callback_query(lambda c: c.data in ["wallet", "charge", "support", "profile_user"])
async def menu_items(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        return await callback.answer("🚫 مسدود!", show_alert=True)
    data = {
        "wallet": "💳 کیف پول: ۰ تومان",
        "charge": "💰 شارژ: ۱۰K, ۵۰K, ۱۰۰K",
        "support": "🛠 @AdminUsername",
        "profile_user": f"👤 {callback.from_user.full_name}\n🆔 {callback.from_user.id}"
    }
    await callback.message.answer(data[callback.data])
    await callback.answer()

# ============================================
# ======== بازی‌ها ========
# ============================================
@dp.callback_query(lambda c: c.data == "game")
async def game(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("🎮 انتخاب کن:", reply_markup=game_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["dice", "dart"])
async def dice_games(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    emoji = "🎲" if callback.data == "dice" else "🎯"
    await callback.message.answer_dice(emoji=emoji)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "rps")
async def rps(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("🪨 انتخاب کن:", reply_markup=rps_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["rps_stone", "rps_paper", "rps_scissors"])
async def rps_play(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    choices = {"rps_stone": "🪨 سنگ", "rps_paper": "📄 کاغذ", "rps_scissors": "✂️ قیچی"}
    beats = {"rps_stone": "rps_scissors", "rps_paper": "rps_stone", "rps_scissors": "rps_paper"}
    user = callback.data
    bot = random.choice(list(choices.keys()))
    if user == bot: result = "🤝 مساوی!"
    elif beats[user] == bot: result = "🎉 بردی!"
    else: result = "😢 باختی!"
    await callback.message.answer(f"تو: {choices[user]}\nربات: {choices[bot]}\n{result}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "guess_game")
async def guess_game(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    number = random.randint(1, 20)
    guess_games[callback.from_user.id] = {"number": number, "attempts": 0}
    await callback.message.answer("🔢 عدد ۱ تا ۲۰ بفرست (/cancel لغو)")
    await callback.answer()

@dp.message(Command("cancel"))
async def cancel_guess(message: types.Message):
    if message.from_user.id in guess_games:
        del guess_games[message.from_user.id]
        await message.answer("❌ لغو شد.")

@dp.message(lambda msg: msg.text and msg.text.isdigit())
async def handle_guess(message: types.Message):
    if message.from_user.id not in guess_games: return
    user_id = message.from_user.id
    guess = int(message.text)
    game = guess_games[user_id]
    game["attempts"] += 1
    target = game["number"]
    if guess == target:
        await message.answer(f"🎉 عدد {target} بود! تلاش: {game['attempts']}")
        del guess_games[user_id]
    elif guess < target:
        await message.answer(f"📈 بیشتر از {guess}")
    else:
        await message.answer(f"📉 کمتر از {guess}")

@dp.callback_query(lambda c: c.data == "coin_flip")
async def coin_flip(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("🪙 شیر یا خط؟", reply_markup=coin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["coin_heads", "coin_tails"])
async def coin_play(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id) or not await is_member(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    user = "شیر" if callback.data == "coin_heads" else "خط"
    bot = random.choice(["شیر", "خط"])
    await callback.message.answer(f"تو: {user}\nربات: {bot}\n{'🎉' if user == bot else '😢'}")
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["back_main", "back_game"])
async def back(callback: types.CallbackQuery):
    if callback.data == "back_main":
        await callback.message.answer("🔙 منوی اصلی:", reply_markup=main_menu())
    else:
        await callback.message.answer("🔙 منوی بازی:", reply_markup=game_menu())
    await callback.answer()

# ============================================
# ======== پنل ادمین ========
# ============================================
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("⚙️ پنل ادمین:", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats")
async def stats(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    total = users_col.count_documents({})
    banned = banned_col.count_documents({})
    files = files_col.count_documents({})
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today = users_col.count_documents({"joined_at": {"$gte": today_start}})
    await callback.message.answer(f"📊 کل: {total}\n📅 امروز: {today}\n🚫 مسدود: {banned}\n📁 فایل‌ها: {files}")

@dp.callback_query(lambda c: c.data == "user_list")
async def user_list(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    users = list(users_col.find().sort("joined_at", -1).limit(15))
    if not users:
        return await callback.message.answer("📭 کاربری نیست.")
    text = "📋 کاربران اخیر:\n"
    for i, u in enumerate(users, 1):
        name = u.get("name", "نامشخص")
        text += f"{i}. {name} (ID: {u['_id']})\n"
    await callback.message.answer(text)

@dp.callback_query(lambda c: c.data == "search_user")
async def search_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("🔍 آیدی یا نام بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and await is_admin(msg.from_user.id))
async def handle_search(message: types.Message):
    if not await is_admin(message.from_user.id): return
    query = message.text.strip()
    if query.isdigit():
        user = users_col.find_one({"_id": int(query)})
        if user:
            await message.answer(f"👤 {user.get('name', 'نامشخص')}\n🆔 {user['_id']}")
        else:
            await message.answer("❌ یافت نشد.")
    else:
        users = list(users_col.find({"name": {"$regex": query, "$options": "i"}}).limit(10))
        if users:
            text = f"🔍 نتایج '{query}':\n"
            for u in users:
                text += f"👤 {u.get('name', 'نامشخص')} (ID: {u['_id']})\n"
            await message.answer(text)
        else:
            await message.answer("❌ یافت نشد.")

@dp.callback_query(lambda c: c.data == "broadcast")
async def broadcast(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("📢 پیام رو بفرست (ریپلی کن):")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.reply_to_message and await is_admin(msg.from_user.id))
async def handle_broadcast(message: types.Message):
    if not await is_admin(message.from_user.id): return
    if "پیام رو بفرست" in message.reply_to_message.text:
        text = message.text
        users = users_col.find()
        sent = 0
        for user in users:
            try:
                await bot.send_message(user["_id"], text)
                sent += 1
            except: pass
        await message.answer(f"✅ به {sent} کاربر ارسال شد.")

@dp.callback_query(lambda c: c.data == "ban_management")
async def ban_management(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    banned = list(banned_col.find())
    if banned:
        text = "🚫 مسدودها:\n"
        for b in banned[:15]:
            text += f"ID: {b['_id']}\n"
        await callback.message.answer(text)
    else:
        await callback.message.answer("✅ هیچکس مسدود نیست.")

@dp.callback_query(lambda c: c.data in ["ban_user", "unban_user"])
async def ban_actions(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    action = "مسدود" if callback.data == "ban_user" else "رفع مسدود"
    await callback.message.answer(f"🚫 آیدی رو برای {action} بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and await is_admin(msg.from_user.id))
async def ban_unban_cmd(message: types.Message):
    user_id = int(message.text)
    if user_id == ADMIN_ID:
        return await message.answer("❌ خودت نه!")
    if await is_banned(user_id):
        banned_col.delete_one({"_id": user_id})
        await message.answer(f"✅ مسدودیت {user_id} رفع شد.")
    else:
        banned_col.insert_one({"_id": user_id, "reason": "ادمین"})
        await message.answer(f"✅ {user_id} مسدود شد.")
        try:
            await bot.send_message(user_id, "🚫 مسدود شدی!")
        except: pass

@dp.callback_query(lambda c: c.data == "group_manage")
async def group_manage(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("⚙️ گروه:", reply_markup=group_manage_menu())

@dp.callback_query(lambda c: c.data in ["lock_group", "unlock_group"])
async def lock_unlock(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    can_send = False if callback.data == "lock_group" else True
    await bot.set_chat_permissions(callback.message.chat.id, ChatPermissions(can_send_messages=can_send))
    await callback.message.answer("🔒 قفل!" if not can_send else "🔓 باز!")

@dp.callback_query(lambda c: c.data == "clear_messages")
async def clear_messages(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer("🧹 تعداد پیام بفرست (مثلاً 10):")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and await is_admin(msg.from_user.id))
async def clear_cmd(message: types.Message):
    count = int(message.text)
    if count > 100:
        return await message.answer("❌ حداکثر ۱۰۰.")
    deleted = 0
    async for msg in bot.get_chat_history(message.chat.id, limit=count):
        if msg.message_id != message.message_id:
            await msg.delete()
            deleted += 1
    await message.answer(f"✅ {deleted} پیام پاک شد.")

# ============================================
# ======== آپلود فایل ========
# ============================================
@dp.message(Command("upload"))
async def upload_file_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ فقط ادمین!")
    await message.answer("📤 فایل رو بفرست:")

@dp.message(lambda msg: msg.document or msg.photo or msg.video)
async def handle_file_upload(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ فقط ادمین!")
    if message.document:
        file_id, file_type, name = message.document.file_id, "document", message.document.file_name
    elif message.photo:
        file_id, file_type, name = message.photo[-1].file_id, "photo", "عکس"
    elif message.video:
        file_id, file_type, name = message.video.file_id, "video", "ویدئو"
    else:
        return await message.answer("❌ پشتیبانی نمی‌شود.")
    file_uuid = str(uuid.uuid4())[:8]
    caption = message.caption if message.caption else DEFAULT_CAPTION
    files_col.insert_one({"uuid": file_uuid, "file_id": file_id, "type": file_type, "name": name, "caption": caption, "uploaded_at": datetime.now()})
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=file_{file_uuid}"
    await message.answer(f"✅ آپلود شد!\n🔗 <code>{link}</code>", parse_mode="HTML")

# ============================================
# ======== دستورات عمومی ========
# ============================================
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 راهنما:\n"
        "/start - شروع\n/time - زمان تهران\n/id - آیدی\n/profile - پروفایل\n"
        "/joke - جوک\n/quote - نقل قول\n/ping - وضعیت\n/admin - پنل\n/cancel - لغو حدس\n/upload - آپلود")

@dp.message(Command("time"))
async def time_command(message: types.Message):
    t = get_tehran_time()
    days = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه"]
    await message.answer(f"🕒 {t.strftime('%Y/%m/%d')} {days[t.weekday()]}\n⏰ {t.strftime('%H:%M:%S')}")

@dp.message(Command("id"))
async def id_command(message: types.Message):
    await message.answer(f"🆔 <code>{message.from_user.id}</code>", parse_mode="HTML")

@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_data = users_col.find_one({"_id": message.from_user.id})
    if user_data:
        joined = user_data.get("joined_at")
        if isinstance(joined, datetime):
            joined = joined.strftime("%Y-%m-%d")
        else:
            joined = "نامشخص"
        await message.answer(f"👤 {message.from_user.full_name}\n🆔 {message.from_user.id}\n📅 {joined}")
    else:
        await message.answer(f"👤 {message.from_user.full_name}\n🆔 {message.from_user.id}")

@dp.message(Command("joke"))
async def joke(message: types.Message): await message.answer(random.choice(JOKES))

@dp.message(Command("quote"))
async def quote(message: types.Message): await message.answer(f"💬 {random.choice(QUOTES)}")

@dp.message(Command("ping"))
async def ping(message: types.Message): await message.answer("✅ آنلاین!")

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    await message.answer("⚙️ پنل ادمین:", reply_markup=admin_menu())

# ============================================
# ======== پیام‌های متنی ========
# ============================================
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private": return
    user_id = message.from_user.id
    if await is_banned(user_id):
        return await message.answer("🚫 مسدود!")
    if not await is_member(user_id):
        return await message.answer("❌ عضو کانال نیستی!", reply_markup=channel_check_menu())
    text = message.text.strip().lower()
    for key, response in GREETINGS.items():
        if key in text:
            return await message.answer(response)
    ai_response = await ask_ai(text)
    if ai_response:
        return await message.answer(ai_response)
    await message.answer(random.choice(FUNNY))

# ============================================
# ======== سرور ========
# ============================================
async def health_check(request):
    return web.Response(text="✅ Bot is running!")

async def start_web():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logging.info(f"✅ Web server started on port {port}")

async def main():
    await start_web()
    logging.info("🤖 Starting bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
