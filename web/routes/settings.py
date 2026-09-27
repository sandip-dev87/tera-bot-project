from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_all, execute
from shared.settings import get_all_settings, set_setting

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    settings = await get_all_settings()
    
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "settings": settings,
    })


@router.post("/settings")
async def save_settings(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    form = await request.form()
    
    for key, value in form.items():
        await set_setting(key, str(value))
    
    return RedirectResponse("/settings", status_code=303)
