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
        "request": request,
        "admin": request.session.get("admin"),
        "users": users,
        "search": search,
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
    
    return RedirectResponse("/users", status_code=303)


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
    
    return RedirectResponse("/users", status_code=303)


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
    
    return RedirectResponse("/users", status_code=303)
