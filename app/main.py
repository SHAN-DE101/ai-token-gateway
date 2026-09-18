import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from app.core.redis import redis_manager
from app.core.postgres import pg_manager
from app.core.clickhouse import ch_manager
from app.services.telemetry import TelemetryService
from app.services.upstream import upstream_router
from app.api.v1.chat import router as chat_router
from app.api.v1.keys import router as keys_router
from app.core.metrics import metrics_endpoint

telemetry_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telemetry_service
    # Gracefully attempt connections; fallback cleanly if cloud services are unconfigured
    try:
        await redis_manager.connect()
    except Exception:
        pass
    try:
        await pg_manager.connect()
    except Exception:
        pass
    try:
        ch_manager.connect()
        telemetry_service = TelemetryService(ch_manager)
        await telemetry_service.start()
    except Exception:
        pass
    yield
    try:
        if telemetry_service:
            await telemetry_service.stop()
        await upstream_router.close()
        await pg_manager.disconnect()
        await redis_manager.disconnect()
        ch_manager.disconnect()
    except Exception:
        pass

app = FastAPI(title="Enterprise AI Token Gateway", lifespan=lifespan)
app.include_router(chat_router, prefix="/v1")
app.include_router(keys_router, prefix="/v1")
app.add_route("/metrics", metrics_endpoint)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r") as f:
            return f.read()
    return "<h1>Dashboard template not found.</h1>"

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return '<meta http-equiv="refresh" content="0; url=/dashboard" />'
