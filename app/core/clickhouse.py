import clickhouse_connect
from app.core.config import settings

class ClickHouseManager:
    def __init__(self):
        self.client = None

    def connect(self):
        self.client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USER,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DB
        )

    def disconnect(self):
        if self.client:
            self.client.close()

ch_manager = ClickHouseManager()
