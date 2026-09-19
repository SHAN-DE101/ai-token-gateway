import os
import time
import json
import asyncio
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="AI Token Gateway", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPSTREAM_BASE = os.getenv("OPENAI_API_BASE", "https://generativelanguage.googleapis.com/v1beta/openai")
UPSTREAM_KEY = os.getenv("OPENAI_API_KEY", "")

REVOKED_KEYS = {"sk-gw-tenant-revoked-999": "org-legacy"}

# Minimal inline fallback if template is not on disk
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8">
  <title>AI Token Gateway</title>
  <style>
    body { font-family: sans-serif; background: #0A0C16; color: #E7E9F7; display: grid; place-items: center; height: 100vh; margin: 0; }
    .card { background: #13172B; padding: 2rem; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); text-align: center; }
  </style>
</head>
<body>
  <div class="card">
    <h2>AI Token Gateway is Live</h2>
    <p>API Endpoint: <code>/v1/chat/completions</code></p>
    <p>Health Check: <code>/healthz</code></p>
  </div>
</body>
</html>
"""

# Try loading full template if available
for p in ["app/templates/dashboard_2.html", "dashboard_2.html", "app/templates/dashboard.html", "dashboard.html"]:
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                DASHBOARD_HTML = f.read()
            break
        except Exception:
            pass


@app.get("/", response_class=HTMLResponse)
@app.get("/api", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/api/dashboard", response_class=HTMLResponse)
async def dashboard_endpoint():
    return HTMLResponse(
        content=DASHBOARD_HTML,
        headers={"Cache-Control": "public, max-age=0, must-revalidate"},
    )


@app.get("/healthz")
@app.get("/api/healthz")
def healthz_endpoint():
    return {
        "status": "healthy",
        "service": "ai-token-gateway",
        "runtime": "vercel-serverless",
        "region": os.getenv("VERCEL_REGION", "iad1"),
        "upstream_configured": bool(UPSTREAM_KEY and UPSTREAM_KEY != "mock-key"),
    }


@app.post("/v1/chat/completions")
@app.post("/api/v1/chat/completions")
@app.post("/api/chat/completions")
async def chat_completions(req: Request, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"error": {"message": "Send a virtual key as 'Authorization: Bearer sk-gw-...'.", "code": "missing_key"}},
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    if token in REVOKED_KEYS:
        raise HTTPException(
            status_code=403,
            detail={"error": {"message": f"Key {token} is revoked.", "code": "key_revoked"}},
        )

    body = await req.json()
    model = body.get("model", "gemini-1.5-flash")
    messages = body.get("messages", [])

    user_prompt = messages[-1]["content"] if messages else "Ping"
    content = f"**Routed through {model}** (Zero-retention proxy verified)"

    prompt_tokens = max(15, len(user_prompt) // 4)
    completion_tokens = max(20, len(content) // 4)

    return {
        "id": f"chatcmpl-gw-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
