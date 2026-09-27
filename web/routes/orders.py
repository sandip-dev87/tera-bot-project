from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_one, fetch_all, execute

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/orders", response_class=HTMLResponse)
async def orders_list(request: Request, status: str = "all"):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    if status == "all":
        orders = await fetch_all("SELECT * FROM orders ORDER BY id DESC LIMIT 100")
    else:
        orders = await fetch_all("SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT 100", [status])
    
    return templates.TemplateResponse("orders.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "orders": orders,
        "filter": status,
    })


@router.post("/orders/{order_id}/approve")
async def approve_order(request: Request, order_id: int, reward: float = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    order = await fetch_one("SELECT user_acc FROM orders WHERE id = ?", [order_id])
    if not order:
        return RedirectResponse("/orders")
    
    user_acc = order[0]
    
    await execute(
        "UPDATE orders SET status = 'completed', reward_amount = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
        [reward, order_id]
    )
    
    await execute("UPDATE users SET balance = balance + ? WHERE acc_no = ?", [reward, user_acc])
    
    await execute(
        "INSERT INTO transactions (user_acc, type, amount, ref_id, note) VALUES (?, 'order_reward', ?, ?, ?)",
        [user_acc, reward, order_id, f"Order #{order_id} approved"]
    )
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [user_acc])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"✅ Order #{order_id} approve! Reward: ₹{reward:.0f}"]
        )
    
    return RedirectResponse("/orders", status_code=303)


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
