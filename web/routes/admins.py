from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in, is_superadmin
from shared.db import fetch_all, fetch_one, execute
from shared.utils import hash_password

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    from web.auth import authenticate
    
    admin = await authenticate(username, password)
    if not admin:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Galat username ya password"
        })
    
    request.session["admin"] = admin
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


@router.get("/admins", response_class=HTMLResponse)
async def admins_list(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    admins = await fetch_all("SELECT id, username, phone, role, created_at FROM admins ORDER BY id")
    
    return templates.TemplateResponse("admins.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "admins": admins,
        "is_super": is_superadmin(request),
    })


@router.post("/admins/add")
async def add_admin(request: Request, username: str = Form(...), phone: str = Form(...), password: str = Form(...), role: str = Form("admin")):
    if not is_superadmin(request):
        return RedirectResponse("/admins")
    
    pwd_hash = hash_password(password)
    
    try:
        await execute(
            "INSERT INTO admins (username, phone, password_hash, role) VALUES (?, ?, ?, ?)",
            [username, phone, pwd_hash, role]
        )
    except Exception as e:
        print(f"Admin add error: {e}")
    
    return RedirectResponse("/admins", status_code=303)


@router.post("/admins/{admin_id}/delete")
async def delete_admin(request: Request, admin_id: int):
    if not is_superadmin(request):
        return RedirectResponse("/admins")
    
    admin = await fetch_one("SELECT role FROM admins WHERE id = ?", [admin_id])
    if admin and admin[0] != "superadmin":
        await execute("DELETE FROM admins WHERE id = ?", [admin_id])
    
    return RedirectResponse("/admins", status_code=303)
