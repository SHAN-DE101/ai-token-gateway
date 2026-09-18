import redis.asyncio as aioredis
import logging
from app.core.config import settings

logger = logging.getLogger("gateway.redis")

class RedisManager:
    def __init__(self):
        self.client: aioredis.Redis | None = None

    async def connect(self):
        try:
            self.client = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=50
            )
            await self.client.ping()
            logger.info("Redis connection established.")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")

    async def disconnect(self):
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed.")

redis_manager = RedisManager()
