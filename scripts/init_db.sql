CREATE DATABASE IF NOT EXISTS ai_gateway;

CREATE TABLE IF NOT EXISTS ai_gateway.request_telemetry (
    event_timestamp DateTime64(3, 'UTC') CODEC (DoubleDelta, ZSTD(1)),
    request_id UUID,
    virtual_key_id LowCardinality(String),
    organization_id LowCardinality(String),
    provider LowCardinality(String),
    model_requested LowCardinality(String),
    model_served LowCardinality(String),
    is_fallback UInt8,
    prompt_tokens UInt32,
    completion_tokens UInt32,
    total_tokens UInt32,
    cost_usd Decimal64(6),
    latency_ttft_ms UInt32,
    latency_total_ms UInt32,
    status_code UInt16,
    error_code LowCardinality(String)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_timestamp)
ORDER BY (organization_id, virtual_key_id, provider, event_timestamp);
