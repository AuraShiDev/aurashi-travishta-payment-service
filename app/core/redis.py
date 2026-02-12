# app/core/redis.py
import redis.asyncio as redis
from app.core.config import Config

# Parse redis url
# redis://localhost:6379/0
redis_client = redis.from_url(
    Config.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2
)
