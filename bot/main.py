import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from bot.config import BOT_TOKEN
from bot.handlers import start, login, forgot, dashboard, order, withdraw, membership, referral
from bot.background import auto_fail_job, notification_job

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(login.router)
    dp.include_router(forgot.router)
    dp.include_router(dashboard.router)
    dp.include_router(order.router)
    dp.include_router(withdraw.router)
    dp.include_router(membership.router)
    dp.include_router(referral.router)
    asyncio.create_task(auto_fail_job(bot))
    asyncio.create_task(notification_job(bot))
    print("🤖 Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
