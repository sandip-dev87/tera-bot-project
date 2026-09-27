from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from web.auth import is_logged_in
from shared.db import fetch_one, fetch_all, execute

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/membership", response_class=HTMLResponse)
async def membership_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    plans = await fetch_all("SELECT * FROM membership_plans ORDER BY id")
    requests = await fetch_all("SELECT * FROM memberships WHERE status = 'pending' ORDER BY id DESC LIMIT 50")
    
    return templates.TemplateResponse("membership.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "plans": plans,
        "requests": requests,
    })


@router.post("/membership/plans/add")
async def add_plan(request: Request, name: str = Form(...), price: float = Form(...), duration_days: int = Form(...), description: str = Form(""), is_free: int = Form(0)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute(
        "INSERT INTO membership_plans (name, price, duration_days, description, is_free) VALUES (?, ?, ?, ?, ?)",
        [name, price, duration_days, description, is_free]
    )
    
    return RedirectResponse("/membership", status_code=303)


@router.post("/membership/plans/{plan_id}/delete")
async def delete_plan(request: Request, plan_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute("DELETE FROM membership_plans WHERE id = ?", [plan_id])
    return RedirectResponse("/membership", status_code=303)


@router.post("/membership/plans/{plan_id}/toggle")
async def toggle_plan(request: Request, plan_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute("UPDATE membership_plans SET is_active = 1 - is_active WHERE id = ?", [plan_id])
    return RedirectResponse("/membership", status_code=303)


@router.post("/membership/{mem_id}/approve")
async def approve_membership(request: Request, mem_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    mem = await fetch_one("SELECT user_acc, duration_days FROM memberships WHERE id = ?", [mem_id])
    if not mem:
        return RedirectResponse("/membership")
    
    user_acc, duration = mem
    expiry = datetime.now() + timedelta(days=duration or 30)
    
    await execute(
        "UPDATE users SET membership_active = 1, membership_expiry = ? WHERE acc_no = ?",
        [expiry, user_acc]
    )
    
    await execute(
        "UPDATE memberships SET status = 'approved', approved_at = CURRENT_TIMESTAMP WHERE id = ?",
        [mem_id]
    )
    
    user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [user_acc])
    if user:
        await execute(
            "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
            [user[0], f"✅ Membership approve!\nExpiry: {expiry.strftime('%Y-%m-%d')}"]
        )
    
    return RedirectResponse("/membership", status_code=303)


@router.post("/membership/{mem_id}/reject")
async def reject_membership(request: Request, mem_id: int, reason: str = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    mem = await fetch_one("SELECT user_acc FROM memberships WHERE id = ?", [mem_id])
    if mem:
        await execute(
            "UPDATE memberships SET status = 'rejected', admin_note = ? WHERE id = ?",
            [reason, mem_id]
        )
        
        user = await fetch_one("SELECT tg_id FROM users WHERE acc_no = ?", [mem[0]])
        if user:
            await execute(
                "INSERT INTO notifications (tg_id, message) VALUES (?, ?)",
                [user[0], f"❌ Membership reject\nReason: {reason}"]
            )
    
    return RedirectResponse("/membership", status_code=303)
