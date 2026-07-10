import asyncio
import os
import logging
import random
import aiohttp
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
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

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

ADMIN_ID = int(os.getenv("ADMIN_ID", 466050034))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", -1001277492702))

DEFAULT_CAPTION = "📌 عضویت در کانال ما: @Ajor_pareh"

# ======== توابع کمکی ========
async def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

async def is_member(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def ask_ai(query: str) -> str:
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

# ======== دیکشنری‌ها ========
GREETINGS = {
    "سلام": "سلام! 👋",
    "خوبی": "خوبم ممنون! تو چطوری؟",
    "چطوری": "خوبم، ممنون!",
    "مرسی": "خواهش می‌کنم! 🤗",
    "خداحافظ": "خداحافظ! 👋"
}

JOKES = [
    "چرا مرغ از جاده رد شد؟ برای اینکه به اون طرف برسه! 😂",
    "بهترین زبان برنامه‌نویسی؟ پایتون! 🐍",
    "یک پنگوئن به یخچال نگاه کرد و گفت: چقدر خنک! 😄",
    "چرا ریاضیات غمگینه؟ چون مسائلش بی‌جوابه!",
    "چی می‌شه اگه نارگیل رو بندازی تو رودخونه؟ آب می‌شه!"
]

QUOTES = [
    "همیشه به فکر فردا باش!",
    "موفقیت یعنی بلند شدن دوباره!",
    "کد بزن و لذت ببر!",
    "زندگی مثل یه جعبه شکلاته!",
    "بهترین زمان برای شروع، الان است!"
]

# ======== منوها ========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 دانلود یوتیوب", callback_data="youtube")],
        [InlineKeyboardButton(text="🎮 بازی و سرگرمی", callback_data="game")],
        [InlineKeyboardButton(text="⚙️ پنل ادمین", callback_data="admin_panel")]
    ])

def game_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 تاس", callback_data="dice"),
         InlineKeyboardButton(text="🎯 دارت", callback_data="dart")],
        [InlineKeyboardButton(text="🪨 سنگ‌کاغذ‌قیچی", callback_data="rps")],
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
        [InlineKeyboardButton(text="📤 آپلود فایل", callback_data="upload_file")],
        [InlineKeyboardButton(text="🔙 برگشت", callback_data="back_main")]
    ])

def channel_check_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=f"https://t.me/YourChannel")],
        [InlineKeyboardButton(text="✅ عضویت داشتم", callback_data="check_join")]
    ])

# ======== دستور /start ========
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

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
            
            # files_col.delete_one({"uuid": file_uuid})  # یکبار مصرف
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
        "به ربات خوش آمدی.",
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
    await callback.message.answer("🎬 لینک ویدیو یوتیوب را بفرست:")
    await callback.answer()

@dp.message(lambda msg: msg.text and ("youtube.com" in msg.text or "youtu.be" in msg.text))
async def get_youtube(message: types.Message):
    try:
        yt = YouTube(message.text)
        stream = yt.streams.get_highest_resolution()
        if stream:
            await message.answer_video(stream.url, caption=f"🎬 {yt.title}")
        else:
            await message.answer("❌ خطا!")
    except:
        await message.answer("❌ خطا! لینک معتبر نیست.")

# ======== بازی‌ها ========
@dp.callback_query(lambda c: c.data == "game")
async def game(callback: types.CallbackQuery):
    await callback.message.answer("🎮 یک بازی انتخاب کن:", reply_markup=game_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "dice")
async def dice(callback: types.CallbackQuery):
    await callback.message.answer_dice(emoji="🎲")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "dart")
async def dart(callback: types.CallbackQuery):
    await callback.message.answer_dice(emoji="🎯")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "rps")
async def rps(callback: types.CallbackQuery):
    await callback.message.answer("🪨 یکی رو انتخاب کن:", reply_markup=rps_menu())
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["rps_stone", "rps_paper", "rps_scissors"])
async def rps_play(callback: types.CallbackQuery):
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

@dp.callback_query(lambda c: c.data == "back_main")
async def back_main(callback: types.CallbackQuery):
    await callback.message.answer("🔙 منوی اصلی:", reply_markup=main_menu())
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

# ======== آپلود فایل (دکمه) ========
@dp.callback_query(lambda c: c.data == "upload_file")
async def upload_file_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ دسترسی ندارید!", show_alert=True)
        return
    await callback.message.answer("📤 لطفاً فایل (عکس، ویدئو، سند) را ارسال کنید.\nبرای کپشن دلخواه، هنگام ارسال فایل، در قسمت کپشن بنویسید.")
    await callback.answer()

# ======== دستور مستقیم /upload ========
@dp.message(Command("upload"))
async def upload_file_command(message: types.Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ فقط ادمین می‌تواند فایل آپلود کند!")
        return
    await message.answer("📤 لطفاً فایل (عکس، ویدئو، سند) را ارسال کنید.\nبرای کپشن دلخواه، هنگام ارسال فایل، در قسمت کپشن بنویسید.")

# ======== دریافت فایل ========
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

# ======== دستورات کامل ========
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 لیست دستورات:\n"
        "/start - شروع و منوی اصلی\n"
        "/help - نمایش راهنما\n"
        "/profile - پروفایل شما\n"
        "/time - ساعت و تاریخ\n"
        "/joke - جوک تصادفی\n"
        "/quote - نقل قول انگیزشی\n"
        "/ping - بررسی وضعیت ربات\n"
        "/upload - آپلود فایل (فقط ادمین)\n"
        "/admin - پنل ادمین"
    )

@dp.message(Command("profile"))
async def profile(message: types.Message):
    await message.answer(f"👤 نام: {message.from_user.full_name}\n🆔 آیدی: {message.from_user.id}")

@dp.message(Command("time"))
async def time_command(message: types.Message):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await message.answer(f"🕒 {now}")

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

# ======== پاسخ به پیام‌های متنی ========
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private":
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

    fallback = random.choice([
        random.choice(JOKES),
        "💬 " + random.choice(QUOTES)
    ])
    await message.answer(fallback)

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
