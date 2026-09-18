from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    
    CLICKHOUSE_HOST: str = "127.0.0.1"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_DB: str = "ai_gateway"

    POSTGRES_URL: str = "postgresql://gateway_admin:gateway_secret@127.0.0.1:5432/gateway_db"

    OPENAI_API_BASE: str = "http://127.0.0.1:8001/v1"
    OPENAI_API_KEY: str = "mock-key"
    UPSTREAM_TIMEOUT_SECONDS: float = 30.0

    MAX_KEEP_ALIVE_CONNS: int = 500
    MAX_CONCURRENT_CONNS: int = 2000

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
