import asyncpg
import logging
from app.core.config import settings

logger = logging.getLogger("gateway.postgres")

class PostgresManager:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(
                dsn=settings.POSTGRES_URL,
                min_size=5,
                max_size=30,
                max_inactive_connection_lifetime=300
            )
            logger.info("PostgreSQL connection pool initialized.")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")

    async def disconnect(self):
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool terminated.")

pg_manager = PostgresManager()
