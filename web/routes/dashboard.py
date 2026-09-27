from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_one, fetch_all

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    total_users = await fetch_one("SELECT COUNT(*) FROM users WHERE is_banned = 0")
    active_members = await fetch_one("SELECT COUNT(*) FROM users WHERE membership_active = 1 AND membership_expiry > CURRENT_TIMESTAMP")
    total_orders = await fetch_one("SELECT COUNT(*) FROM orders")
    
    pending_orders = await fetch_one("SELECT COUNT(*) FROM orders WHERE status = 'created'")
    processing_orders = await fetch_one("SELECT COUNT(*) FROM orders WHERE status = 'under_processing'")
    completed_orders = await fetch_one("SELECT COUNT(*) FROM orders WHERE status = 'completed'")
    failed_orders = await fetch_one("SELECT COUNT(*) FROM orders WHERE status = 'failed'")
    
    pending_withdrawals = await fetch_one("SELECT COUNT(*), COALESCE(SUM(total_deducted), 0) FROM withdrawals WHERE status = 'pending'")
    
    users_balance = await fetch_one("SELECT COALESCE(SUM(balance), 0) FROM users WHERE is_banned = 0")
    
    fees_profit = await fetch_one("SELECT COALESCE(SUM(processing_fee), 0), COALESCE(SUM(actual_cost), 0), COALESCE(SUM(profit), 0) FROM withdrawals WHERE status = 'approved'")
    
    membership_revenue = await fetch_one("SELECT COALESCE(SUM(amount), 0) FROM memberships WHERE status = 'approved'")
    membership_pending = await fetch_one("SELECT COUNT(*) FROM memberships WHERE status = 'pending'")
    
    return templates.TemplateResponse(request, "dashboard.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "total_users": total_users[0],
        "active_members": active_members[0],
        "total_orders": total_orders[0],
        "pending_orders": pending_orders[0],
        "processing_orders": processing_orders[0],
        "completed_orders": completed_orders[0],
        "failed_orders": failed_orders[0],
        "pending_withdrawals_count": pending_withdrawals[0],
        "pending_withdrawals_amount": pending_withdrawals[1],
        "users_balance": users_balance[0],
        "fees": fees_profit[0],
        "cost": fees_profit[1],
        "profit": fees_profit[2],
        "membership_revenue": membership_revenue[0],
        "membership_pending": membership_pending[0],
    })
