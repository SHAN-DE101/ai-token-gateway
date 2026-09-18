from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Token Gateway"
    VERSION: str = "1.0.0"
    
    # Upstream AI
    OPENAI_API_KEY: str = "mock-key"
    OPENAI_API_BASE: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    UPSTREAM_TIMEOUT_SECONDS: float = 30.0
    MAX_KEEP_ALIVE_CONNS: int = 20
    MAX_CONCURRENT_CONNS: int = 100
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Postgres
    POSTGRES_URL: Optional[str] = None
    POSTGRES_USER: str = "gateway_user"
    POSTGRES_PASSWORD: str = "gateway_pass"
    POSTGRES_DB: str = "gateway_catalog"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    
    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DATABASE: str = "ai_gateway"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
