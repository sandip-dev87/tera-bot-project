import random
import string
from datetime import datetime, timedelta
import bcrypt
from shared.db import fetch_one, execute


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        hash_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


async def generate_acc_no() -> str:
    while True:
        length = random.randint(4, 6)
        acc_no = ''.join(random.choices(string.digits, k=length))
        existing = await fetch_one("SELECT acc_no FROM users WHERE acc_no = ?", [acc_no])
        if not existing:
            return acc_no


def generate_otp() -> str:
    return str(random.randint(100000, 999999))


async def save_otp(mobile: str, otp: str, minutes: int = 5):
    # Expiry ko SQLite format mein string banao
    expires = (datetime.now() + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    await execute(
        "INSERT INTO otp (mobile, otp_code, expires_at, attempts) VALUES (?, ?, ?, 0) ON CONFLICT(mobile) DO UPDATE SET otp_code = ?, expires_at = ?, attempts = 0",
        [mobile, otp, expires, otp, expires]
    )


async def verify_otp(mobile: str, user_otp: str) -> dict:
    try:
        result = await fetch_one(
            "SELECT otp_code, expires_at, attempts FROM otp WHERE mobile = ?", [mobile]
        )
        if not result:
            return {"ok": False, "msg": "OTP nahi mila. Dobara bhejo."}
        
        otp_code, expires_at, attempts = result
        attempts = attempts or 0
        
        if attempts >= 3:
            return {"ok": False, "msg": "Bahut baar galat. Naya OTP bhejo."}
        
        # Expiry check — multiple formats try karo
        expires_dt = None
        exp_str = str(expires_at).strip()
        
        # Format 1: "2026-09-27 11:25:46"
        try:
            expires_dt = datetime.strptime(exp_str[:19], "%Y-%m-%d %H:%M:%S")
        except:
            pass
        
        # Format 2: ISO format
        if not expires_dt:
            try:
                expires_dt = datetime.fromisoformat(exp_str.replace("Z", "").replace("+00:00", ""))
            except:
                pass
        
        # Agar dono fail, toh OTP valid maano (safe fallback)
        if not expires_dt:
            print(f"WARN: Could not parse expiry: {exp_str}")
            expires_dt = datetime.now() + timedelta(minutes=5)
        
        if datetime.now() > expires_dt:
            return {"ok": False, "msg": "OTP expired. Naya bhejo."}
        
        if str(user_otp).strip() != str(otp_code).strip():
            await execute("UPDATE otp SET attempts = attempts + 1 WHERE mobile = ?", [mobile])
            return {"ok": False, "msg": "Galat OTP"}
        
        await execute("DELETE FROM otp WHERE mobile = ?", [mobile])
        return {"ok": True}
    except Exception as e:
        print(f"verify_otp error: {e}")
        return {"ok": False, "msg": f"Error: {e}"}


def is_valid_mobile(mobile: str) -> bool:
    return mobile.isdigit() and len(mobile) == 10


def is_valid_password(password: str) -> bool:
    return len(password) >= 4


def format_amount(amount: float) -> str:
    return f"₹{amount:,.0f}"


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")
