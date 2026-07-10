import asyncio
import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    logging.error("❌ توکن تنظیم نشده!")
    exit(1)

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ======== منوی اصلی ========
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🎬 یوتیوب", callback_data="youtube")],
        [InlineKeyboardButton("🎮 بازی", callback_data="game")],
        [InlineKeyboardButton("💳 کیف پول", callback_data="wallet"), InlineKeyboardButton("💰 شارژ", callback_data="charge")],
        [InlineKeyboardButton("🛠 پشتیبانی", callback_data="support"), InlineKeyboardButton("👤 حساب", callback_data="profile_user")],
        [InlineKeyboardButton("⚙️ پنل ادمین", callback_data="admin_panel")]
    ])

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "🚀 سلام! به ربات خوش آمدی.",
        reply_markup=main_menu()
    )

@dp.callback_query()
async def handle_callback(callback: types.CallbackQuery):
    await callback.answer("دکمه دریافت شد!")
    await callback.message.answer(f"شما دکمه {callback.data} را زدید.")

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
