import asyncio
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import BOT_TOKEN
from bot.handlers import start, login, forgot, dashboard, order, withdraw, membership, referral
from bot.background import auto_fail_job, notification_job
from web.main import app


async def start_bot():
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


async def start_web():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    print("🌐 Web started on http://0.0.0.0:8000")
    await server.serve()


async def main():
    await asyncio.gather(
        start_bot(),
        start_web()
    )


if __name__ == "__main__":
    asyncio.run(main())
