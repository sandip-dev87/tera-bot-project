from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_one, fetch_all, execute
from shared.settings import get_commission_type, get_commission_value
from bot.config import BOT_TOKEN
import aiohttp
import json

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/orders", response_class=HTMLResponse)
async def orders_list(request: Request, status: str = "all", search: str = ""):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    if search:
        if search.isdigit():
            orders = await fetch_all(
                "SELECT * FROM orders WHERE id = ? OR user_acc LIKE ? OR working_url LIKE ? ORDER BY id DESC LIMIT 100",
                [int(search), f"%{search}%", f"%{search}%"]
            )
        else:
            orders = await fetch_all(
                "SELECT * FROM orders WHERE user_acc LIKE ? OR working_url LIKE ? ORDER BY id DESC LIMIT 100",
                [f"%{search}%", f"%{search}%"]
            )
    elif status == "all":
        orders = await fetch_all("SELECT * FROM orders ORDER BY id DESC LIMIT 100")
    else:
        orders = await fetch_all("SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT 100", [status])
    
    return templates.TemplateResponse(request, "orders.html", {
        "admin": request.session.get("admin"),
        "orders": orders,
        "filter": status,
        "search": search,
    })


@router.get("/proof/{order_id}/{index}")
async def get_proof(order_id: int, index: int):
    order = await fetch_one("SELECT proof_file_ids FROM orders WHERE id = ?", [order_id])
    if not order or not order[0]:
        return Response("No proof", status_code=404)
    
    raw = order[0]
    file_id = None
    
    try:
        ids = json.loads(raw)
        if isinstance(ids, list) and len(ids) > index:
            file_id = ids[index]
        elif isinstance(ids, str):
            file_id = ids
    except (json.JSONDecodeError, TypeError):
        file_id = raw
    
    if not file_id:
        return Response("Index out of range", status_code=404)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}") as resp:
                data = await resp.json()
                if not data.get("ok"):
                    return Response(f"Telegram error", status_code=404)
                file_path = data["result"]["file_path"]
            
            async with session.get(f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}") as resp:
                content = await resp.read()
                content_type = resp.headers.get("Content-Type", "image/jpeg")
        
        return Response(content=content, media_type=content_type)
    except Exception as e:
        print(f"Proof fetch error: {e}")
        return Response(f"Error: {e}", status_code=500)


@router.post("/orders/{order_id}/approve")
async def approve_order(request: Request, order_id: int, reward: float = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    order = await fetch_one("SELECT user_acc FROM orders WHERE id = ?", [order_id])
    if not order:
        return RedirectResponse("/orders")
    
    user_acc = order[0]
    
    # 1. Order update
    await execute(
        "UPDATE orders SET status = 'completed', reward_amount = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        [reward, order_id]
    )
    
    # 2. User balance + transaction
    await execute("UPDATE users SET balance = balance + ? WHERE acc_no = ?", [reward, user_acc])
    await execute(
        "INSERT INTO transactions (user_acc, type, amount, ref_id, note) VALUES (?, 'order_reward', ?, ?, ?)",
        [user_acc, reward, order_id, f"Order #{order_id} approved"]
    )
    
    # 3. Referral commission
    await process_referral_commission(user_acc, order_id)
    
    # 4. User ko notification
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [user_acc])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"✅ Order #{order_id} approve! Reward: ₹{reward:.0f}"]
        )
    
    return RedirectResponse("/orders", status_code=303)


async def process_referral_commission(user_acc: str, order_id: int):
    """Referral commission process karo (fixed amount)"""
    # User ka referrer dhundo
    user = await fetch_one("SELECT referred_by FROM users WHERE acc_no = ?", [user_acc])
    if not user or not user[0]:
        return  # Koi referrer nahi
    
    referrer_acc = user[0]
    
    # Commission type aur value lo
    comm_type = await get_commission_type()  # 'fixed' ya 'percent'
    comm_value = await get_commission_value()  # 10 (fixed) ya 10 (percent)
    
    # **FIXED AMOUNT** — admin ne jo set kiya (₹10)
    commission = comm_value
    
    # Referrer ka balance badhao
    await execute("UPDATE users SET balance = balance + ? WHERE acc_no = ?", [commission, referrer_acc])
    
    # Referral table update
    await execute(
        "UPDATE referrals SET commission_earned = commission_earned + ? WHERE referrer_acc = ? AND referred_acc = ?",
        [commission, referrer_acc, user_acc]
    )
    
    # Transaction
    await execute(
        "INSERT INTO transactions (user_acc, type, amount, ref_id, note) VALUES (?, 'referral', ?, ?, ?)",
        [referrer_acc, commission, order_id, f"Referral commission from {user_acc}"]
    )
    
    # Referrer ko notification
    referrer = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [referrer_acc])
    if referrer:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [referrer[0], f"💰 ₹{commission:.0f} mile referral se (user {user_acc})"]
        )


@router.post("/orders/{order_id}/fail")
async def fail_order(request: Request, order_id: int, reason: str = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    order = await fetch_one("SELECT user_acc, status, deposit_amount_id FROM orders WHERE id = ?", [order_id])
    if not order:
        return RedirectResponse("/orders")
    
    user_acc, old_status, dep_id = order
    
    await execute(
        "UPDATE orders SET status = 'failed', fail_reason = ? WHERE id = ?",
        [reason, order_id]
    )
    
    if old_status == "under_processing" and dep_id:
        await execute("UPDATE deposit_amounts SET used_count = used_count - 1 WHERE id = ?", [dep_id])
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [user_acc])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"❌ Order #{order_id} fail\nReason: {reason}"]
        )
    
    return RedirectResponse("/orders", status_code=303)
