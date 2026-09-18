import json
import logging
from typing import Optional, Dict, Any
from app.core.redis import redis_manager
from app.core.postgres import pg_manager

logger = logging.getLogger("gateway.key_manager")

CACHE_TTL_SECONDS = 300

BOOTSTRAP_KEYS = {
    "sk-gw-tenant-alpha-001": {"organization_id": "org-finance", "rpm_limit": 120, "tpm_limit": 100000, "budget_limit_usd": 5000.0, "is_active": True},
    "sk-gw-tenant-prod-001": {"organization_id": "org-core-ai", "rpm_limit": 1000, "tpm_limit": 500000, "budget_limit_usd": 10000.0, "is_active": True},
    "sk-gw-tenant-revoked-999": {"organization_id": "org-legacy", "rpm_limit": 60, "tpm_limit": 50000, "budget_limit_usd": 100.0, "is_active": False}
}

class KeyManager:
    @staticmethod
    async def get_key_metadata(virtual_key: str) -> Optional[Dict[str, Any]]:
        cache_key = f"key_meta:{virtual_key}"
        redis_client = getattr(redis_manager, "client", None)

        # 1. Check L1 Cache in Redis
        if redis_client:
            try:
                cached_data = await redis_client.get(cache_key)
                if cached_data:
                    return json.loads(cached_data)
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        # 2. Check L2 Database in PostgreSQL
        if pg_manager.pool:
            try:
                async with pg_manager.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT key_id, organization_id, rpm_limit, tpm_limit, budget_limit_usd, is_active
                        FROM virtual_keys
                        WHERE key_id = $1
                        """,
                        virtual_key
                    )
                if row:
                    meta = {
                        "key_id": row["key_id"],
                        "organization_id": row["organization_id"],
                        "rpm_limit": row["rpm_limit"],
                        "tpm_limit": row["tpm_limit"],
                        "budget_limit_usd": float(row["budget_limit_usd"]),
                        "is_active": row["is_active"]
                    }
                    if redis_client:
                        try:
                            await redis_client.set(cache_key, json.dumps(meta), ex=CACHE_TTL_SECONDS)
                        except Exception:
                            pass
                    return meta
            except Exception as e:
                logger.error(f"Postgres query error: {e}")

        # 3. Fallback to bootstrap seed keys
        if virtual_key in BOOTSTRAP_KEYS:
            meta = dict(BOOTSTRAP_KEYS[virtual_key])
            meta["key_id"] = virtual_key
            return meta

        return None

    @staticmethod
    async def invalidate_key_cache(virtual_key: str):
        redis_client = getattr(redis_manager, "client", None)
        if redis_client:
            try:
                await redis_client.delete(f"key_meta:{virtual_key}")
            except Exception:
                pass

    @staticmethod
    async def upsert_key(
        virtual_key: str,
        organization_id: str,
        rpm_limit: int = 120,
        tpm_limit: int = 100000,
        budget_limit_usd: float = 1000.0,
        is_active: bool = True
    ):
        if pg_manager.pool:
            async with pg_manager.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO virtual_keys (key_id, organization_id, rpm_limit, tpm_limit, budget_limit_usd, is_active, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
                    ON CONFLICT (key_id) DO UPDATE SET
                        organization_id = EXCLUDED.organization_id,
                        rpm_limit = EXCLUDED.rpm_limit,
                        tpm_limit = EXCLUDED.tpm_limit,
                        budget_limit_usd = EXCLUDED.budget_limit_usd,
                        is_active = EXCLUDED.is_active,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    virtual_key, organization_id, rpm_limit, tpm_limit, budget_limit_usd, is_active
                )
        await KeyManager.invalidate_key_cache(virtual_key)
