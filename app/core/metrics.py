from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

HTTP_REQUESTS_TOTAL = Counter(
    "gateway_requests_total",
    "Total requests processed by the gateway",
    ["virtual_key", "model_requested", "model_served", "status_code", "is_fallback"]
)

REQUEST_DURATION_HISTOGRAM = Histogram(
    "gateway_request_duration_seconds",
    "End-to-end request latency in seconds",
    ["model_served"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

TTFT_HISTOGRAM = Histogram(
    "gateway_ttft_seconds",
    "Time to first token in seconds for streaming responses",
    ["model_served"],
    buckets=[0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0]
)

TOKENS_PROCESSED_TOTAL = Counter(
    "gateway_tokens_total",
    "Total tokens billed and processed",
    ["model_served", "token_type"]
)

RATE_LIMIT_REJECTIONS_TOTAL = Counter(
    "gateway_rate_limit_rejections_total",
    "Total requests rejected by rate limiting",
    ["virtual_key", "reason"]
)

TELEMETRY_QUEUE_DEPTH = Gauge(
    "gateway_telemetry_queue_depth",
    "Current number of pending telemetry events in the background buffer"
)

def metrics_endpoint():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
