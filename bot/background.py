import asyncio
from shared.db import fetch_all, execute

async def auto_fail_job(bot):
    while True:
        try:
            expired = await fetch_all("SELECT id, user_acc FROM orders WHERE status = 'created' AND expires_at < CURRENT_TIMESTAMP")
            for order_id, user_acc in expired:
                await execute("UPDATE orders SET status = 'failed', fail_reason = 'Timeout' WHERE id = ?", [order_id])
                user = await fetch_all("SELECT tg_id FROM users WHERE acc_no = ?", [user_acc])
                if user:
                    try:
                        await bot.send_message(user[0][0], f"❌ Order #{order_id} fail ho gaya\nReason: Timeout")
                    except:
                        pass
        except Exception as e:
            print(f"Auto-fail error: {e}")
        await asyncio.sleep(60)

async def notification_job(bot):
    while True:
        try:
            pending = await fetch_all("SELECT id, tg_id, message FROM notifications WHERE is_sent = 0 LIMIT 10")
            for notif_id, tg_id, message in pending:
                try:
                    await bot.send_message(tg_id, message)
                except:
                    pass
                await execute("UPDATE notifications SET is_sent = 1 WHERE id = ?", [notif_id])
        except Exception as e:
            print(f"Notification error: {e}")
        await asyncio.sleep(10)
