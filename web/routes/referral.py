from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_all

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/referral", response_class=HTMLResponse)
async def referral_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    referrals = await fetch_all(
        "SELECT r.*, u.name as referrer_name FROM referrals r JOIN users u ON u.acc_no = r.referrer_acc ORDER BY r.id DESC LIMIT 100"
    )
    
    return templates.TemplateResponse(request, "referral.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "referrals": referrals,
    })
