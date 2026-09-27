from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_one, fetch_all, execute

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/users", response_class=HTMLResponse)
async def users_list(request: Request, search: str = ""):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    if search:
        users = await fetch_all(
            "SELECT * FROM users WHERE acc_no LIKE ? OR mobile LIKE ? OR name LIKE ? ORDER BY created_at DESC LIMIT 100",
            [f"%{search}%", f"%{search}%", f"%{search}%"]
        )
    else:
        users = await fetch_all("SELECT * FROM users ORDER BY created_at DESC LIMIT 100")
    
    return templates.TemplateResponse(request, "users.html", {
        "admin": request.session.get("admin"),
        "users": users,
        "search": search,
    })


@router.get("/users/{acc_no}", response_class=HTMLResponse)
async def user_detail(request: Request, acc_no: str):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    user = await fetch_one("SELECT * FROM users WHERE acc_no = ?", [acc_no])
    if not user:
        return RedirectResponse("/users")
    
    # Order stats
    order_stats = await fetch_one(
        """SELECT 
           COUNT(*),
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='under_processing' THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='created' THEN 1 ELSE 0 END),
           SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END),
           COALESCE(SUM(CASE WHEN status='completed' THEN reward_amount ELSE 0 END), 0),
           COALESCE(SUM(CASE WHEN status='completed' THEN deposit_amount ELSE 0 END), 0)
           FROM orders WHERE user_acc = ?""",
        [acc_no]
    )
    
    # Withdrawal stats
    wd_stats = await fetch_one(
        """SELECT 
           COUNT(*),
           COALESCE(SUM(CASE WHEN status='approved' THEN amount ELSE 0 END), 0),
           COALESCE(SUM(CASE WHEN status='pending' THEN amount ELSE 0 END), 0),
           SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END)
           FROM withdrawals WHERE user_acc = ?""",
        [acc_no]
    )
    
    # Referrals
    referrals = await fetch_all(
        """SELECT r.referred_acc, r.commission_earned, u.name, u.created_at
           FROM referrals r
           LEFT JOIN users u ON u.acc_no = r.referred_acc
           WHERE r.referrer_acc = ?
           ORDER BY r.id DESC""",
        [acc_no]
    )
    
    # Recent orders
    recent_orders = await fetch_all(
        "SELECT id, deposit_amount, status, reward_amount, created_at FROM orders WHERE user_acc = ? ORDER BY id DESC LIMIT 10",
        [acc_no]
    )
    
    # Recent transactions
    transactions = await fetch_all(
        "SELECT type, amount, note, created_at FROM transactions WHERE user_acc = ? ORDER BY id DESC LIMIT 10",
        [acc_no]
    )
    
    return templates.TemplateResponse(request, "user_detail.html", {
        "admin": request.session.get("admin"),
        "user": user,
        "order_stats": order_stats,
        "wd_stats": wd_stats,
        "referrals": referrals,
        "recent_orders": recent_orders,
        "transactions": transactions,
    })


@router.post("/users/{acc_no}/balance")
async def edit_balance(request: Request, acc_no: str, amount: float = Form(...), note: str = Form("")):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute("UPDATE users SET balance = balance + ? WHERE acc_no = ?", [amount, acc_no])
    await execute(
        "INSERT INTO transactions (user_acc, type, amount, note) VALUES (?, 'manual', ?, ?)",
        [acc_no, amount, note]
    )
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [acc_no])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"💰 Balance adjust: ₹{amount:+.0f}\nNote: {note}"]
        )
    
    return RedirectResponse(f"/users/{acc_no}", status_code=303)


@router.post("/users/{acc_no}/ban")
async def ban_user(request: Request, acc_no: str, reason: str = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute(
        "UPDATE users SET is_banned = 1, ban_reason = ?, banned_at = CURRENT_TIMESTAMP WHERE acc_no = ?",
        [reason, acc_no]
    )
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [acc_no])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"❌ Account ban\nReason: {reason}"]
        )
    
    return RedirectResponse(f"/users/{acc_no}", status_code=303)


@router.post("/users/{acc_no}/unban")
async def unban_user(request: Request, acc_no: str):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute(
        "UPDATE users SET is_banned = 0, ban_reason = NULL WHERE acc_no = ?",
        [acc_no]
    )
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [acc_no])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], "✅ Account unban ho gaya"]
        )
    
    return RedirectResponse(f"/users/{acc_no}", status_code=303)
