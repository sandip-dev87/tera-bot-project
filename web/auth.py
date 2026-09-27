from fastapi import Request
from shared.db import fetch_one
from shared.utils import verify_password


async def authenticate(username: str, password: str):
    """Admin login verify"""
    admin = await fetch_one(
        "SELECT id, username, password_hash, role FROM admins WHERE username = ? OR phone = ?",
        [username, username]
    )
    if not admin:
        return None
    
    admin_id, uname, pwd_hash, role = admin
    
    if not verify_password(password, pwd_hash):
        return None
    
    return {
        "id": admin_id,
        "username": uname,
        "role": role
    }


def get_current_admin(request: Request):
    """Session se current admin lo"""
    return request.session.get("admin")


def is_logged_in(request: Request) -> bool:
    return request.session.get("admin") is not None


def is_superadmin(request: Request) -> bool:
    admin = request.session.get("admin")
    if not admin:
        return False
    return admin.get("role") == "superadmin"
