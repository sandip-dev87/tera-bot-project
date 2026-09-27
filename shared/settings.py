from shared.db import fetch_one, execute, fetch_all


async def get_setting(key: str, default: str = None) -> str:
    result = await fetch_one("SELECT value FROM settings WHERE key = ?", [key])
    return result[0] if result else default


async def set_setting(key: str, value: str):
    await execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
        [key, value, value]
    )


async def get_int_setting(key: str, default: int = 0) -> int:
    val = await get_setting(key, str(default))
    try:
        return int(val)
    except:
        return default


async def get_float_setting(key: str, default: float = 0.0) -> float:
    val = await get_setting(key, str(default))
    try:
        return float(val)
    except:
        return default


async def get_all_settings() -> dict:
    result = await fetch_all("SELECT key, value FROM settings")
    return {row[0]: row[1] for row in result}


async def get_order_timeout() -> int:
    return await get_int_setting("order_timeout_minutes", 40)


async def get_crypto_fee() -> float:
    return await get_float_setting("crypto_fee", 40)


async def get_upi_fee() -> float:
    return await get_float_setting("upi_fee", 10)


async def get_bank_fee() -> float:
    return await get_float_setting("bank_fee", 15)


async def get_commission_type() -> str:
    return await get_setting("commission_type", "percent")


async def get_commission_value() -> float:
    return await get_float_setting("commission_value", 10)


async def get_browser_message() -> str:
    return await get_setting("browser_message", "browser mein kholo")


async def is_membership_required() -> bool:
    val = await get_setting("membership_required", "1")
    return val == "1"


async def get_min_withdrawal() -> float:
    return await get_float_setting("min_withdrawal", 100)
