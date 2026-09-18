from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
import uuid
import time
import json
import httpx
from datetime import datetime, timezone
import tiktoken

from app.services.rate_limiter import RateLimiter
from app.services.key_manager import KeyManager
from app.services.upstream import upstream_router, COST_TABLE, FALLBACK_CHAIN
from app.core.config import settings
from app.core.metrics import (
    RATE_LIMIT_REJECTIONS_TOTAL,
    TOKENS_PROCESSED_TOTAL,
    TTFT_HISTOGRAM,
    REQUEST_DURATION_HISTOGRAM,
    HTTP_REQUESTS_TOTAL
)

router = APIRouter()
enc = tiktoken.get_encoding("cl100k_base")

@router.post("/chat/completions")
async def chat_completions(request: Request):
    auth_header = request.headers.get("Authorization", "")
    virtual_key = auth_header.replace("Bearer ", "").strip()

    if not virtual_key.startswith("sk-gw-"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Virtual Key must start with 'sk-gw-'"
        )

    # Dynamic Key Lookup (Redis L1 cache -> Postgres L2 DB)
    key_meta = await KeyManager.get_key_metadata(virtual_key)
    if not key_meta:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid virtual key")
    if not key_meta["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Virtual key has been suspended or revoked")

    org_id = key_meta["organization_id"]
    rpm_limit = key_meta["rpm_limit"]
    tpm_limit = key_meta["tpm_limit"]

    body = await request.json()
    is_stream = body.get("stream", False)
    
    prompt_text = "".join([m.get("content", "") for m in body.get("messages", [])])
    est_tokens = len(enc.encode(prompt_text)) + 50

    # Dynamic rate limiting
    allowed, reason = await RateLimiter.check_and_reserve(
        virtual_key=virtual_key,
        tokens=est_tokens,
        rpm_limit=rpm_limit,
        tpm_limit=tpm_limit
    )
    if not allowed:
        RATE_LIMIT_REJECTIONS_TOTAL.labels(virtual_key=virtual_key, reason=reason).inc()
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": {"message": f"Rate limit quota reached: {reason}", "type": "rate_limit_error"}},
            headers={"Retry-After": "60"}
        )

    # 1. Non-streaming Execution
    if not is_stream:
        resp, model_req, model_served, is_fallback, latency_ms = await upstream_router.forward_standard(body, virtual_key)
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
            
        usage = data.get("usage", {})
        p_tokens = usage.get("prompt_tokens", est_tokens)
        c_tokens = usage.get("completion_tokens", 0)
        tot_tokens = usage.get("total_tokens", p_tokens + c_tokens)

        TOKENS_PROCESSED_TOTAL.labels(model_served=model_served, token_type="prompt").inc(p_tokens)
        TOKENS_PROCESSED_TOTAL.labels(model_served=model_served, token_type="completion").inc(c_tokens)

        pricing = COST_TABLE.get(model_served, {"input": 0.0, "output": 0.0})
        cost_usd = round((p_tokens * pricing["input"]) + (c_tokens * pricing["output"]), 6)

        import app.main as main_module
        if main_module.telemetry_service:
            main_module.telemetry_service.record_async({
                "event_timestamp": datetime.now(timezone.utc),
                "request_id": str(uuid.uuid4()),
                "virtual_key_id": virtual_key,
                "organization_id": org_id,
                "provider": "openai",
                "model_requested": model_req,
                "model_served": model_served,
                "is_fallback": is_fallback,
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "total_tokens": tot_tokens,
                "cost_usd": cost_usd,
                "latency_ttft_ms": latency_ms,
                "latency_total_ms": latency_ms,
                "status_code": resp.status_code,
                "error_code": "NONE"
            })
        return JSONResponse(status_code=resp.status_code, content=data)

    # 2. SSE Streaming Execution
    async def sse_stream_generator():
        import app.main as main_module
        t0 = time.perf_counter()
        ttft_recorded = False
        ttft_ms = 0
        completion_chunks = 0
        model_req = body.get("model", "gpt-4o")
        candidate_models = [model_req] + FALLBACK_CHAIN.get(model_req, [])

        client = upstream_router.client
        res = None
        model_served = model_req
        is_fallback = 0

        for idx, candidate in enumerate(candidate_models):
            model_served = candidate
            is_fallback = 1 if idx > 0 else 0
            body_copy = dict(body)
            body_copy["model"] = candidate
            
            req = client.build_request(
                "POST",
                f"{settings.OPENAI_API_BASE.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                json=body_copy,
                timeout=settings.UPSTREAM_TIMEOUT_SECONDS
            )
            try:
                res = await client.send(req, stream=True)
                if res.status_code < 400:
                    break
                await res.aclose()
            except Exception:
                continue

        try:
            async for chunk in res.aiter_raw():
                if not ttft_recorded and chunk:
                    ttft_ms = int((time.perf_counter() - t0) * 1000)
                    ttft_recorded = True
                    TTFT_HISTOGRAM.labels(model_served=model_served).observe(ttft_ms / 1000.0)
                completion_chunks += 1
                yield chunk
        finally:
            await res.aclose()
            total_latency = int((time.perf_counter() - t0) * 1000)
            REQUEST_DURATION_HISTOGRAM.labels(model_served=model_served).observe(total_latency / 1000.0)
            HTTP_REQUESTS_TOTAL.labels(
                virtual_key=virtual_key,
                model_requested=model_req,
                model_served=model_served,
                status_code=str(res.status_code),
                is_fallback=str(is_fallback)
            ).inc()

            c_tokens = max(completion_chunks, 1)
            TOKENS_PROCESSED_TOTAL.labels(model_served=model_served, token_type="prompt").inc(est_tokens)
            TOKENS_PROCESSED_TOTAL.labels(model_served=model_served, token_type="completion").inc(c_tokens)

            pricing = COST_TABLE.get(model_served, {"input": 0.0, "output": 0.0})
            cost_usd = round((est_tokens * pricing["input"]) + (c_tokens * pricing["output"]), 6)

            if main_module.telemetry_service:
                main_module.telemetry_service.record_async({
                    "event_timestamp": datetime.now(timezone.utc),
                    "request_id": str(uuid.uuid4()),
                    "virtual_key_id": virtual_key,
                    "organization_id": org_id,
                    "provider": "openai",
                    "model_requested": model_req,
                    "model_served": model_served,
                    "is_fallback": is_fallback,
                    "prompt_tokens": est_tokens,
                    "completion_tokens": c_tokens,
                    "total_tokens": est_tokens + c_tokens,
                    "cost_usd": cost_usd,
                    "latency_ttft_ms": ttft_ms if ttft_ms > 0 else total_latency,
                    "latency_total_ms": total_latency,
                    "status_code": res.status_code,
                    "error_code": "NONE"
                })

    return StreamingResponse(sse_stream_generator(), media_type="text/event-stream")
