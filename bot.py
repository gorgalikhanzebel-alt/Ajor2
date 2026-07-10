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
import traceback

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
CHANNEL_ID = int(os.getenv("CHANNEL_ID", -1001277492702))
CHANNEL_LINK = "https://t.me/ajor_pareh"
DEFAULT_CAPTION = "📌 عضویت در کانال ما: @ajor_pareh"

OPENROUTER_API_KEY = "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"

# ======== دیکشنری‌های سبک ========
GREETINGS = {"سلام": "سلام! 👋", "خوبی": "خوبم ممنون!", "چطوری": "خوبم!", "مرسی": "خواهش!", "خداحافظ": "خداحافظ! 👋", "صبح بخیر": "صبح بخیر! ☀️", "شب بخیر": "شب بخیر! 🌙", "خوش اومدی": "خوش اومدی! ✨", "درود": "درود! 🌹"}
JOKES = ["چرا مرغ از جاده رد شد؟ 😂", "پایتون بهترین زبان! 🐍", "پنگوئن گفت چقدر خنک! 😄", "ریاضیات غمگینه؟ بی‌جوابه!", "نارگیل تو رودخونه آب میشه!", "یه گربه گفت منوس! 😹"]
QUOTES = ["به فکر فردا باش!", "بلند شدن دوباره!", "کد بزن لذت ببر!", "زندگی مثل شکلاته!", "بهترین زمان الان است!", "با امید تلاش کن! 🏔️"]
FUNNY = ["چی میگی بچه خوشگل؟ 😏", "سیک تو بزن! 😂", "نمیفهمم حاجی!", "چرت و پرت نگو! 🤔"]

guess_games = {}

# ======== توابع ========
async def is_admin(user_id): return user_id == ADMIN_ID
async def is_banned(user_id): return banned_col.find_one({"_id": user_id}) is not None
async def is_member(user_id):
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

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

# ======== منوهای شیشه‌ای (تصحیح‌شده) ========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎬 یوتیوب", callback_data="youtube")],
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
        [InlineKeyboardButton("🔍 جستجو", callback_data="search_user")],
        [InlineKeyboardButton("👤 پروفایل", callback_data="view_profile")],
        [InlineKeyboardButton("📢 همگانی", callback_data="broadcast")],
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
    try:
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
        
        await message.answer(
            f"🚀 سلام {name}!\nبه ربات خوش آمدی. از دکمه‌های زیر استفاده کن:",
            reply_markup=main_menu()
        )
    except Exception as e:
        logging.error(f"❌ خطا در start: {e}\n{traceback.format_exc()}")
        await message.answer("❌ خطایی رخ داد! لطفاً دوباره تلاش کن.")

# ======== بقیه کدها (بدون تغییر) ========
@dp.callback_query(lambda c: c.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        return await callback.answer("🚫 مسدود!", show_alert=True)
    if await is_member(callback.from_user.id):
        await callback.message.edit_text("✅ ممنون! حالا می‌تونی استفاده کنی.")
        await callback.message.answer("🚀 منوی اصلی:", reply_markup=main_menu())
    else:
        await callback.answer("❌ عضو نشدی!", show_alert=True)

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
# ======== پنل ادمین (دستوری) ========
# ============================================
@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    total = users_col.count_documents({})
    banned = banned_col.count_documents({})
    files = files_col.count_documents({})
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today = users_col.count_documents({"joined_at": {"$gte": today_start}})
    await message.answer(
        f"📊 **آمار ربات**\n\n"
        f"👥 کل کاربران: {total}\n"
        f"📅 امروز: {today}\n"
        f"🚫 مسدودها: {banned}\n"
        f"📁 فایل‌ها: {files}"
    )

@dp.message(Command("users"))
async def users_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    users = list(users_col.find().sort("joined_at", -1).limit(20))
    if not users:
        return await message.answer("📭 کاربری ثبت نشده.")
    text = "📋 **۲۰ کاربر اخیر**\n\n"
    for i, u in enumerate(users, 1):
        name = u.get("name", "نامشخص")
        joined = u.get("joined_at", "")
        if isinstance(joined, datetime):
            joined = joined.strftime("%Y-%m-%d")
        else:
            joined = "نامشخص"
        text += f"{i}. {name} (ID: {u['_id']}) - {joined}\n"
    await message.answer(text)

@dp.message(Command("search"))
async def search_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    query = message.text.replace("/search", "").strip()
    if not query:
        return await message.answer("🔍 لطفاً نام یا آیدی کاربر را بعد از دستور وارد کنید.\nمثال: `/search امیر`")
    if query.isdigit():
        user = users_col.find_one({"_id": int(query)})
        if user:
            await show_profile(message, user)
        else:
            await message.answer("❌ کاربری با این آیدی یافت نشد.")
    else:
        users = list(users_col.find({"name": {"$regex": query, "$options": "i"}}).limit(10))
        if users:
            res = f"🔍 نتایج '{query}':\n"
            for u in users:
                joined = u.get("joined_at", "")
                if isinstance(joined, datetime):
                    joined = joined.strftime("%Y-%m-%d")
                else:
                    joined = "نامشخص"
                res += f"👤 {u.get('name', 'نامشخص')} (ID: {u['_id']}) - {joined}\n"
            await message.answer(res)
        else:
            await message.answer("❌ کاربری یافت نشد.")

@dp.message(Command("profile"))
async def profile_admin_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    query = message.text.replace("/profile", "").strip()
    if not query:
        return await message.answer("👤 لطفاً آیدی کاربر را وارد کنید.\nمثال: `/profile 123456789`")
    if query.isdigit():
        user = users_col.find_one({"_id": int(query)})
        if user:
            await show_profile(message, user)
        else:
            await message.answer("❌ کاربری با این آیدی یافت نشد.")
    else:
        await message.answer("❌ لطفاً یک آیدی عددی معتبر وارد کنید.")

@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    text = message.text.replace("/broadcast", "").strip()
    if not text:
        return await message.answer("📢 لطفاً متن پیام را بعد از دستور وارد کنید.\nمثال: `/broadcast سلام به همه`")
    users = users_col.find()
    sent = 0
    for user in users:
        try:
            await bot.send_message(user["_id"], text)
            sent += 1
        except: pass
    await message.answer(f"✅ پیام به {sent} کاربر ارسال شد.")

@dp.message(Command("ban"))
async def ban_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    query = message.text.replace("/ban", "").strip()
    if not query:
        return await message.answer("🚫 لطفاً آیدی کاربر را وارد کنید.\nمثال: `/ban 123456789`")
    if query.isdigit():
        user_id = int(query)
        if user_id == ADMIN_ID:
            return await message.answer("❌ خودت رو مسدود نکن!")
        if await is_banned(user_id):
            return await message.answer(f"⚠️ کاربر {user_id} قبلاً مسدود است.")
        banned_col.insert_one({"_id": user_id, "reason": "ادمین"})
        await message.answer(f"✅ کاربر {user_id} مسدود شد.")
        try:
            await bot.send_message(user_id, "🚫 توسط ادمین مسدود شدی!")
        except: pass
    else:
        await message.answer("❌ لطفاً یک آیدی عددی معتبر وارد کنید.")

@dp.message(Command("unban"))
async def unban_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    query = message.text.replace("/unban", "").strip()
    if not query:
        return await message.answer("✅ لطفاً آیدی کاربر را وارد کنید.\nمثال: `/unban 123456789`")
    if query.isdigit():
        user_id = int(query)
        if await is_banned(user_id):
            banned_col.delete_one({"_id": user_id})
            await message.answer(f"✅ مسدودیت {user_id} رفع شد.")
        else:
            await message.answer(f"❌ کاربر {user_id} مسدود نیست.")
    else:
        await message.answer("❌ لطفاً یک آیدی عددی معتبر وارد کنید.")

@dp.message(Command("banned"))
async def banned_list_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    banned = list(banned_col.find())
    if banned:
        text = "🚫 **لیست مسدودها:**\n\n"
        for b in banned[:15]:
            text += f"ID: {b['_id']}\n"
        await message.answer(text)
    else:
        await message.answer("✅ هیچ کاربری مسدود نیست.")

@dp.message(Command("lock"))
async def lock_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    if message.chat.type == "private":
        return await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
    await bot.set_chat_permissions(message.chat.id, ChatPermissions(can_send_messages=False))
    await message.answer("🔒 گروه قفل شد!")

@dp.message(Command("unlock"))
async def unlock_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    if message.chat.type == "private":
        return await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
    await bot.set_chat_permissions(message.chat.id, ChatPermissions(can_send_messages=True))
    await message.answer("🔓 گروه باز شد!")

@dp.message(Command("clear"))
async def clear_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    if message.chat.type == "private":
        return await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
    query = message.text.replace("/clear", "").strip()
    if not query or not query.isdigit():
        return await message.answer("🧹 لطفاً تعداد پیام را وارد کنید.\nمثال: `/clear 10`")
    count = int(query)
    if count > 100:
        return await message.answer("❌ حداکثر ۱۰۰ پیام.")
    deleted = 0
    async for msg in bot.get_chat_history(message.chat.id, limit=count):
        if msg.message_id != message.message_id:
            await msg.delete()
            deleted += 1
    await message.answer(f"✅ {deleted} پیام پاک شد.")

async def show_profile(message, user):
    name = user.get("name", "نامشخص")
    uid = user.get("_id", "نامشخص")
    joined = user.get("joined_at", "")
    if isinstance(joined, datetime):
        joined = joined.strftime("%Y-%m-%d %H:%M")
    else:
        joined = "نامشخص"
    banned = await is_banned(uid)
    text = (
        f"👤 **پروفایل کاربر**\n\n"
        f"نام: {name}\n"
        f"🆔 آیدی: {uid}\n"
        f"📅 تاریخ عضویت: {joined}\n"
        f"🚫 وضعیت: {'مسدود' if banned else 'فعال'}"
    )
    await message.answer(text)

# ============================================
# ======== دکمه‌های پنل ادمین ========
# ============================================
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        return await callback.answer("⛔ دسترسی!", show_alert=True)
    await callback.message.answer(
        "⚙️ **پنل ادمین (دستوری)**\n\n"
        "📊 `/stats` - آمار کامل\n"
        "📋 `/users` - لیست ۲۰ کاربر اخیر\n"
        "🔍 `/search [نام/آیدی]` - جستجوی کاربر\n"
        "👤 `/profile [آیدی]` - مشاهده پروفایل\n"
        "📢 `/broadcast [متن]` - ارسال همگانی\n"
        "🚫 `/ban [آیدی]` - مسدود کردن\n"
        "✅ `/unban [آیدی]` - رفع مسدودیت\n"
        "📋 `/banned` - لیست مسدودها\n"
        "🔒 `/lock` - قفل گروه\n"
        "🔓 `/unlock` - باز کردن گروه\n"
        "🧹 `/clear [تعداد]` - پاک کردن پیام‌ها"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats")
async def stats_callback(callback: types.CallbackQuery):
    await stats_cmd(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "user_list")
async def user_list_callback(callback: types.CallbackQuery):
    await users_cmd(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "search_user")
async def search_user_callback(callback: types.CallbackQuery):
    await callback.message.answer("🔍 از دستور `/search [نام/آیدی]` استفاده کنید.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "view_profile")
async def view_profile_callback(callback: types.CallbackQuery):
    await callback.message.answer("👤 از دستور `/profile [آیدی]` استفاده کنید.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "broadcast")
async def broadcast_callback(callback: types.CallbackQuery):
    await callback.message.answer("📢 از دستور `/broadcast [متن]` استفاده کنید.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "ban_management")
async def ban_management_callback(callback: types.CallbackQuery):
    await banned_list_cmd(callback.message)
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["ban_user", "unban_user"])
async def ban_unban_callback(callback: types.CallbackQuery):
    action = "ban" if callback.data == "ban_user" else "unban"
    await callback.message.answer(f"🔄 از دستور `/{action} [آیدی]` استفاده کنید.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "group_manage")
async def group_manage_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        "⚙️ **مدیریت گروه**\n\n"
        "🔒 `/lock` - قفل گروه\n"
        "🔓 `/unlock` - باز کردن گروه\n"
        "🧹 `/clear [تعداد]` - پاک کردن پیام‌ها"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["lock_group", "unlock_group", "clear_messages"])
async def group_actions_callback(callback: types.CallbackQuery):
    cmd_map = {"lock_group": "lock", "unlock_group": "unlock", "clear_messages": "clear 10"}
    await callback.message.answer(f"🔄 از دستور `/{cmd_map[callback.data]}` استفاده کنید.")
    await callback.answer()

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
        "📖 **راهنما**\n"
        "/start - شروع و منوی اصلی\n"
        "/time - زمان تهران\n"
        "/id - آیدی من\n"
        "/profile - پروفایل من\n"
        "/joke - جوک\n"
        "/quote - نقل قول\n"
        "/ping - وضعیت\n"
        "/admin - پنل ادمین\n"
        "/cancel - لغو حدس\n"
        "/upload - آپلود (ادمین)"
    )

@dp.message(Command("time"))
async def time_command(message: types.Message):
    t = get_tehran_time()
    days = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه"]
    await message.answer(f"🕒 **زمان تهران**\n📅 {t.strftime('%Y/%m/%d')} - {days[t.weekday()]}\n⏰ {t.strftime('%H:%M:%S')}")

@dp.message(Command("id"))
async def id_command(message: types.Message):
    await message.answer(f"🆔 آیدی شما:\n<code>{message.from_user.id}</code>", parse_mode="HTML")

@dp.message(Command("profile"))
async def profile_self(message: types.Message):
    user_data = users_col.find_one({"_id": message.from_user.id})
    if user_data:
        joined = user_data.get("joined_at")
        if isinstance(joined, datetime):
            joined = joined.strftime("%Y-%m-%d %H:%M")
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
async def ping(message: types.Message): await message.answer("✅ ربات آنلاین!")

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ دسترسی!")
    await message.answer(
        "⚙️ **پنل ادمین (دستوری)**\n\n"
        "📊 `/stats` - آمار کامل\n"
        "📋 `/users` - لیست ۲۰ کاربر اخیر\n"
        "🔍 `/search [نام/آیدی]` - جستجوی کاربر\n"
        "👤 `/profile [آیدی]` - مشاهده پروفایل کاربر\n"
        "📢 `/broadcast [متن]` - ارسال همگانی\n"
        "🚫 `/ban [آیدی]` - مسدود کردن\n"
        "✅ `/unban [آیدی]` - رفع مسدودیت\n"
        "📋 `/banned` - لیست مسدودها\n"
        "🔒 `/lock` - قفل گروه\n"
        "🔓 `/unlock` - باز کردن گروه\n"
        "🧹 `/clear [تعداد]` - پاک کردن پیام‌ها"
    )

# ============================================
# ======== پیام‌های متنی ========
# ============================================
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private":
        return
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
