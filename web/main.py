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

# Session middleware
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "secret"))

# Static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="web/templates")

# Routes
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
