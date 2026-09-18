import asyncio
import logging
from app.core.metrics import TELEMETRY_QUEUE_DEPTH

logger = logging.getLogger("gateway.telemetry")

class TelemetryService:
    def __init__(self, ch_manager):
        self.queue = asyncio.Queue(maxsize=50000)
        self.ch_manager = ch_manager
        self._flusher_task = None

    async def start(self):
        self._flusher_task = asyncio.create_task(self._worker())

    async def stop(self):
        if self._flusher_task:
            self._flusher_task.cancel()

    def record_async(self, record: dict):
        try:
            self.queue.put_nowait(record)
            TELEMETRY_QUEUE_DEPTH.set(self.queue.qsize())
        except asyncio.QueueFull:
            logger.warning("Telemetry queue full (50,000). Dropping record.")

    async def _worker(self):
        while True:
            batch = []
            start_time = asyncio.get_event_loop().time()
            
            while len(batch) < 1000 and (asyncio.get_event_loop().time() - start_time) < 0.5:
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=0.05)
                    batch.append(item)
                    self.queue.task_done()
                except asyncio.TimeoutError:
                    break

            if batch:
                TELEMETRY_QUEUE_DEPTH.set(self.queue.qsize())
                try:
                    rows = [
                        [
                            b["event_timestamp"], b["request_id"], b["virtual_key_id"],
                            b["organization_id"], b["provider"], b["model_requested"],
                            b["model_served"], b["is_fallback"], b["prompt_tokens"],
                            b["completion_tokens"], b["total_tokens"], b["cost_usd"],
                            b["latency_ttft_ms"], b["latency_total_ms"], b["status_code"],
                            b["error_code"]
                        ]
                        for b in batch
                    ]
                    self.ch_manager.client.insert("ai_gateway.request_telemetry", rows)
                except Exception as e:
                    logger.error(f"ClickHouse batch ingestion error: {str(e)}")
