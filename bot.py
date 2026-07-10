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

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

ADMIN_ID = int(os.getenv("ADMIN_ID", 466050034))
CHANNEL_ID = -1001277492702
CHANNEL_LINK = "https://t.me/ajor_pareh"
DEFAULT_CAPTION = "📌 عضویت در کانال ما: @ajor_pareh"

OPENROUTER_API_KEY = "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"

# ======== جملات خنده‌دار و ... ========
FUNNY_FALLBACKS = [
    "چی میگی بچه خوشگل؟ 😏",
    "سیک تو بزن تا سیکمو نزدن 😂",
    "نمیفهمم حاجی چی میگی",
    "این چرت و پرتا چیه میگی مردک 🤔",
    "به نظرم ط ی چیزی زدی اینارو میگی"
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

guess_games = {}

# ======== توابع کمکی ========
async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

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
        [InlineKeyboardButton(text="📊 آمار کاربران", callback_data="stats")],
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

# ======== ارسال فایل‌های یک گروه ========
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
            logging.error(f"خطا در ارسال فایل {f['uuid']}: {e}")
    
    await message.answer("✅ **همه فایل‌های این گروه ارسال شدند!**")

# ======== دستور /start ========
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

    if message.text and message.text.startswith("/start group_"):
        group_uuid = message.text.split("_")[1]
        if not await is_member(user_id):
            await message.answer(
                f"👋 سلام {name}!\n"
                "برای دریافت فایل‌های این گروه، لطفاً اول عضو کانال ما بشو:",
                reply_markup=channel_check_menu()
            )
            return
        await send_group_files(message, group_uuid)
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
        users_col.insert_one({"_id": user_id, "name": name})

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

# ======== بررسی مجدد عضویت ========
@dp.callback_query(lambda c: c.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_member(user_id):
        await callback.message.edit_text("✅ ممنون! حالا می‌تونی از ربات استفاده کنی.")
        await callback.message.answer("🚀 منوی اصلی:", reply_markup=main_menu())
    else:
        await callback.answer("❌ هنوز عضو کانال نشدی! اول عضو شو.", show_alert=True)

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
            await message.answer_video(stream.url, caption=f"🎬 {yt.title}")
        else:
            await message.answer("❌ خطا!")
    except:
        await message.answer("❌ خطا! لینک معتبر نیست.")

# ======== دکمه‌های منوی اصلی ========
@dp.callback_query(lambda c: c.data == "wallet")
async def wallet_callback(callback: types.CallbackQuery):
    await callback.message.answer("💳 کیف پول شما:\nموجودی: ۰ تومان\n\nاین بخش به زودی تکمیل می‌شود.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "charge")
async def charge_callback(callback: types.CallbackQuery):
    await callback.message.answer("💰 شارژ حساب:\n۱. شارژ ۱۰,۰۰۰ تومان\n۲. شارژ ۵۰,۰۰۰ تومان\n۳. شارژ ۱۰۰,۰۰۰ تومان\n\nلطفاً مبلغ مورد نظر را وارد کنید.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback: types.CallbackQuery):
    await callback.message.answer("🛠 پشتیبانی:\nبرای ارتباط با ادمین، به آیدی زیر پیام دهید:\n@AdminUsername\n\nساعات پاسخگویی: ۲۴/۷")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "profile_user")
async def profile_user_callback(callback: types.CallbackQuery):
    user = callback.from_user
    await callback.message.answer(f"👤 نام: {user.full_name}\n🆔 آیدی: {user.id}\n📱 شماره: ثبت نشده")
    await callback.answer()

# ======== بازی‌ها ========
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
    await callback.answer()

@dp.callback_query(lambda c: c.data == "dart")
async def dart(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer_dice(emoji="🎯")
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

# ======== بازی حدس عدد ========
@dp.callback_query(lambda c: c.data == "guess_game")
async def guess_game(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    number = random.randint(1, 20)
    guess_games[callback.from_user.id] = {"number": number, "attempts": 0}
    await callback.message.answer(
        f"🔢 من یک عدد بین ۱ تا ۲۰ انتخاب کردم!\n"
        f"عدد مورد نظر را بفرستید.\n"
        f"برای انصراف، /cancel را بفرستید."
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

@dp.message(lambda msg: msg.text and msg.text.isdigit())
async def handle_guess_number(message: types.Message):
    user_id = message.from_user.id
    if user_id not in guess_games:
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

# ======== بازی شیر یا خط ========
@dp.callback_query(lambda c: c.data == "coin_flip")
async def coin_flip(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("🪙 شیر یا خط؟ انتخاب کن:", reply_markup=coin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["coin_heads", "coin_tails"])
async def coin_play(callback: types.CallbackQuery):
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

# ======== پنل ادمین ========
@dp.callback_query(lambda c: c.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("⚙️ پنل ادمین:", reply_markup=admin_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "stats")
async def stats(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    count = users_col.count_documents({})
    await callback.message.answer(f"📊 تعداد کاربران ثبت‌شده: {count}")
    await callback.answer()

# ======== شروع آپلود گروه جدید ========
@dp.callback_query(lambda c: c.data == "upload_file")
async def upload_file_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    # بستن گروه قبلی اگر فعال باشه
    groups_col.update_many(
        {"admin_id": callback.from_user.id, "is_active": True},
        {"$set": {"is_active": False}}
    )
    
    # ساخت گروه جدید
    group_uuid = str(uuid.uuid4())[:8]
    groups_col.insert_one({
        "group_uuid": group_uuid,
        "admin_id": callback.from_user.id,
        "created_at": datetime.now(),
        "is_active": True,
        "file_count": 0
    })
    
    await callback.message.answer(
        f"📤 **گروه جدید ساخته شد!**\n"
        f"شناسه گروه: `{group_uuid}`\n\n"
        f"حالا فایل‌های خود را یکی یکی ارسال کنید.\n"
        f"پس از اتمام، از دکمه **انتشار گروه** در پنل ادمین استفاده کنید.\n"
        f"توجه: فقط فایل‌هایی که بعد از این پیام ارسال شوند، به این گروه اضافه می‌شوند.",
        parse_mode="Markdown"
    )
    await callback.answer()

# ======== انتشار گروه ========
@dp.callback_query(lambda c: c.data == "publish_group")
async def publish_group_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    # پیدا کردن گروه فعال برای این ادمین
    group = groups_col.find_one({"admin_id": callback.from_user.id, "is_active": True})
    
    if not group:
        await callback.answer("❌ شما هیچ گروه فعالی ندارید. ابتدا یک گروه جدید بسازید.", show_alert=True)
        return

    group_uuid = group["group_uuid"]
    file_count = group.get("file_count", 0)
    
    if file_count == 0:
        await callback.answer("❌ این گروه هیچ فایلی ندارد. لطفاً ابتدا فایل ارسال کنید.", show_alert=True)
        return

    # غیرفعال کردن گروه
    groups_col.update_one({"group_uuid": group_uuid}, {"$set": {"is_active": False}})

    # ساخت لینک
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=group_{group_uuid}"

    text = (
        f"✅ **گروه با موفقیت منتشر شد!**\n\n"
        f"🔗 لینک گروه:\n<code>{link}</code>\n\n"
        f"📂 تعداد فایل‌ها: {file_count}\n"
        f"کاربران با کلیک روی این لینک، همه فایل‌های این گروه را دریافت می‌کنند.\n"
        f"⚠️ کاربران باید عضو کانال باشند."
    )
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

# ======== دریافت فایل‌ها و ذخیره در گروه جاری ========
@dp.message(lambda msg: msg.document or msg.photo or msg.video)
async def handle_file_upload(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین می‌تواند فایل آپلود کند!")
        return

    # پیدا کردن گروه فعال برای این ادمین
    group = groups_col.find_one({"admin_id": message.from_user.id, "is_active": True})
    if not group:
        await message.answer(
            "❌ شما هیچ گروه فعالی ندارید. ابتدا با دکمه 'شروع آپلود گروه جدید' یک گروه بسازید."
        )
        return

    group_uuid = group["group_uuid"]

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
        "group_uuid": group_uuid,
        "file_id": file_id,
        "type": file_type,
        "name": file_name,
        "caption": caption,
        "uploaded_at": datetime.now()
    })

    # به‌روزرسانی تعداد فایل‌های گروه
    groups_col.update_one(
        {"group_uuid": group_uuid},
        {"$inc": {"file_count": 1}}
    )

    new_count = groups_col.find_one({"group_uuid": group_uuid})["file_count"]
    await message.answer(
        f"✅ فایل `{file_name}` با موفقیت به گروه اضافه شد.\n"
        f"تعداد فایل‌های گروه: {new_count}",
        parse_mode="Markdown"
    )

# ======== مدیریت گروه‌ها ========
@dp.callback_query(lambda c: c.data == "manage_groups")
async def manage_groups(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    groups = list(groups_col.find({"admin_id": callback.from_user.id}).sort("created_at", -1).limit(20))
    if not groups:
        await callback.message.answer("📋 شما هیچ گروهی ایجاد نکرده‌اید.")
        return
    
    keyboard = []
    for g in groups:
        status = "✅ فعال" if g.get("is_active", False) else "🔒 بسته"
        btn_text = f"{status} - {g['group_uuid']} ({g.get('file_count', 0)} فایل)"
        keyboard.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"group_info_{g['group_uuid']}"
        )])
    keyboard.append([InlineKeyboardButton(text="🔙 برگشت", callback_data="admin_panel")])
    
    await callback.message.answer(
        "📋 **لیست گروه‌های شما**\n"
        "روی هر گروه کلیک کنید تا اطلاعات آن را ببینید.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("group_info_"))
async def group_info(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    
    group_uuid = callback.data.split("_")[2]
    group = groups_col.find_one({"group_uuid": group_uuid})
    if not group:
        await callback.answer("❌ گروه یافت نشد.", show_alert=True)
        return
    
    files = list(files_col.find({"group_uuid": group_uuid}).sort("uploaded_at", 1))
    file_names = "\n".join([f"• {f.get('name', 'بی‌نام')}" for f in files]) if files else "هیچ فایلی"
    
    await callback.message.answer(
        f"📁 **اطلاعات گروه**\n"
        f"شناسه: `{group_uuid}`\n"
        f"وضعیت: {'✅ فعال' if group.get('is_active') else '🔒 بسته'}\n"
        f"تعداد فایل‌ها: {len(files)}\n"
        f"تاریخ ایجاد: {group['created_at']}\n\n"
        f"📎 فایل‌ها:\n{file_names}"
    )
    await callback.answer()

# ======== دستورات ========
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 لیست دستورات:\n"
        "/start - شروع و منوی اصلی\n"
        "/help - نمایش راهنما\n"
        "/profile - پروفایل شما\n"
        "/time - ساعت و تاریخ (تهران)\n"
        "/id - نمایش آیدی عددی شما\n"
        "/joke - جوک تصادفی\n"
        "/quote - نقل قول انگیزشی\n"
        "/ping - بررسی وضعیت ربات\n"
        "/admin - پنل ادمین\n"
        "/cancel - لغو بازی حدس عدد\n"
        "/publishgroup - انتشار گروه فعلی (اختیاری، می‌توانید از دکمه استفاده کنید)\n"
        "\n⚙️ دستورات مدیریت گروه:\n"
        "/lock - قفل گروه\n"
        "/unlock - باز کردن گروه\n"
        "/ban [آیدی] - بن کاربر\n"
        "/unban [آیدی] - رفع بن\n"
        "/clear [تعداد] - پاک کردن پیام‌ها"
    )

@dp.message(Command("profile"))
async def profile(message: types.Message):
    await message.answer(f"👤 نام: {message.from_user.full_name}\n🆔 آیدی: {message.from_user.id}")

@dp.message(Command("time"))
async def time_command(message: types.Message):
    t = get_tehran_time()
    days = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنج‌شنبه", "جمعه", "شنبه", "یک‌شنبه"]
    await message.answer(
        f"🕒 **زمان و تاریخ (تهران)**\n\n"
        f"📅 تاریخ: {t.strftime('%Y/%m/%d')}\n"
        f"📆 روز: {days[t.weekday()]}\n"
        f"⏰ ساعت: {t.strftime('%H:%M:%S')}"
    )

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

@dp.message(Command("publishgroup"))
async def publish_group_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    
    # پیدا کردن گروه فعال
    group = groups_col.find_one({"admin_id": message.from_user.id, "is_active": True})
    if not group:
        await message.answer("❌ شما هیچ گروه فعالی ندارید. ابتدا یک گروه جدید بسازید.")
        return

    group_uuid = group["group_uuid"]
    file_count = group.get("file_count", 0)
    
    if file_count == 0:
        await message.answer("❌ این گروه هیچ فایلی ندارد. لطفاً ابتدا فایل ارسال کنید.")
        return

    groups_col.update_one({"group_uuid": group_uuid}, {"$set": {"is_active": False}})

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=group_{group_uuid}"

    text = (
        f"✅ **گروه با موفقیت منتشر شد!**\n\n"
        f"🔗 لینک گروه:\n<code>{link}</code>\n\n"
        f"📂 تعداد فایل‌ها: {file_count}\n"
        f"کاربران با کلیک روی این لینک، همه فایل‌های این گروه را دریافت می‌کنند.\n"
        f"⚠️ کاربران باید عضو کانال باشند."
    )
    await message.answer(text, parse_mode="HTML")

# ======== مدیریت گروه‌های تلگرامی ========
@dp.message(Command("lock"))
async def lock_group(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    if message.chat.type == "private":
        await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
        return
    await bot.set_chat_permissions(message.chat.id, ChatPermissions(can_send_messages=False))
    await message.answer("🔒 گروه قفل شد. فقط ادمین‌ها می‌توانند پیام بفرستند.")

@dp.message(Command("unlock"))
async def unlock_group(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    if message.chat.type == "private":
        await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
        return
    await bot.set_chat_permissions(message.chat.id, ChatPermissions(can_send_messages=True))
    await message.answer("🔓 گروه باز شد. همه می‌توانند پیام بفرستند.")

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    if message.chat.type == "private":
        await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
        return
    try:
        user_id = int(message.text.split()[1])
        await bot.ban_chat_member(message.chat.id, user_id)
        await message.answer(f"✅ کاربر {user_id} بن شد.")
    except:
        await message.answer("❌ فرمت صحیح: `/ban 123456789`")

@dp.message(Command("unban"))
async def unban_user(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    if message.chat.type == "private":
        await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
        return
    try:
        user_id = int(message.text.split()[1])
        await bot.unban_chat_member(message.chat.id, user_id)
        await message.answer(f"✅ بن کاربر {user_id} رفع شد.")
    except:
        await message.answer("❌ فرمت صحیح: `/unban 123456789`")

@dp.message(Command("clear"))
async def clear_messages(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    if message.chat.type == "private":
        await message.answer("❌ این دستور فقط در گروه کار می‌کند.")
        return
    try:
        count = int(message.text.split()[1])
        if count > 100:
            await message.answer("❌ حداکثر ۱۰۰ پیام.")
            return
        deleted = 0
        async for msg in bot.get_chat_history(message.chat.id, limit=count):
            if msg.message_id != message.message_id:
                await msg.delete()
                deleted += 1
        await message.answer(f"✅ {deleted} پیام پاک شد.")
    except:
        await message.answer("❌ فرمت صحیح: `/clear 10`")

# ======== پاسخ به پیام‌های متنی ========
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id

    if not await is_member(user_id):
        await message.answer(
            "❌ شما عضو کانال ما نیستی!\n"
            "لطفاً اول عضو کانال بشو تا بتوانی از ربات استفاده کنی.",
            reply_markup=channel_check_menu()
        )
        return

    text = message.text.strip().lower()
    
    for key, response in GREETINGS.items():
        if key in text:
            await message.answer(response)
            return

    ai_response = await ask_ai(text)
    if ai_response:
        await message.answer(ai_response)
        return

    await message.answer(random.choice(FUNNY_FALLBACKS))

# ======== پورت ========
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
