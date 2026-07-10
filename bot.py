import asyncio
import os
import logging
import random
import requests
from datetime import datetime
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

# ======== تنظیمات از متغیرهای محیطی ========
ADMIN_ID = int(os.getenv("ADMIN_ID", 466050034))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", -1001277492702))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/YourChannel")

client = MongoClient(MONGO_URI)
db = client["telegram_bot"]
users_col = db["users"]

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ======== دیکشنری پاسخ‌های هوشمند ========
GREETINGS = {
    "سلام": ["سلام! 👋", "سلام عزیز! 😊", "درود!", "سلام علیک!", "سلام به تو!"],
    "خوبی": ["خوبم ممنون! تو چطوری؟", "عالی! تو خوبی؟", "خوبم، مرسی!"],
    "چطوری": ["خوبم، ممنون! تو چطوری؟", "عالی! از تو چه خبر؟"],
    "مرسی": ["خواهش می‌کنم! 🤗", "قربانت!", "خواهش!"],
    "خداحافظ": ["خداحافظ! 👋", "به امید دیدار!", "فعلاً!"],
    "صبح بخیر": ["صبح بخیر! ☀️", "روز خوبی داشته باشی!"],
    "شب بخیر": ["شب بخیر! 🌙", "خواب خوب!"]
}

JOKES = [
    "چرا مرغ از جاده رد شد؟ برای اینکه به اون طرف برسه! 😂",
    "بهترین زبان برنامه‌نویسی؟ پایتون! 🐍",
    "ربات خوب رباتی که جواب بده!",
    "یک پنگوئن به یخچال نگاه کرد و گفت: چقدر خنک! 😄",
    "چرا ریاضیات غمگینه؟ چون مسائلش بی‌جوابه!",
    "چی می‌شه اگه نارگیل رو بندازی تو رودخونه؟ آب می‌شه!",
    "بهترین شوخی: کد بزن و لذت ببر!",
    "یک گربه به کامپیوتر گفت: منوس! 😹"
]

QUOTES = [
    "همیشه به فکر فردا باش!",
    "موفقیت یعنی بلند شدن دوباره!",
    "کد بزن و لذت ببر!",
    "زندگی مثل یه جعبه شکلاته، هیچ وقت نمی‌دونی چی به دست میاری!",
    "بهترین زمان برای شروع همیشه الان است!",
    "هیچ چیز غیرممکن نیست، فقط زمان می‌بره!",
    "با امید و تلاش، قله‌ها فتح می‌شوند!",
    "لبخند بزن، دنیا لبخند می‌زند! 😊"
]

# ======== توابع کمکی ========
async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def is_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def get_greeting_response(text: str) -> str:
    text = text.lower().strip()
    for key, responses in GREETINGS.items():
        if key in text:
            return random.choice(responses)
    return None

async def ask_ai(query: str) -> str:
    try:
        url = f"https://api.nexra.aryan.ir/v1/chat/gpt?text={query}"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success" and data.get("data"):
                return data["data"].strip()
        return None
    except:
        return None

# ======== منوها ========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 دانلود اینستاگرام", callback_data="insta")],
        [InlineKeyboardButton(text="🎬 دانلود یوتیوب", callback_data="youtube")],
        [InlineKeyboardButton(text="📱 دانلود تیک‌تاک", callback_data="tiktok")],
        [InlineKeyboardButton(text="📤 آپلود فیلم/عکس", callback_data="upload")],
        [InlineKeyboardButton(text="🎮 بازی و سرگرمی", callback_data="game")],
        [InlineKeyboardButton(text="💰 حمایت مالی", callback_data="donate")],
        [InlineKeyboardButton(text="👥 ممبرگیر", callback_data="members")],
        [InlineKeyboardButton(text="⚙️ پنل ادمین", callback_data="admin_panel")]
    ])

def game_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 تاس", callback_data="dice"),
         InlineKeyboardButton(text="🎯 دارت", callback_data="dart")],
        [InlineKeyboardButton(text="🎰 شانس", callback_data="slot")],
        [InlineKeyboardButton(text="🪨 سنگ‌کاغذ‌قیچی", callback_data="rps")],
        [InlineKeyboardButton(text="🔢 حدس عدد", callback_data="guess")],
        [InlineKeyboardButton(text="🏎️ ماشین‌بازی", callback_data="race")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_main")]
    ])

def rps_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪨 سنگ", callback_data="rps_stone")],
        [InlineKeyboardButton(text="📄 کاغذ", callback_data="rps_paper")],
        [InlineKeyboardButton(text="✂️ قیچی", callback_data="rps_scissors")]
    ])

def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 آمار کاربران", callback_data="stats")],
        [InlineKeyboardButton(text="📢 ارسال همگانی", callback_data="broadcast")],
        [InlineKeyboardButton(text="📋 لیست کاربران", callback_data="user_list")],
        [InlineKeyboardButton(text="🗑 حذف کاربر", callback_data="delete_user")],
        [InlineKeyboardButton(text="⚙️ تنظیمات گروه", callback_data="group_settings")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_main")]
    ])

def group_settings_menu():
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

# ======== دستور /start ========
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id, "name": message.from_user.first_name})

    if not await is_member(user_id):
        await message.answer(
            f"👋 سلام {message.from_user.first_name}!\n"
            "برای استفاده از ربات، لطفاً اول عضو کانال ما بشو:",
            reply_markup=channel_check_menu()
        )
        return

    await message.answer(
        f"🚀 سلام {message.from_user.first_name}!\n"
        "به ربات خوش آمدی. (نسخه نهایی با هوش مصنوعی)",
        reply_markup=main_menu()
    )

# ======== بررسی عضویت ========
@dp.callback_query(lambda c: c.data == "check_join")
async def check_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await is_member(user_id):
        await callback.message.edit_text("✅ ممنون! حالا می‌تونی از ربات استفاده کنی.")
        await callback.message.answer("🚀 منوی اصلی:", reply_markup=main_menu())
    else:
        await callback.answer("❌ هنوز عضو کانال نشدی! اول عضو شو.", show_alert=True)

# ======== دانلود اینستاگرام ========
@dp.callback_query(lambda c: c.data == "insta")
async def insta(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("📎 لینک پست اینستاگرام را بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and ("instagram.com" in msg.text or "instagr.am" in msg.text))
async def get_insta(message: types.Message):
    if not await is_member(message.from_user.id):
        await message.answer("❌ اول عضو کانال بشو!")
        return
    await message.answer("❌ متأسفانه دانلود اینستاگرام با مشکلات فنی مواجه شده. لطفاً از گزینه‌های یوتیوب یا تیک‌تاک استفاده کن.")

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
    await message.answer("⏳ در حال دریافت ویدیو از یوتیوب...")
    try:
        yt = YouTube(message.text)
        stream = yt.streams.get_highest_resolution()
        if stream:
            await message.answer_video(stream.url, caption=f"🎬 {yt.title}")
        else:
            await message.answer("❌ خطا! ویدیو پیدا نشد.")
    except Exception as e:
        logging.error(e)
        await message.answer("❌ خطا! لینک معتبر نیست.")

# ======== دانلود تیک‌تاک ========
@dp.callback_query(lambda c: c.data == "tiktok")
async def tiktok(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("📱 لینک ویدیو تیک‌تاک را بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and ("tiktok.com" in msg.text or "vm.tiktok.com" in msg.text))
async def get_tiktok(message: types.Message):
    if not await is_member(message.from_user.id):
        await message.answer("❌ اول عضو کانال بشو!")
        return
    await message.answer("⏳ در حال دریافت ویدیو از تیک‌تاک...")
    try:
        api_url = f"https://www.tikwm.com/api/?url={message.text}"
        response = requests.get(api_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("code") == 0 and data.get("data"):
                video_url = data["data"]["play"]
                if video_url:
                    await message.answer_video(video_url, caption="📱 ویدیو از تیک‌تاک دانلود شد!")
                    return
        await message.answer("❌ خطا! لینک معتبر نیست.")
    except Exception as e:
        logging.error(e)
        await message.answer("❌ خطا! لطفاً لینک را بررسی کن.")

# ======== آپلود ========
@dp.callback_query(lambda c: c.data == "upload")
async def upload(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("📤 فیلم یا عکس خود را بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.photo or msg.video)
async def handle_media(message: types.Message):
    if not await is_member(message.from_user.id):
        await message.answer("❌ اول عضو کانال بشو!")
        return
    await message.answer("✅ دریافت شد!")

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

@dp.callback_query(lambda c: c.data == "slot")
async def slot(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer_dice(emoji="🎰")
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

@dp.callback_query(lambda c: c.data == "guess")
async def guess(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    number = random.randint(1, 10)
    await callback.message.answer(f"🔢 من عدد {number} رو انتخاب کردم!")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "race")
async def race(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    winner = random.choice(["🚗", "🚕", "🚙", "🏎️"])
    await callback.message.answer(f"🏁 برنده مسابقه: {winner}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.answer("🔙 منوی اصلی:", reply_markup=main_menu())
    await callback.answer()

# ======== حمایت مالی ========
@dp.callback_query(lambda c: c.data == "donate")
async def donate(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("💳 لینک حمایت مالی: https://example.com")
    await callback.answer()

# ======== ممبرگیر ========
@dp.callback_query(lambda c: c.data == "members")
async def members(callback: types.CallbackQuery):
    if not await is_member(callback.from_user.id):
        await callback.answer("❌ اول عضو کانال بشو!", show_alert=True)
        return
    await callback.message.answer("👥 لینک دعوت: @Admin")
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
    await callback.message.answer(f"📊 تعداد کاربران: {count}")
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
    count = 0
    for user in users:
        try:
            await bot.send_message(user["_id"], text)
            count += 1
        except:
            pass
    await message.answer(f"✅ پیام به {count} کاربر ارسال شد.")

@dp.callback_query(lambda c: c.data == "user_list")
async def user_list(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    users = users_col.find()
    names = []
    for user in users:
        name = user.get("name", "بدون نام")
        names.append(f"{name} (ID: {user['_id']})")
    if names:
        text = "📋 لیست کاربران:\n" + "\n".join(names[:20])
        await callback.message.answer(text)
    else:
        await callback.message.answer("📭 هنوز کاربری ثبت نشده.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "delete_user")
async def delete_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("🗑 آیدی عددی کاربر را برای حذف بفرستید:")
    await callback.answer()

@dp.message(lambda msg: msg.text and msg.text.isdigit() and await is_admin(msg.from_user.id))
async def delete_user_cmd(message: types.Message):
    user_id = int(message.text)
    result = users_col.delete_one({"_id": user_id})
    if result.deleted_count:
        await message.answer(f"✅ کاربر {user_id} حذف شد.")
    else:
        await message.answer(f"❌ کاربر {user_id} یافت نشد.")

@dp.callback_query(lambda c: c.data == "group_settings")
async def group_settings(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("⚙️ تنظیمات گروه:", reply_markup=group_settings_menu())
    await callback.answer()

# ======== مدیریت گروه ========
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

@dp.callback_query(lambda c: c.data == "ban_user")
async def ban_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("🚫 آیدی عددی کاربر را برای بن بفرستید (مثلاً /ban 123456789):")
    await callback.answer()

@dp.message(Command("ban"))
async def ban_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    try:
        user_id = int(message.text.split()[1])
        await bot.ban_chat_member(message.chat.id, user_id)
        await message.answer(f"✅ کاربر {user_id} بن شد.")
    except:
        await message.answer("❌ فرمت: `/ban 123456789`")

@dp.callback_query(lambda c: c.data == "unban_user")
async def unban_user(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("✅ آیدی عددی کاربر را برای رفع بن بفرستید (مثلاً /unban 123456789):")
    await callback.answer()

@dp.message(Command("unban"))
async def unban_cmd(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین!")
        return
    try:
        user_id = int(message.text.split()[1])
        await bot.unban_chat_member(message.chat.id, user_id)
        await message.answer(f"✅ بن کاربر {user_id} رفع شد.")
    except:
        await message.answer("❌ فرمت: `/unban 123456789`")

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

# ======== پاسخ به پیام‌های متنی ========
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    text = message.text.strip()

    if not await is_member(user_id):
        await message.answer("❌ لطفاً اول عضو کانال ما بشو.", reply_markup=channel_check_menu())
        return

    greeting_response = get_greeting_response(text)
    if greeting_response:
        await message.answer(greeting_response)
        return

    ai_response = await ask_ai(text)
    if ai_response:
        await message.answer(ai_response)
        return

    fallback = random.choice([
        random.choice(JOKES),
        "💬 " + random.choice(QUOTES),
        "❓ سوالی داری؟ می‌تونم کمک کنم!"
    ])
    await message.answer(fallback)

# ======== دستورات ========
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 لیست دستورات:\n"
        "/start - شروع و منوی اصلی\n"
        "/help - نمایش راهنما\n"
        "/about - درباره ربات\n"
        "/ping - بررسی وضعیت\n"
        "/time - ساعت و تاریخ\n"
        "/id - آیدی عددی شما\n"
        "/profile - پروفایل شما\n"
        "/stat - آمار کاربران\n"
        "/joke - جوک تصادفی\n"
        "/quote - نقل قول انگیزشی\n"
        "/admin - پنل ادمین"
    )

@dp.message(Command("about"))
async def about(message: types.Message):
    await message.answer("🤖 ربات قدرتمند با هوش مصنوعی، دانلود یوتیوب و تیک‌تاک، بازی‌ها و مدیریت گروه!")

@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("✅ ربات آنلاین است!")

@dp.message(Command("time"))
async def time_command(message: types.Message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await message.answer(f"🕒 {now}")

@dp.message(Command("id"))
async def id_command(message: types.Message):
    await message.answer(f"🆔 آیدی عددی شما: `{message.from_user.id}`")

@dp.message(Command("profile"))
async def profile(message: types.Message):
    await message.answer(f"👤 نام: {message.from_user.full_name}\n🆔 آیدی: {message.from_user.id}")

@dp.message(Command("stat"))
async def stat(message: types.Message):
    count = users_col.count_documents({})
    await message.answer(f"📊 تعداد کاربران: {count}")

@dp.message(Command("joke"))
async def joke(message: types.Message):
    await message.answer(random.choice(JOKES))

@dp.message(Command("quote"))
async def quote(message: types.Message):
    await message.answer(f"💬 {random.choice(QUOTES)}")

@dp.message(Command("admin"))
async def admin_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی به پنل ادمین ندارید!")
        return
    await message.answer("⚙️ پنل ادمین:", reply_markup=admin_menu())

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
