import libsql_client
import os
from dotenv import load_dotenv

load_dotenv()

TURSO_URL = os.getenv("TURSO_URL")
TURSO_TOKEN = os.getenv("TURSO_TOKEN")

_client = None


async def get_client():
    global _client
    if _client is None:
        http_url = TURSO_URL.replace("libsql://", "https://")
        _client = libsql_client.create_client(
            url=http_url,
            auth_token=TURSO_TOKEN
        )
    return _client


async def execute(query, params=None):
    client = await get_client()
    return await client.execute(query, params or [])


async def fetch_one(query, params=None):
    result = await execute(query, params)
    return result.rows[0] if result.rows else None


async def fetch_all(query, params=None):
    result = await execute(query, params)
    return result.rows


async def close():
    global _client
    if _client:
        await _client.close()
        _client = None
