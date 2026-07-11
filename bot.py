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
FUNNY_FALLBACKS = ["چی میگی بچه خوشگل؟ 😏", "سیک تو بزن تا سیکمو نزدن 😂", "نمیفهمم حاجی چی میگی", "این چرت و پرتا چیه میگی مردک 🤔", "به نظرم ط ی چیزی زدی اینارو میگی"]

JOKES = [ ... ]  # لیست کامل جوک‌ها از کد اصلی

QUOTES = [ ... ]  # لیست کامل نقل قول

GREETINGS = { ... }  # لیست کامل سلام

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
        activities_col.insert_one({"user_id": user_id, "action": action, "details": details, "timestamp": datetime.now()})
        users_col.update_one({"_id": user_id}, {"$set": {"last_activity": datetime.now()}})
    except:
        pass

async def ask_ai(query: str) -> str:
    # توابع AI رو از کد اصلی کپی کن
    pass  # (کامل از کد قبلی)

def get_tehran_time():
    return datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)

# ======== منوها (کامل از کد اصلی) ========
def main_menu(): ... 
# (همه منوها رو از کد اصلی خودت کپی کن)

# ======== /start و callbackهای اصلی (کامل) ========
# (همه رو از کد اصلی کپی کن)

# ======== جستجوی کاربر (غیرفعال شده برای تست) ========
# @dp.message(lambda msg: msg.from_user.id == ADMIN_ID and msg.text and not msg.text.startswith('/'))
# async def handle_search_user(message: types.Message):
#     # فعلاً غیرفعال
#     pass

# ======== چت اصلی - آخرین و مهم‌ترین هندلر ========
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

    # سلام و احوالپرسی
    for key, response in GREETINGS.items():
        if key in text:
            await message.answer(response)
            await log_activity(user_id, "greeting", text)
            return

    # هوش مصنوعی
    ai_response = await ask_ai(text)
    if ai_response:
        await message.answer(ai_response)
        await log_activity(user_id, "ai_chat", text)
        return

    # پاسخ پیش‌فرض
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
