import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from app.api.v1.chat import router as chat_router
from app.api.v1.keys import router as keys_router
from app.core.metrics import metrics_endpoint

# Graceful imports for heavy connectors
try:
    from app.core.redis import redis_manager
except Exception:
    redis_manager = None

try:
    from app.core.postgres import pg_manager
except Exception:
    pg_manager = None

try:
    from app.core.clickhouse import ch_manager
    from app.services.telemetry import TelemetryService
except Exception:
    ch_manager = None
    TelemetryService = None

try:
    from app.services.upstream import upstream_router
except Exception:
    upstream_router = None

telemetry_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global telemetry_service
    if redis_manager:
        try:
            await redis_manager.connect()
        except Exception:
            pass
    if pg_manager:
        try:
            await pg_manager.connect()
        except Exception:
            pass
    if ch_manager and TelemetryService:
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
        if upstream_router:
            await upstream_router.close()
        if pg_manager:
            await pg_manager.disconnect()
        if redis_manager:
            await redis_manager.disconnect()
        if ch_manager:
            ch_manager.disconnect()
    except Exception:
        pass

app = FastAPI(title="Enterprise AI Token Gateway", lifespan=lifespan)
app.include_router(chat_router, prefix="/v1")
app.include_router(keys_router, prefix="/v1")
app.add_route("/metrics", metrics_endpoint)

@app.get("/healthz")
def healthz():
    return {"status": "healthy", "service": "ai-token-gateway"}

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    dashboard_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    if os.path.exists(dashboard_path):
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return f.read()
    return """
    <!DOCTYPE html>
    <html>
    <head><title>AI Token Gateway</title></head>
    <body style="font-family:sans-serif; background:#020617; color:#f8fafc; padding:2rem; text-align:center;">
        <h1 style="color:#38bdf8;">AI Token Gateway is Live on Vercel</h1>
        <p>Endpoints available: <code>/v1/chat/completions</code>, <code>/v1/keys</code>, <code>/metrics</code></p>
        <p><a href="https://github.com/SHAN-DE101/ai-token-gateway" style="color:#818cf8;">View on GitHub</a></p>
    </body>
    </html>
    """

@app.get("/", response_class=HTMLResponse)
async def get_root():
    return '<meta http-equiv="refresh" content="0; url=/dashboard" />'
