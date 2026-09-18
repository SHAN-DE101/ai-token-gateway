import httpx
import time
import logging
from typing import Tuple, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger("gateway.upstream")

# Universal Model Pricing Table (USD per token)
UNIVERSAL_COST_TABLE: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 0.000005, "output": 0.000015},
    "gpt-4o-mini": {"input": 0.00000015, "output": 0.0000006},
    "o1-preview": {"input": 0.000015, "output": 0.000060},

    # Google Gemini
    "gemini-1.5-pro": {"input": 0.0000035, "output": 0.0000105},
    "gemini-1.5-flash": {"input": 0.000000075, "output": 0.0000003},
    "gemini-2.0-flash": {"input": 0.0000001, "output": 0.0000004},

    # Anthropic
    "claude-3-5-sonnet": {"input": 0.000003, "output": 0.000015},
    "claude-3-5-haiku": {"input": 0.0000008, "output": 0.000004},

    # Open Source (vLLM / Ollama / Groq / DeepSeek / Meta)
    "meta-llama/llama-3.3-70b-instruct": {"input": 0.00000059, "output": 0.00000079},
    "deepseek-ai/deepseek-v3": {"input": 0.00000014, "output": 0.00000028},
    "deepseek-ai/deepseek-r1": {"input": 0.00000055, "output": 0.00000219},
    "qwen/qwen-2.5-72b-instruct": {"input": 0.00000035, "output": 0.00000040},
    "mistralai/mistral-large": {"input": 0.000002, "output": 0.000006},

    # Fallback default for any arbitrary model in the world
    "default": {"input": 0.000001, "output": 0.000002}
}

UNIVERSAL_FALLBACK_CHAIN: Dict[str, List[str]] = {
    "gpt-4o": ["gemini-1.5-pro", "meta-llama/llama-3.3-70b-instruct", "gpt-4o-mini"],
    "claude-3-5-sonnet": ["gemini-1.5-pro", "gpt-4o", "deepseek-ai/deepseek-v3"],
    "gpt-4o-failing": ["gemini-1.5-pro", "gpt-4o-mini"]
}

# Aliases for backwards compatibility with chat.py
COST_TABLE = UNIVERSAL_COST_TABLE
FALLBACK_CHAIN = UNIVERSAL_FALLBACK_CHAIN

class UpstreamRouter:
    def __init__(self):
        self.limits = httpx.Limits(
            max_keepalive_connections=settings.MAX_KEEP_ALIVE_CONNS,
            max_connections=settings.MAX_CONCURRENT_CONNS,
            keepalive_expiry=30.0
        )
        self.client = httpx.AsyncClient(limits=self.limits, http2=True)

    async def close(self):
        await self.client.aclose()

    def resolve_provider_and_url(self, model: str) -> Tuple[str, str, Dict[str, str]]:
        url = f"{settings.OPENAI_API_BASE.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        provider = "openai"
        if "gemini" in model.lower():
            provider = "google"
        elif "claude" in model.lower():
            provider = "anthropic"
        elif any(oss in model.lower() for oss in ["llama", "deepseek", "qwen", "mistral"]):
            provider = "open-source"

        return provider, url, headers

    async def forward_standard(self, payload: Dict[str, Any], virtual_key: str) -> Tuple[httpx.Response, str, str, int, int]:
        model_req = payload.get("model", "gpt-4o")
        candidate_models = [model_req] + UNIVERSAL_FALLBACK_CHAIN.get(model_req, [])

        t0 = time.perf_counter()
        resp = None
        model_served = model_req
        is_fallback = 0

        for idx, candidate in enumerate(candidate_models):
            model_served = candidate
            is_fallback = 1 if idx > 0 else 0

            payload_copy = dict(payload)
            payload_copy["model"] = candidate

            provider, url, headers = self.resolve_provider_and_url(candidate)

            try:
                resp = await self.client.post(
                    url,
                    headers=headers,
                    json=payload_copy,
                    timeout=settings.UPSTREAM_TIMEOUT_SECONDS
                )
                if resp.status_code < 400:
                    break
                logger.warning(f"Model {candidate} failed with {resp.status_code}. Cascading down...")
            except Exception as e:
                logger.warning(f"Connection to {candidate} error: {e}. Cascading...")

        total_latency = int((time.perf_counter() - t0) * 1000)
        return resp, model_req, model_served, is_fallback, total_latency

upstream_router = UpstreamRouter()
