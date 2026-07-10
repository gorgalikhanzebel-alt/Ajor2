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

# ======== ذخیره‌سازی موقت بازی حدس عدد ========
guess_games = {}  # {user_id: {"number": int, "attempts": int}}

# ======== جملات خنده‌دار ========
FUNNY_FALLBACKS = [
    "چی میگی بچه خوشگل؟ 😏",
    "سیک تو بزن تا سیکمو نزدن 😂",
    "نمیفهمم حاجی چی میگی",
    "این چرت و پرتا چیه میگی مردک 🤔",
    "به نظرم ط ی چیزی زدی اینارو میگی"
]

# ======== جوک‌ها (۱۰ مورد) ========
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

# ======== نقل قول‌ها (۱۰ مورد) ========
QUOTES = [
    "همیشه به فکر فردا باش!",
    "موفقیت یعنی بلند شدن دوباره!",
    "کد بزن و لذت ببر!",
    "زندگی مثل یه جعبه شکلاته!",
    "بهترین زمان برای شروع، الان است!",
    "هیچ چیز غیرممکن نیست، فقط زمان می‌بره! ⏳",
    "با امید و تلاش، قله‌ها فتح می‌شوند! 🏔️",
    "لبخند بزن، دنیا لبخند می‌زند! 😊",
    "هر روز یه فرصت تازه برای شروع دوباره است! 🌅",
    "موفقیت یعنی بلند شدن هر بار که زمین می‌خوری! 💪"
]

# ======== ۲۰ کلمه احوال‌پرسی ========
GREETINGS = {
    "سلام": "سلام! 👋",
    "خوبی": "خوبم ممنون! تو چطوری؟",
    "چطوری": "خوبم، ممنون!",
    "مرسی": "خواهش می‌کنم! 🤗",
    "خداحافظ": "خداحافظ! 👋",
    "صبح بخیر": "صبح بخیر! ☀️",
    "شب بخیر": "شب بخیر! 🌙",
    "خوش اومدی": "خوش اومدی! ✨",
    "چه خبر": "سلامت باشی! 😊",
    "خوشحالم": "منم خوشحالم! 😄",
    "علیک": "علیک السلام! 🙏",
    "درود": "درود بر تو! 🌹",
    "ایول": "ایول داش! 🔥",
    "دمت گرم": "دمت گرم داداش! ❤️",
    "چاکرم": "چاکرم استاد! 🙌",
    "سپاس": "سپاسگزارم! 🌺",
    "متشکرم": "خواهش می‌کنم! 🌸",
    "بله": "چشم! ✅",
    "نه": "نه جان؟ 😅",
    "باشه": "باشه عزیزم! 😊"
}

# ======== توابع کمکی ========
async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def is_banned(user_id: int) -> bool:
    return banned_col.find_one({"_id": user_id}) is not None

async def is_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def ask_ai_openrouter(query: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "google/gemini-2.0-flash-lite-001",
        "messages": [{"role": "user", "content": query}],
        "max_tokens": 500,
        "temperature": 0.7,
    }
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
    if result:
        return result
    result = await ask_ai_nexra(query)
    if result:
        return result
    return None

def get_tehran_time():
    """دریافت زمان تهران (UTC+3:30)"""
    utc = datetime.now(timezone.utc)
    tehran_offset = timedelta(hours=3, minutes=30)
    tehran_time = utc + tehran_offset
    return tehran_time

def format_user_info(user, user_data=None):
    name = user.full_name if user else user_data.get("name", "نامشخص")
    user_id = user.id if user else user_data.get("_id", "نامشخص")
    joined_at = user_data.get("joined_at", "نامشخص") if user_data else "نامشخص"
    if isinstance(joined_at, datetime):
        joined_at = joined_at.strftime("%Y-%m-%d %H:%M")
    return f"👤 نام: {name}\n🆔 آیدی: {user_id}\n📅 تاریخ عضویت: {joined_at}"

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
        [InlineKeyboardButton(text="📊 آمار کامل", callback_data="full_stats")],
        [InlineKeyboardButton(text="📋 لیست کاربران", callback_data="user_list")],
        [InlineKeyboardButton(text="📢 ارسال همگانی", callback_data="broadcast")],
        [InlineKeyboardButton(text="🔍 جستجوی کاربر", callback_data="search_user")],
        [InlineKeyboardButton(text="🚫 مدیریت مسدودها", callback_data="ban_management")],
        [InlineKeyboardButton(text="⚙️ مدیریت گروه", callback_data="group_manage")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_main")]
    ])

def group_manage_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 قفل گروه", callback_data="lock_group")],
        [InlineKeyboardButton(text="🔓 باز کردن گروه", callback_data="unlock_group")],
        [InlineKeyboardButton(text="🚫 بن کاربر", callback_data="ban_user")],
        [InlineKeyboardButton(text="✅ رفع بن", callback_data="unban_user")],
        [InlineKeyboardButton(text="🧹 پاک کردن پیام‌ها", callback_data="clear_messages")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="admin_panel")]
    ])

def channel_check_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ عضویت داشتم", callback_data="check_join")]
    ])

# ============================================
# ======== دستور /start ========
# ============================================
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

    if await is_banned(user_id):
        await message.answer("🚫 شما توسط ادمین مسدود شده‌اید!")
        return

    if message.text and message.text.startswith("/start file_"):
        file_uuid = message.text.split("_")[1]
        file_data = files_col.find_one({"uuid": file_uuid})
        if file_data:
            if not await is_member(user_id):
                await message.answer(
                    f"👋 سلام {name}!\n"
                    "برای دریافت این فایل، لطفاً اول عضو کانال ما بشو:",
                    reply_markup=channel_check_menu()
                )
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
        users_col.insert_one({"_id": user_id, "name": name, "joined_at": datetime.now()})

    if not await is_member(user_id):
        await message.answer(
            f"👋 سلام {name}!\n"
            "برای استفاده از ربات، لطفاً اول عضو کانال ما بشو:",
            reply_markup=channel_check_menu()
        )
        return

    await message.answer(
        f"🚀 سلام {name}!\n"
        "به ربات خوش آمدی. از دکمه‌های زیر استفاده کن:",
        reply_markup=main_menu()
    )

# ============================================
# ======== بررسی مجدد عضویت ========
# ============================================
@dp.callback_query(lambda c: c.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_banned(user_id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if await is_member(user_id):
        await callback.message.edit_text("✅ ممنون! حالا می‌تونی از ربات استفاده کنی.")
        await callback.message.answer("🚀 منوی اصلی:", reply_markup=main_menu())
    else:
        await callback.answer("❌ هنوز عضو کانال نشدی! اول عضو شو.", show_alert=True)

# ============================================
# ======== دانلود یوتیوب ========
# ============================================
@dp.callback_query(lambda c: c.data == "youtube")
async def youtube(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🎬 لینک ویدیو یوتیوب را بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and ("youtube.com" in msg.text or "youtu.be" in msg.text))
async def get_youtube(message: types.Message):
    if await is_banned(message.from_user.id):
        await message.answer("🚫 شما مسدود هستید!")
        return
    if not await is_member(message.from_user.id):
        await message.answer("❌ اول عضو کانال بشو!")
        return
    try:
        yt = YouTube(message.text)
        stream = yt.streams.get_highest_resolution()
        if stream:
            await message.answer_video(stream.url, caption=f"🎬 {yt.title}")
        else:
            await message.answer("❌ خطا!")
    except:
        await message.answer("❌ خطا! لینک معتبر نیست.")

# ============================================
# ======== دکمه‌های منوی اصلی ========
# ============================================
@dp.callback_query(lambda c: c.data == "wallet")
async def wallet_callback(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    await callback.message.answer("💳 کیف پول شما:\nموجودی: ۰ تومان\n\nاین بخش به زودی تکمیل می‌شود.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "charge")
async def charge_callback(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    await callback.message.answer("💰 شارژ حساب:\n۱. شارژ ۱۰,۰۰۰ تومان\n۲. شارژ ۵۰,۰۰۰ تومان\n۳. شارژ ۱۰۰,۰۰۰ تومان\n\nلطفاً مبلغ مورد نظر را وارد کنید.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    await callback.message.answer("🛠 پشتیبانی:\nبرای ارتباط با ادمین، به آیدی زیر پیام دهید:\n@AdminUsername\n\nساعات پاسخگویی: ۲۴/۷")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "profile_user")
async def profile_user_callback(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    user = callback.from_user
    await callback.message.answer(f"👤 نام: {user.full_name}\n🆔 آیدی: {user.id}\n📱 شماره: ثبت نشده")
    await callback.answer()

# ============================================
# ======== بازی‌ها ========
# ============================================
@dp.callback_query(lambda c: c.data == "game")
async def game(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🎮 یک بازی انتخاب کن:", reply_markup=game_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "dice")
async def dice(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer_dice(emoji="🎲")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "dart")
async def dart(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer_dice(emoji="🎯")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "rps")
async def rps(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🪨 یکی رو انتخاب کن:", reply_markup=rps_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["rps_stone", "rps_paper", "rps_scissors"])
async def rps_play(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    choices = {
        "rps_stone": {"name": "🪨 سنگ", "beats": "rps_scissors"},
        "rps_paper": {"name": "📄 کاغذ", "beats": "rps_stone"},
        "rps_scissors": {"name": "✂️ قیچی", "beats": "rps_paper"}
    }
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
    await callback.answer()

# ======== بازی حدس عدد (اصلاح‌شده) ========
@dp.callback_query(lambda c: c.data == "guess_game")
async def guess_game(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    
    user_id = callback.from_user.id
    number = random.randint(1, 20)
    guess_games[user_id] = {"number": number, "attempts": 0}
    
    await callback.message.answer(
        f"🔢 من یک عدد بین ۱ تا ۲۰ انتخاب کردم!\n"
        f"عدد مورد نظر را بفرستید تا حدس بزنید.\n"
        f"برای انصراف، دستور /cancel رو بفرستید."
    )
    await callback.answer()

@dp.message(Command("cancel"))
async def cancel_guess(message: types.Message):
    user_id = message.from_user.id
    if user_id in guess_games:
        del guess_games[user_id]
        await message.answer("❌ بازی حدس عدد لغو شد.")
    else:
        await message.answer("⚠️ شما در حال حاضر هیچ بازی حدس عددی ندارید.")

# ======== پردازش حدس عدد ========
@dp.message(lambda msg: msg.text and msg.text.isdigit())
async def handle_guess_number(message: types.Message):
    user_id = message.from_user.id
    
    # اگر کاربر در حالت حدس عدد نباشد، پیام را نادیده بگیر (برای جلوگیری از تداخل)
    if user_id not in guess_games:
        return
    
    # بررسی مسدود بودن و عضویت
    if await is_banned(user_id):
        await message.answer("🚫 شما مسدود هستید!")
        if user_id in guess_games:
            del guess_games[user_id]
        return
    if not await is_member(user_id):
        await message.answer("❌ اول عضو کانال بشو!")
        if user_id in guess_games:
            del guess_games[user_id]
        return
    
    guess = int(message.text)
    game = guess_games[user_id]
    game["attempts"] += 1
    target = game["number"]
    
    if guess == target:
        await message.answer(
            f"🎉 **تبریک! درست حدس زدی!**\n"
            f"عدد {target} بود.\n"
            f"تعداد تلاش‌های شما: {game['attempts']}"
        )
        del guess_games[user_id]
    elif guess < target:
        await message.answer(f"📈 بیشتر از {guess} است. دوباره تلاش کن.")
    else:
        await message.answer(f"📉 کمتر از {guess} است. دوباره تلاش کن.")

# ======== شیر یا خط ========
@dp.callback_query(lambda c: c.data == "coin_flip")
async def coin_flip(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🪙 شیر یا خط؟ انتخاب کن:", reply_markup=coin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["coin_heads", "coin_tails"])
async def coin_play(callback: types.CallbackQuery):
    if await is_banned(callback.from_user.id):
        await callback.answer("🚫 شما مسدود هستید!", show_alert=True)
        return
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    user_choice = "شیر" if callback.data == "coin_heads" else "خط"
    bot_choice = random.choice(["شیر", "خط"])
    if user_choice == bot_choice:
        result = "🎉 بردی!"
    else:
        result = "😢 باختی!"
    await callback.message.answer(f"تو: {user_choice}\nربات: {bot_choice}\n\n{result}")
    await callback.answer()

# ======== برگشت‌ها ========
@dp.callback_query(lambda c: c.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.answer("🔙 منوی اصلی:", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_game")
async def back_game(callback: types.CallbackQuery):
    await callback.message.answer("🔙 منوی بازی:", reply_markup=game_menu())
    await callback.answer()

# ============================================
# ======== پنل ادمین کامل (فقط برای ادمین) ========
# ============================================
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("⚙️ پنل ادمین حرفه‌ای:", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "full_stats")
async def full_stats(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    total = users_col.count_documents({})
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today = users_col.count_documents({"joined_at": {"$gte": today_start}})
    banned_count = banned_col.count_documents({})
    files_count = files_col.count_documents({})
    
    stats_text = (
        f"📊 **آمار کامل ربات**\n\n"
        f"👥 کل کاربران: {total}\n"
        f"📅 کاربران جدید امروز: {today}\n"
        f"🚫 کاربران مسدود: {banned_count}\n"
        f"📁 فایل‌های آپلود شده: {files_count}\n"
        f"📆 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    await callback.message.answer(stats_text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "user_list")
async def user_list(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    users = list(users_col.find().sort("joined_at", -1).limit(20))
    if not users:
        await callback.message.answer("📭 هنوز کاربری ثبت نشده.")
        await callback.answer()
        return
    
    text = "📋 **لیست ۲۰ کاربر اخیر**\n\n"
    for i, user in enumerate(users, 1):
        name = user.get("name", "نامشخص")
        uid = user.get("_id", "نامشخص")
        joined = user.get("joined_at", "")
        if isinstance(joined, datetime):
            joined = joined.strftime("%Y-%m-%d")
        text += f"{i}. {name} (ID: {uid}) - {joined}\n"
        if len(text) > 3500:
            text += "...\nو کاربران بیشتر"
            break
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "broadcast")
async def broadcast(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("📢 لطفاً پیام همگانی را بنویسید (به این پیام ریپلی کنید):")
    await callback.answer()

@dp.message(lambda msg: msg.reply_to_message and msg.reply_to_message.text and "پیام همگانی" in msg.reply_to_message.text)
async def handle_broadcast(message: types.Message):
    if not await is_admin(message.from_user.id):
        return
    text = message.text
    users = users_col.find()
    sent = 0
    failed = 0
    for user in users:
        try:
            await bot.send_message(user["_id"], text)
            sent += 1
        except:
            failed += 1
    await message.answer(f"✅ پیام به {sent} کاربر ارسال شد.\n❌ {failed} کاربر دریافت نکردند.")

@dp.callback_query(lambda c: c.data == "search_user")
async def search_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("🔍 آیدی عددی یا نام کاربر را برای جستجو بفرستید:")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and await is_admin(msg.from_user.id))
async def search_user_by_id(message: types.Message):
    user_id = int(message.text)
    user_data = users_col.find_one({"_id": user_id})
    if user_data:
        text = format_user_info(message.from_user, user_data)
        await message.answer(text)
    else:
        await message.answer("❌ کاربری با این آیدی یافت نشد.")

@dp.message(lambda msg: msg.text and not msg.text.startswith("/") and not msg.text.isdigit() and await is_admin(msg.from_user.id))
async def search_user_by_name(message: types.Message):
    name = message.text.strip()
    users = users_col.find({"name": {"$regex": name, "$options": "i"}}).limit(10)
    results = list(users)
    if results:
        text = f"🔍 نتایج جستجو برای '{name}':\n\n"
        for user in results:
            text += f"👤 {user.get('name', 'نامشخص')} (ID: {user['_id']})\n"
        await message.answer(text)
    else:
        await message.answer(f"❌ کاربری با نام '{name}' یافت نشد.")

@dp.callback_query(lambda c: c.data == "ban_management")
async def ban_management(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    banned = list(banned_col.find())
    if banned:
        text = "🚫 **لیست کاربران مسدود:**\n\n"
        for user in banned[:20]:
            text += f"ID: {user['_id']} - {user.get('reason', 'بدون دلیل')}\n"
        await callback.message.answer(text, parse_mode="Markdown")
    else:
        await callback.message.answer("✅ هیچ کاربری مسدود نیست.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "ban_user")
async def ban_user_admin(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("🚫 آیدی عددی کاربر را برای مسدودسازی بفرستید:")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and await is_admin(msg.from_user.id))
async def ban_user_cmd(message: types.Message):
    user_id = int(message.text)
    if user_id == ADMIN_ID:
        await message.answer("❌ نمی‌توانید خودتان را مسدود کنید!")
        return
    if banned_col.find_one({"_id": user_id}):
        await message.answer(f"⚠️ کاربر {user_id} قبلاً مسدود شده است.")
        return
    banned_col.insert_one({"_id": user_id, "reason": "مسدود توسط ادمین", "banned_at": datetime.now()})
    await message.answer(f"✅ کاربر {user_id} مسدود شد.")
    try:
        await bot.send_message(user_id, "🚫 شما توسط ادمین ربات مسدود شده‌اید!")
    except:
        pass

@dp.callback_query(lambda c: c.data == "unban_user")
async def unban_user_admin(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("✅ آیدی عددی کاربر را برای رفع مسدودیت بفرستید:")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and await is_admin(msg.from_user.id))
async def unban_user_cmd(message: types.Message):
    user_id = int(message.text)
    if banned_col.delete_one({"_id": user_id}):
        await message.answer(f"✅ مسدودیت کاربر {user_id} رفع شد.")
    else:
        await message.answer(f"❌ کاربر {user_id} مسدود نیست.")

# ======== مدیریت گروه ========
@dp.callback_query(lambda c: c.data == "group_manage")
async def group_manage(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("⚙️ مدیریت گروه:", reply_markup=group_manage_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "lock_group")
async def lock_group(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await bot.set_chat_permissions(callback.message.chat.id, ChatPermissions(can_send_messages=False))
    await callback.message.answer("🔒 گروه قفل شد.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "unlock_group")
async def unlock_group(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await bot.set_chat_permissions(callback.message.chat.id, ChatPermissions(can_send_messages=True))
    await callback.message.answer("🔓 گروه باز شد.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "clear_messages")
async def clear_messages(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("🧹 تعداد پیام‌ها را بفرستید (مثلاً 10):")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and await is_admin(msg.from_user.id))
async def clear_cmd(message: types.Message):
    count = int(message.text)
    if count > 100:
        await message.answer("❌ حداکثر ۱۰۰ پیام.")
        return
    deleted = 0
    async for msg in bot.get_chat_history(message.chat.id, limit=count):
        if msg.message_id != message.message_id:
            await msg.delete()
            deleted += 1
    await message.answer(f"✅ {deleted} پیام پاک شد.")

# ======== آپلود فایل ========
@dp.callback_query(lambda c: c.data == "upload_file")
async def upload_file_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("📤 لطفاً فایل (عکس، ویدئو، سند) را ارسال کنید.\nبرای کپشن دلخواه، هنگام ارسال فایل، در قسمت کپشن بنویسید.")
    await callback.answer()

@dp.message(Command("upload"))
async def upload_file_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین می‌تواند فایل آپلود کند!")
        return
    await message.answer("📤 لطفاً فایل (عکس، ویدئو، سند) را ارسال کنید.\nبرای کپشن دلخواه، هنگام ارسال فایل، در قسمت کپشن بنویسید.")

@dp.message(lambda msg: msg.document or msg.photo or msg.video)
async def handle_file_upload(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین می‌تواند فایل آپلود کند!")
        return

    if message.document:
        file_id = message.document.file_id
        file_type = "document"
        file_name = message.document.file_name
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        file_name = "عکس"
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        file_name = "ویدئو"
    else:
        await message.answer("❌ نوع فایل پشتیبانی نمی‌شود.")
        return

    file_uuid = str(uuid.uuid4())[:8]
    caption = message.caption if message.caption else DEFAULT_CAPTION

    files_col.insert_one({
        "uuid": file_uuid,
        "file_id": file_id,
        "type": file_type,
        "name": file_name,
        "caption": caption,
        "uploaded_at": datetime.now()
    })

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=file_{file_uuid}"

    await message.answer(
        f"✅ فایل با موفقیت آپلود شد!\n\n"
        f"🔗 لینک اختصاصی:\n<code>{link}</code>\n\n"
        f"📌 کپشن فایل:\n{caption}\n\n"
        f"⚠️ کاربران ابتدا باید عضو کانال شوند تا فایل را دریافت کنند.",
        parse_mode="HTML"
    )

# ============================================
# ======== دستورات اصلاح‌شده ========
# ============================================

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 لیست دستورات:\n"
        "/start - شروع و منوی اصلی\n"
        "/help - نمایش راهنما\n"
        "/profile - پروفایل شما\n"
        "/time - ساعت و تاریخ (به وقت تهران)\n"
        "/id - نمایش آیدی عددی شما\n"
        "/joke - جوک تصادفی\n"
        "/quote - نقل قول انگیزشی\n"
        "/ping - بررسی وضعیت ربات\n"
        "/upload - آپلود فایل (فقط ادمین)\n"
        "/admin - پنل ادمین\n"
        "/cancel - لغو بازی حدس عدد"
    )

@dp.message(Command("profile"))
async def profile(message: types.Message):
    await message.answer(f"👤 نام: {message.from_user.full_name}\n🆔 آیدی: {message.from_user.id}")

# ======== دستور /time با زمان تهران ========
@dp.message(Command("time"))
async def time_command(message: types.Message):
    tehran_time = get_tehran_time()
    persian_weekdays = {
        0: "دوشنبه", 1: "سه‌شنبه", 2: "چهارشنبه",
        3: "پنج‌شنبه", 4: "جمعه", 5: "شنبه", 6: "یک‌شنبه"
    }
    weekday = persian_weekdays[tehran_time.weekday()]
    await message.answer(
        f"🕒 **زمان و تاریخ (به وقت تهران)**\n\n"
        f"📅 تاریخ: {tehran_time.strftime('%Y/%m/%d')}\n"
        f"📆 روز: {weekday}\n"
        f"⏰ ساعت: {tehran_time.strftime('%H:%M:%S')}"
    )

# ======== دستور /id (نمایش آیدی کاربر) ========
@dp.message(Command("id"))
async def id_command(message: types.Message):
    await message.answer(f"🆔 آیدی عددی شما:\n<code>{message.from_user.id}</code>", parse_mode="HTML")

@dp.message(Command("joke"))
async def joke(message: types.Message):
    await message.answer(random.choice(JOKES))

@dp.message(Command("quote"))
async def quote(message: types.Message):
    await message.answer(f"💬 {random.choice(QUOTES)}")

@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("✅ ربات آنلاین و سالم است!")

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی به پنل ادمین ندارید!")
        return
    await message.answer("⚙️ پنل ادمین:", reply_markup=admin_menu())

# ============================================
# ======== پاسخ به پیام‌های متنی ========
# ============================================
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id

    # بررسی مسدود بودن
    if await is_banned(user_id):
        await message.answer("🚫 شما توسط ادمین مسدود شده‌اید!")
        return

    # بررسی عضویت در کانال
    if not await is_member(user_id):
        await message.answer(
            "❌ شما عضو کانال ما نیستی!\n"
            "لطفاً اول عضو کانال بشو تا بتوانی از ربات استفاده کنی.",
            reply_markup=channel_check_menu()
        )
        return

    text = message.text.strip().lower()
    
    # پاسخ به احوال‌پرسی
    for key, response in GREETINGS.items():
        if key in text:
            await message.answer(response)
            return

    # هوش مصنوعی
    ai_response = await ask_ai(text)
    if ai_response:
        await message.answer(ai_response)
        return

    # جملات خنده‌دار
    await message.answer(random.choice(FUNNY_FALLBACKS))

# ============================================
# ======== پورت ========
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
