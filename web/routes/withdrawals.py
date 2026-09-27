from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_one, fetch_all, execute

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/withdrawals", response_class=HTMLResponse)
async def withdrawals_list(request: Request, status: str = "pending"):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    withdrawals = await fetch_all(
        "SELECT * FROM withdrawals WHERE status = ? ORDER BY id DESC LIMIT 100",
        [status]
    )
    
    return templates.TemplateResponse("withdrawals.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "withdrawals": withdrawals,
        "filter": status,
    })


@router.post("/withdrawals/{wd_id}/approve")
async def approve_withdrawal(request: Request, wd_id: int, note: str = Form("")):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    wd = await fetch_one("SELECT user_acc, amount FROM withdrawals WHERE id = ?", [wd_id])
    if not wd:
        return RedirectResponse("/withdrawals")
    
    await execute(
        "UPDATE withdrawals SET status = 'approved', admin_note = ?, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
        [note, wd_id]
    )
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [wd[0]])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"✅ Withdrawal ₹{wd[1]:.0f} approved!"]
        )
    
    return RedirectResponse("/withdrawals", status_code=303)


@router.post("/withdrawals/{wd_id}/reject")
async def reject_withdrawal(request: Request, wd_id: int, reason: str = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    wd = await fetch_one("SELECT user_acc, total_deducted FROM withdrawals WHERE id = ?", [wd_id])
    if not wd:
        return RedirectResponse("/withdrawals")
    
    user_acc, total = wd
    
    await execute(
        "UPDATE withdrawals SET status = 'rejected', admin_note = ?, processed_at = CURRENT_TIMESTAMP WHERE id = ?",
        [reason, wd_id]
    )
    
    await execute("UPDATE users SET balance = balance + ? WHERE acc_no = ?", [total, user_acc])
    
    await execute(
        "INSERT INTO transactions (user_acc, type, amount, ref_id, note) VALUES (?, 'manual', ?, ?, ?)",
        [user_acc, total, wd_id, f"Withdrawal #{wd_id} rejected - refund"]
    )
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [user_acc])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"❌ Withdrawal reject\nReason: {reason}\n₹{total:.0f} wapas balance mein"]
        )
    
    return RedirectResponse("/withdrawals", status_code=303)
