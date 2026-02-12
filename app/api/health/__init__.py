from sqlalchemy import text
from app.db.main import async_engine
from app.core.redis import redis_client
import psutil
import shutil
import asyncio



async def check_database():
    try:
        async with asyncio.timeout(2):
            async with async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"


async def check_redis():
    try:
        async with asyncio.timeout(2):
            await redis_client.ping()
        return "up"
    except Exception:
        return "down"


def check_disk():
    total, used, free = shutil.disk_usage("/")
    return {
        "total_gb": round(total / (1024 ** 3), 2),
        "used_gb": round(used / (1024 ** 3), 2),
        "free_gb": round(free / (1024 ** 3), 2),
        "usage_percent": round((used / total) * 100, 2)
    }


def check_memory():
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024 ** 3), 2),
        "used_gb": round(mem.used / (1024 ** 3), 2),
        "available_gb": round(mem.available / (1024 ** 3), 2),
        "usage_percent": mem.percent
    }