from fastapi import APIRouter
import asyncio
from app.api.health import (
    check_database,
    check_redis,
    check_disk,
    check_memory
)

health_router = APIRouter()
@health_router.get("/")
async def health_check():
    db_status, redis_status = await asyncio.gather(
        check_database(),
        check_redis()
    )

    disk = check_disk()
    memory = check_memory()

    status = "ok"
    if db_status == "down" or redis_status == "down":
        status = "degraded"

    return {
        "status": status,
        "checks": {
            "database": db_status,
            "redis": redis_status,
            "disk": disk,
            "memory": memory
        }
    }