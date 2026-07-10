import asyncio
import os
import logging
import random
import aiohttp
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
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
CHANNEL_ID = -1001277492702
CHANNEL_LINK = "https://t.me/ajor_pareh"
DEFAULT_CAPTION = "📌 عضویت در کانال ما: @ajor_pareh"

OPENROUTER_API_KEY = "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"

# ======== جملات خنده‌دار ========
FUNNY_FALLBACKS = [
    "چی میگی بچه خوشگل؟ 😏",
    "سیک تو بزن تا سیکمو نزدن 😂",
    "نمیفهمم حاجی چی میگی",
    "این چرت و پرتا چیه میگی مردک 🤔",
    "به نظرم ط ی چیزی زدی اینارو میگی"
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

# ======== منوهای شیشه‌ای (InlineKeyboard) ========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📥 دانلود از لینک", callback_data="download")],
        [InlineKeyboardButton(text="💳 کیف پول", callback_data="wallet"), 
         InlineKeyboardButton(text="🛒 خرید اشتراک", callback_data="buy")],
        [InlineKeyboardButton(text="📂 سفارشات", callback_data="orders"), 
         InlineKeyboardButton(text="👤 حساب کاربری", callback_data="profile")],
        [InlineKeyboardButton(text="🎁 دعوت دوستان", callback_data="invite"), 
         InlineKeyboardButton(text="📢 کانال", callback_data="channel")],
        [InlineKeyboardButton(text="🛠 پشتیبانی", callback_data="support")]
    ])

def channel_check_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 عضویت در کانال", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ عضویت داشتم", callback_data="check_join")]
    ])

# ======== تنظیم دستورات (منوی پایین ربات) ========
async def set_commands():
    commands = [
        BotCommand(command="start", description="شروع و منوی اصلی"),
        BotCommand(command="help", description="راهنما"),
    ]
    await bot.set_my_commands(commands)

# ======== دستور /start ========
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name

    # بررسی لینک اختصاصی فایل
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

    # ذخیره کاربر
    if not users_col.find_one({"_id": user_id}):
        users_col.insert_one({"_id": user_id, "name": name})

    # بررسی عضویت
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

# ======== کالبک‌های منوی اصلی ========
@dp.callback_query(lambda c: c.data == "download")
async def download_callback(callback: types.CallbackQuery):
    await callback.message.answer("🎬 لینک ویدیو یوتیوب را بفرست:")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "wallet")
async def wallet_callback(callback: types.CallbackQuery):
    await callback.message.answer("💳 کیف پول شما:\nموجودی: ۰ تومان")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "buy")
async def buy_callback(callback: types.CallbackQuery):
    await callback.message.answer("🛒 لیست اشتراک‌ها:\n۱. یک ماهه - ۱۰,۰۰۰ تومان\n۲. سه ماهه - ۲۵,۰۰۰ تومان")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "orders")
async def orders_callback(callback: types.CallbackQuery):
    await callback.message.answer("📂 لیست سفارشات شما:\nهنوز سفارشی ثبت نشده است.")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "profile")
async def profile_callback(callback: types.CallbackQuery):
    user = callback.from_user
    await callback.message.answer(f"👤 نام: {user.full_name}\n🆔 آیدی: {user.id}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "invite")
async def invite_callback(callback: types.CallbackQuery):
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{callback.from_user.id}"
    await callback.message.answer(f"🎁 لینک دعوت شما:\n<code>{link}</code>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "channel")
async def channel_callback(callback: types.CallbackQuery):
    await callback.message.answer(f"📢 کانال ما:\n{CHANNEL_LINK}")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback: types.CallbackQuery):
    await callback.message.answer("🛠 پشتیبانی:\n@AdminUsername")
    await callback.answer()

# ======== دانلود یوتیوب ========
@dp.message(lambda msg: msg.text and ("youtube.com" in msg.text or "youtu.be" in msg.text))
async def get_youtube(message: types.Message):
    if not await is_member(message.from_user.id):
        await message.answer("❌ اول عضو کانال بشو!", reply_markup=channel_check_menu())
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

# ======== آپلود فایل (فقط ادمین) ========
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
        f"✅ فایل با موفقیت آپلود شد!\n\n🔗 لینک اختصاصی:\n<code>{link}</code>",
        parse_mode="HTML"
    )

# ======== دستورات ========
@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer("📖 از دکمه‌های منوی اصلی استفاده کنید.")

# ======== پاسخ به پیام‌های متنی ========
@dp.message()
async def handle_text(message: types.Message):
    if message.chat.type != "private":
        return
    user_id = message.from_user.id
    if not await is_member(user_id):
        await message.answer(
            "❌ شما عضو کانال ما نیستی! لطفاً اول عضو شو.",
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
    await set_commands()
    logging.info("🤖 Starting bot...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
