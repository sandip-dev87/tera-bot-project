from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

from web.routes import dashboard, orders, users, withdrawals, membership, urls, referral, settings, admins

app = FastAPI(title="Admin Panel")

app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "secret"))
app.mount("/static", StaticFiles(directory="web/static"), name="static")

templates = Jinja2Templates(directory="web/templates")


def safe_amount(value):
    """String ya number ko safe amount mein convert karo"""
    try:
        return f"₹{float(value):,.0f}"
    except (ValueError, TypeError):
        return f"₹{value}"


def safe_num(value):
    """String ya number ko safe number mein convert karo"""
    try:
        return f"{float(value):,.0f}"
    except (ValueError, TypeError):
        return str(value) if value else "0"


templates.env.filters["safe_amount"] = safe_amount
templates.env.filters["safe_num"] = safe_num

# Baaki routes ko same templates use karne ke liye globally inject karo
import web.routes.dashboard as dash_mod
import web.routes.orders as orders_mod
import web.routes.users as users_mod
import web.routes.withdrawals as wd_mod
import web.routes.membership as mem_mod
import web.routes.urls as urls_mod
import web.routes.referral as ref_mod
import web.routes.settings as set_mod
import web.routes.admins as adm_mod

for mod in [dash_mod, orders_mod, users_mod, wd_mod, mem_mod, urls_mod, ref_mod, set_mod, adm_mod]:
    mod.templates = templates

app.include_router(dashboard.router)
app.include_router(orders.router)
app.include_router(users.router)
app.include_router(withdrawals.router)
app.include_router(membership.router)
app.include_router(urls.router)
app.include_router(referral.router)
app.include_router(settings.router)
app.include_router(admins.router)


@app.get("/")
async def root():
    return RedirectResponse("/login")
