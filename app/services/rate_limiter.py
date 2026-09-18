import time
from app.core.redis import redis_manager

SLIDING_WINDOW_LUA = """
local key_rpm = KEYS[1]
local key_tpm = KEYS[2]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local max_rpm = tonumber(ARGV[3])
local max_tpm = tonumber(ARGV[4])
local tokens = tonumber(ARGV[5])

local clear_before = now - window
redis.call('ZREMRANGEBYSCORE', key_rpm, 0, clear_before)
redis.call('ZREMRANGEBYSCORE', key_tpm, 0, clear_before)

local current_reqs = redis.call('ZCARD', key_rpm)
if current_reqs >= max_rpm then
    return {0, "RPM_EXCEEDED"}
end

local tpm_entries = redis.call('ZRANGE', key_tpm, 0, -1)
local current_tokens = 0
for i = 1, #tpm_entries do
    local parts = {}
    for match in string.gmatch(tpm_entries[i], "[^:]+") do
        table.insert(parts, match)
    end
    if #parts >= 2 then
        current_tokens = current_tokens + tonumber(parts[2])
    end
end

if (current_tokens + tokens) > max_tpm then
    return {0, "TPM_EXCEEDED"}
end

redis.call('ZADD', key_rpm, now, tostring(now) .. ":" .. tostring(math.random(1000, 9999)))
redis.call('ZADD', key_tpm, now, tostring(now) .. ":" .. tostring(tokens) .. ":" .. tostring(math.random(1000, 9999)))

redis.call('EXPIRE', key_rpm, window + 1)
redis.call('EXPIRE', key_tpm, window + 1)

return {1, "OK"}
"""

class RateLimiter:
    @staticmethod
    async def check_and_reserve(
        virtual_key: str,
        tokens: int,
        rpm_limit: int = 120,
        tpm_limit: int = 100000,
        window: int = 60
    ) -> tuple[bool, str]:
        now = int(time.time())
        key_rpm = f"ratelimit:rpm:{virtual_key}"
        key_tpm = f"ratelimit:tpm:{virtual_key}"

        result = await redis_manager.client.eval(
            SLIDING_WINDOW_LUA,
            2,
            key_rpm,
            key_tpm,
            now,
            window,
            rpm_limit,
            tpm_limit,
            tokens
        )
        return bool(result[0]), result[1]
