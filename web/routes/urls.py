from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from web.auth import is_logged_in
from shared.db import fetch_one, fetch_all, execute

router = APIRouter()
templates = Jinja2Templates(directory="web/templates")


@router.get("/urls", response_class=HTMLResponse)
async def urls_list(request: Request):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    urls = await fetch_all("SELECT * FROM working_urls ORDER BY id DESC")
    all_amounts = await fetch_all("SELECT * FROM deposit_amounts ORDER BY id")
    
    return templates.TemplateResponse("urls.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "urls": urls,
        "all_amounts": all_amounts,
    })


@router.post("/urls/add")
async def add_url(request: Request, url: str = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute("INSERT INTO working_urls (url) VALUES (?)", [url])
    return RedirectResponse("/urls", status_code=303)


@router.post("/urls/{url_id}/toggle")
async def toggle_url(request: Request, url_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute("UPDATE working_urls SET is_active = 1 - is_active WHERE id = ?", [url_id])
    return RedirectResponse("/urls", status_code=303)


@router.post("/urls/{url_id}/delete")
async def delete_url(request: Request, url_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute("DELETE FROM deposit_amounts WHERE url_id = ?", [url_id])
    await execute("DELETE FROM working_urls WHERE id = ?", [url_id])
    return RedirectResponse("/urls", status_code=303)


@router.post("/urls/{url_id}/amounts/add")
async def add_amount(request: Request, url_id: int, amount: float = Form(...), deposit_structure: str = Form(...), max_limit: int = Form(...)):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    try:
        await execute(
            "INSERT INTO deposit_amounts (url_id, amount, deposit_structure, max_limit) VALUES (?, ?, ?, ?)",
            [url_id, amount, deposit_structure, max_limit]
        )
    except Exception as e:
        print(f"Duplicate: {e}")
    
    return RedirectResponse("/urls", status_code=303)


@router.post("/urls/amounts/{amt_id}/delete")
async def delete_amount(request: Request, amt_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    await execute("DELETE FROM deposit_amounts WHERE id = ?", [amt_id])
    return RedirectResponse("/urls", status_code=303)


@router.get("/urls/{url_id}/analytics", response_class=HTMLResponse)
async def url_analytics(request: Request, url_id: int):
    if not is_logged_in(request):
        return RedirectResponse("/login")
    
    url = await fetch_one("SELECT * FROM working_urls WHERE id = ?", [url_id])
    if not url:
        return RedirectResponse("/urls")
    
    total = await fetch_one("SELECT COUNT(*) FROM orders WHERE url_id = ?", [url_id])
    completed = await fetch_one("SELECT COUNT(*) FROM orders WHERE url_id = ? AND status = 'completed'", [url_id])
    processing = await fetch_one("SELECT COUNT(*) FROM orders WHERE url_id = ? AND status = 'under_processing'", [url_id])
    failed = await fetch_one("SELECT COUNT(*) FROM orders WHERE url_id = ? AND status = 'failed'", [url_id])
    
    money = await fetch_one(
        "SELECT COALESCE(SUM(deposit_amount), 0), COALESCE(SUM(reward_amount), 0) FROM orders WHERE url_id = ? AND status = 'completed'",
        [url_id]
    )
    
    amounts = await fetch_all("SELECT * FROM deposit_amounts WHERE url_id = ?", [url_id])
    
    recent = await fetch_all("SELECT * FROM orders WHERE url_id = ? ORDER BY id DESC LIMIT 20", [url_id])
    
    return templates.TemplateResponse("url_analytics.html", {
        "request": request,
        "admin": request.session.get("admin"),
        "url": url,
        "total": total[0],
        "completed": completed[0],
        "processing": processing[0],
        "failed": failed[0],
        "total_deposit": money[0],
        "total_reward": money[1],
        "amounts": amounts,
        "recent": recent,
    })
