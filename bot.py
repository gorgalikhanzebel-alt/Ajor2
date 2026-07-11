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
groups_col = db["groups"]
activities_col = db["activities"]

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

ADMIN_ID = 466050034
CHANNEL_ID = -1001277492702
CHANNEL_LINK = "https://t.me/ajor_pareh"
DEFAULT_CAPTION = "📌 عضویت در کانال ما: @ajor_pareh"

OPENROUTER_API_KEY = "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"

# ======== لیست‌ها ========
FUNNY_FALLBACKS = [
    "چی میگی بچه خوشگل؟ 😏", "سیک تو بزن تا سیکمو نزدن 😂", "نمیفهمم حاجی چی میگی",
    "این چرت و پرتا چیه میگی مردک 🤔", "به نظرم ط ی چیزی زدی اینارو میگی"
]

JOKES = [
    "چرا مرغ از جاده رد شد؟ برای اینکه به اون طرف برسه! 😂",
    "بهترین زبان برنامه‌نویسی؟ پایتون! 🐍",
    "یک پنگوئن به یخچال نگاه کرد و گفت: چقدر خنک! 😄",
    "چرا ریاضیات غمگینه؟ چون مسائلش بی‌جوابه!",
    "چی می‌شه اگه نارگیل رو بندازی تو رودخونه؟ آب می‌شه!",
    "یک گربه به کامپیوتر گفت: منوس! 😹",
    "چرا برنامه‌نویس‌ها عاشق قهوه‌ان؟ چون coffee رو با class constructor یکی می‌دونن! ☕",
    "بهترین شوخی برنامه‌نویسی؟ null pointer exception! 😂",
    "چرا تابع main همیشه اول میاد؟ چون مامانش گفته! 😄",
    "تفاوت بین یه برنامه‌نویس و یه هنرمند؟ یکی باگ می‌نویسه، یکی نقاشی! 🎨"
]

QUOTES = [
    "همیشه به فکر فردا باش!", "موفقیت یعنی بلند شدن دوباره!", "کد بزن و لذت ببر!",
    "زندگی مثل یه جعبه شکلاته!", "بهترین زمان برای شروع، الان است!",
    "هیچ چیز غیرممکن نیست، فقط زمان می‌بره! ⏳",
    "با امید و تلاش، قله‌ها فتح می‌شوند! 🏔️",
    "لبخند بزن، دنیا لبخند می‌زند! 😊",
    "هر روز یه فرصت تازه برای شروع دوباره است! 🌅",
    "موفقیت یعنی بلند شدن هر بار که زمین می‌خوری! 💪"
]

GREETINGS = {
    "سلام": "سلام! 👋", "خوبی": "خوبم ممنون! تو چطوری؟", "چطوری": "خوبم، ممنون!",
    "مرسی": "خواهش می‌کنم! 🤗", "خداحافظ": "خداحافظ! 👋", "صبح بخیر": "صبح بخیر! ☀️",
    "شب بخیر": "شب بخیر! 🌙", "خوش اومدی": "خوش اومدی! ✨", "چه خبر": "سلامت باشی! 😊",
    "خوشحالم": "منم خوشحالم! 😄", "علیک": "علیک السلام! 🙏", "درود": "درود بر تو! 🌹",
    "ایول": "ایول داش! 🔥", "دمت گرم": "دمت گرم داداش! ❤️", "چاکرم": "چاکرم استاد! 🙌",
    "سپاس": "سپاسگزارم! 🌺", "متشکرم": "خواهش می‌کنم! 🌸", "بله": "چشم! ✅",
    "نه": "نه جان؟ 😅", "باشه": "باشه عزیزم! 😊"
}

guess_games = {}

async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def is_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def log_activity(user_id: int, action: str, details: str = ""):
    try:
        activities_col.insert_one({
            "user_id": user_id,
            "action": action,
            "details": details,
            "timestamp": datetime.now()
        })
        users_col.update_one({"_id": user_id}, {"$set": {"last_activity": datetime.now()}})
    except:
        pass

async def ask_ai_openrouter(query: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    data = {"model": "google/gemini-2.0-flash-lite-001", "messages": [{"role": "user", "content": query}], "max_tokens": 500, "temperature": 0.7}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=data, timeout=15) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result['choices'][0]['message']['content']
                return None
    except:
        return None

async def ask_ai_nexra(query: str) -> str:
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.nexra.aryan.ir/v1/chat/gpt?text={query}"
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success" and data.get("data"):
                        return data["data"].strip()
        return None
    except:
        return None

async def ask_ai(query: str) -> str:
    result = await ask_ai_openrouter(query)
    if result: return result
    result = await ask_ai_nexra(query)
    if result: return result
    return None

def get_tehran_time():
    return datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)

# ======== منوها ========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 دانلود یوتیوب", callback_data="youtube")],
        [InlineKeyboardButton(text="🎮 بازی و سرگرمی", callback_data="game")],
        [InlineKeyboardButton(text="💳 کیف پول", callback_data="wallet"),
         InlineKeyboardButton(text="💰 شارژ حساب", callback_data="charge")],
        [InlineKeyboardButton(text="🛠 پشتیبانی", callback_data="support"),
         InlineKeyboardButton(text="👤 حساب کاربری", callback_data="profile_user")],
        [InlineKeyboardButton(text="⚙️ پنل ادمین", callback_data="admin_panel")]
    ])

def game_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 تاس", callback_data="dice"),
         InlineKeyboardButton(text="🎯 دارت", callback_data="dart")],
        [InlineKeyboardButton(text="🪨 سنگ‌کاغذ‌قیچی", callback_data="rps")],
        [InlineKeyboardButton(text="🔢 حدس عدد", callback_data="guess_game")],
        [InlineKeyboardButton(text="🪙 شیر یا خط", callback_data="coin_flip")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_main")]
    ])

def rps_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪨 سنگ", callback_data="rps_stone")],
        [InlineKeyboardButton(text="📄 کاغذ", callback_data="rps_paper")],
        [InlineKeyboardButton(text="✂️ قیچی", callback_data="rps_scissors")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_game")]
    ])

def coin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 شیر", callback_data="coin_heads")],
        [InlineKeyboardButton(text="🪙 خط", callback_data="coin_tails")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_game")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار کلی", callback_data="stats")],
        [InlineKeyboardButton(text="👥 لیست کاربران", callback_data="list_users")],
        [InlineKeyboardButton(text="🔍 جستجوی کاربر", callback_data="search_user")],
        [InlineKeyboardButton(text="📋 فعالیت‌های کاربر", callback_data="user_activities")],
        [InlineKeyboardButton(text="📤 شروع آپلود گروه جدید", callback_data="upload_file")],
        [InlineKeyboardButton(text="📤 انتشار گروه و دریافت لینک", callback_data="publish_group")],
        [InlineKeyboardButton(text="📋 مدیریت گروه‌ها", callback_data="manage_groups")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_main")]
    ])

def channel_check_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ عضویت داشتم", callback_data="check_join")]
    ])

# ======== ارسال فایل‌های گروه ========
async def send_group_files(message: types.Message, group_uuid: str):
    files = list(files_col.find({"group_uuid": group_uuid}).sort("uploaded_at", 1))
    if not files:
        await message.answer("❌ این گروه فایلی ندارد.")
        return
    await message.answer(f"📂 **{len(files)} فایل** یافت شد. در حال ارسال...")
    for f in files:
        file_id = f["file_id"]
        file_type = f["type"]
        caption = f.get("caption", DEFAULT_CAPTION)
        try:
            if file_type == "photo":
                await message.answer_photo(file_id, caption=caption)
            elif file_type == "video":
                await message.answer_video(file_id, caption=caption)
            else:
                await message.answer_document(file_id, caption=caption)
            await asyncio.sleep(0.5)
        except Exception as e:
            logging.error(f"خطا در ارسال فایل: {e}")
    await message.answer("✅ **همه فایل‌های این گروه ارسال شدند!**")

# ======== دستور /start ========
@dp.message(Command("test"))
async def test_command(message: types.Message):
    await message.answer("✅ کد جدید با موفقیت اجرا شد! 🎉")

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

    if message.text and message.text.startswith("/start group_"):
        group_uuid = message.text.split("_", 2)[1]
        if not await is_member(user_id):
            await message.answer(f"👋 سلام {name}!\nبرای دریافت فایل‌ها اول عضو کانال شو:", reply_markup=channel_check_menu())
            return
        await send_group_files(message, group_uuid)
        return

    if message.text and message.text.startswith("/start file_"):
        file_uuid = message.text.split("_", 2)[1]
        file_data = files_col.find_one({"uuid": file_uuid})
        if file_data:
            if not await is_member(user_id):
                await message.answer(f"👋 سلام {name}!\nعضو کانال شو:", reply_markup=channel_check_menu())
                return
            file_id = file_data["file_id"]
            file_type = file_data["type"]
            caption = file_data.get("caption", DEFAULT_CAPTION)
            if file_type == "photo":
                await message.answer_photo(file_id, caption=caption)
            elif file_type == "video":
                await message.answer_video(file_id, caption=caption)
            else:
                await message.answer_document(file_id, caption=caption)
            return
        else:
            await message.answer("❌ فایل مورد نظر یافت نشد.")
            return

    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({
            "_id": user_id,
            "name": name,
            "joined_at": datetime.now(),
            "last_activity": datetime.now(),
            "is_banned": False
        })

    await log_activity(user_id, "start", "استارت ربات")

    if not await is_member(user_id):
        await message.answer(f"👋 سلام {name}!\nعضو کانال شو:", reply_markup=channel_check_menu())
        return

    await message.answer(f"🚀 سلام {name}!\nبه ربات خوش آمدی:", reply_markup=main_menu())

# ======== بررسی عضویت ========
@dp.callback_query(lambda c: c.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_member(user_id):
        await callback.message.edit_text("✅ ممنون! حالا می‌تونی از ربات استفاده کنی.")
        await callback.message.answer("🚀 منوی اصلی:", reply_markup=main_menu())
    else:
        await callback.answer("❌ هنوز عضو کانال نشدی!", show_alert=True)

# ======== دانلود یوتیوب ========
@dp.callback_query(lambda c: c.data == "youtube")
async def youtube(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🎬 لینک ویدیو یوتیوب را بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and ("youtube.com" in msg.text or "youtu.be" in msg.text))
async def get_youtube(message: types.Message):
    if not await is_member(message.from_user.id):
        await message.answer("❌ اول عضو کانال بشو!")
        return
    try:
        yt = YouTube(message.text)
        stream = yt.streams.get_highest_resolution()
        if stream:
            await message.answer("⏬ در حال دانلود...")
            file_path = f"temp_{uuid.uuid4()}.mp4"
            stream.download(filename=file_path)
            with open(file_path, "rb") as video:
                await message.answer_video(video, caption=f"🎬 {yt.title}")
            os.remove(file_path)
            await log_activity(message.from_user.id, "youtube_download", yt.title)
        else:
            await message.answer("❌ خطا!")
    except Exception as e:
        logging.error(f"YouTube error: {e}")
        await message.answer("❌ خطا در دانلود!")

# ======== callbackهای منوی اصلی و بازی‌ها ========
@dp.callback_query(lambda c: c.data == "wallet")
async def wallet_callback(callback: types.CallbackQuery):
    await callback.message.answer("💳 کیف پول شما:\nموجودی: ۰ تومان\n\nاین بخش به زودی تکمیل می‌شود.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "charge")
async def charge_callback(callback: types.CallbackQuery):
    await callback.message.answer("💰 شارژ حساب:\n۱. شارژ ۱۰,۰۰۰ تومان\n۲. شارژ ۵۰,۰۰۰ تومان\n۳. شارژ ۱۰۰,۰۰۰ تومان")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback: types.CallbackQuery):
    await callback.message.answer("🛠 پشتیبانی:\n@AdminUsername")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "profile_user")
async def profile_user_callback(callback: types.CallbackQuery):
    user = callback.from_user
    await callback.message.answer(f"👤 نام: {user.full_name}\n🆔 آیدی: {user.id}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "game")
async def game(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🎮 یک بازی انتخاب کن:", reply_markup=game_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "dice")
async def dice(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer_dice(emoji="🎲")
    await log_activity(callback.from_user.id, "dice", "بازی تاس")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "dart")
async def dart(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer_dice(emoji="🎯")
    await log_activity(callback.from_user.id, "dart", "بازی دارت")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "rps")
async def rps(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🪨 یکی رو انتخاب کن:", reply_markup=rps_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["rps_stone", "rps_paper", "rps_scissors"])
async def rps_play(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    choices = {"rps_stone": {"name": "🪨 سنگ", "beats": "rps_scissors"}, "rps_paper": {"name": "📄 کاغذ", "beats": "rps_stone"}, "rps_scissors": {"name": "✂️ قیچی", "beats": "rps_paper"}}
    user_choice = callback.data
    bot_choice = random.choice(list(choices.keys()))
    user_emoji = choices[user_choice]["name"]
    bot_emoji = choices[bot_choice]["name"]
    if user_choice == bot_choice:
        result = "🤝 مساوی!"
    elif choices[user_choice]["beats"] == bot_choice:
        result = "🎉 بردی!"
    else:
        result = "😢 باختی!"
    await callback.message.answer(f"تو: {user_emoji}\nربات: {bot_emoji}\n\n{result}")
    await log_activity(callback.from_user.id, "rps", f"نتیجه: {result}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "guess_game")
async def guess_game(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    number = random.randint(1, 20)
    guess_games[callback.from_user.id] = {"number": number, "attempts": 0}
    await callback.message.answer("🔢 من یک عدد بین ۱ تا ۲۰ انتخاب کردم!\nعدد را بفرستید.\n/cancel برای لغو")
    await log_activity(callback.from_user.id, "guess_game_start")
    await callback.answer()

@dp.message(Command("cancel"))
async def cancel_guess(message: types.Message):
    user_id = message.from_user.id
    if user_id in guess_games:
        del guess_games[user_id]
        await message.answer("❌ بازی لغو شد.")
    else:
        await message.answer("⚠️ بازی فعالی ندارید.")

@dp.message(lambda msg: msg.text and msg.text.isdigit())
async def handle_guess_number(message: types.Message):
    user_id = message.from_user.id
    if user_id not in guess_games:
        return
    if not await is_member(user_id):
        await message.answer("❌ اول عضو کانال شو!")
        del guess_games[user_id]
        return
    guess = int(message.text)
    game = guess_games[user_id]
    game["attempts"] += 1
    target = game["number"]
    if guess == target:
        await message.answer(f"🎉 تبریک! عدد {target} بود.\nتعداد تلاش: {game['attempts']}")
        await log_activity(user_id, "guess_game_win")
        del guess_games[user_id]
    elif guess < target:
        await message.answer("📈 بیشتر بزن")
    else:
        await message.answer("📉 کمتر بزن")

@dp.callback_query(lambda c: c.data == "coin_flip")
async def coin_flip(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🪙 شیر یا خط؟", reply_markup=coin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["coin_heads", "coin_tails"])
async def coin_play(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    user_choice = "شیر" if callback.data == "coin_heads" else "خط"
    bot_choice = random.choice(["شیر", "خط"])
    result = "🎉 بردی!" if user_choice == bot_choice else "😢 باختی!"
    await callback.message.answer(f"تو: {user_choice}\nربات: {bot_choice}\n\n{result}")
    await log_activity(callback.from_user.id, "coin_flip", result)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.answer("🔙 منوی اصلی:", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_game")
async def back_game(callback: types.CallbackQuery):
    await callback.message.answer("🔙 منوی بازی:", reply_markup=game_menu())
    await callback.answer()

# ======== پنل ادمین ========
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("⚙️ پنل ادمین:", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats")
async def stats_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    total_users = users_col.count_documents({})
    total_files = files_col.count_documents({})
    total_groups = groups_col.count_documents({})
    banned = users_col.count_documents({"is_banned": True})
    active = activities_col.count_documents({"timestamp": {"$gte": datetime.now() - timedelta(days=1)}})
    await callback.message.answer(f"📊 آمار:\nکاربران: {total_users}\nفایل‌ها: {total_files}\nگروه‌ها: {total_groups}\nبن: {banned}\nفعال امروز: {active}")
    await callback.answer()

# ======== جستجوی کاربر (اصلاح شده) ========
@dp.message(lambda msg: msg.from_user.id == ADMIN_ID and msg.text and not msg.text.startswith('/'))
async def handle_search_user(message: types.Message):
    query = message.text.strip()
    if query.isdigit():
        user = users_col.find_one({"_id": int(query)})
        if user:
            await message.answer(f"✅ پیدا شد!\n🆔 {user['_id']}\nنام: {user.get('name')}")
            return
    await message.answer("❌ کاربر پیدا نشد.")

# ======== آپلود فایل ========
@dp.callback_query(lambda c: c.data == "upload_file")
async def upload_file_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    groups_col.update_many({"admin_id": callback.from_user.id, "is_active": True}, {"$set": {"is_active": False}})
    group_uuid = str(uuid.uuid4())[:8]
    groups_col.insert_one({
        "group_uuid": group_uuid,
        "admin_id": callback.from_user.id,
        "created_at": datetime.now(),
        "is_active": True,
        "file_count": 0
    })
    await callback.message.answer(f"📤 گروه جدید ساخته شد!\nشناسه: `{group_uuid}`\nفایل بفرست.", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "publish_group")
async def publish_group_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    group = groups_col.find_one({"admin_id": callback.from_user.id, "is_active": True})
    if not group or group.get("file_count", 0) == 0:
        await callback.answer("❌ گروه فعال با فایل وجود ندارد.", show_alert=True)
        return
    group_uuid = group["group_uuid"]
    groups_col.update_one({"group_uuid": group_uuid}, {"$set": {"is_active": False}})
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=group_{group_uuid}"
    await callback.message.answer(f"✅ منتشر شد!\nلینک: <code>{link}</code>", parse_mode="HTML")
    await callback.answer()

@dp.message(lambda msg: msg.document or msg.photo or msg.video)
async def handle_file_upload(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    group = groups_col.find_one({"admin_id": message.from_user.id, "is_active": True})
    if not group:
        await message.answer("❌ اول گروه جدید بساز.")
        return
    group_uuid = group["group_uuid"]
    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name or "فایل"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        file_name = "عکس"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = "ویدئو"
    else:
        return
    file_uuid = str(uuid.uuid4())[:8]
    caption = message.caption or DEFAULT_CAPTION
    files_col.insert_one({
        "uuid": file_uuid,
        "group_uuid": group_uuid,
        "file_id": file_id,
        "type": file_type,
        "name": file_name,
        "caption": caption,
        "uploaded_at": datetime.now()
    })
    groups_col.update_one({"group_uuid": group_uuid}, {"$inc": {"file_count": 1}})
    await message.answer(f"✅ فایل {file_name} اضافه شد.")
    
# ======== چت اصلی ========
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    text = (message.text or "").strip().lower()

    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({
            "_id": user_id,
            "name": message.from_user.first_name or "کاربر",
            "joined_at": datetime.now(),
            "last_activity": datetime.now(),
            "is_banned": False
        })

    if not await is_member(user_id):
        await message.answer("❌ اول عضو کانال شو:", reply_markup=channel_check_menu())
        return

    for key, response in GREETINGS.items():
        if key in text:
            await message.answer(response)
            await log_activity(user_id, "greeting", text)
            return

    ai_response = await ask_ai(text)
    if ai_response:
        await message.answer(ai_response)
        await log_activity(user_id, "ai_chat", text)
        return

    await message.answer(random.choice(FUNNY_FALLBACKS))
    await log_activity(user_id, "fallback", text)

# ======== وب و اجرا ========
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

async def main():
    await start_web()
    logging.info("🤖 ربات شروع شد")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
