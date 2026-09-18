-- KEYS[1]: virtual_key:rpm
-- KEYS[2]: virtual_key:tpm
-- ARGV[1]: current_timestamp (seconds)
-- ARGV[2]: max_rpm
-- ARGV[3]: max_tpm
-- ARGV[4]: estimated_tokens
-- ARGV[5]: window (seconds, usually 60)

local now = tonumber(ARGV[1])
local max_rpm = tonumber(ARGV[2])
local max_tpm = tonumber(ARGV[3])
local est_tokens = tonumber(ARGV[4])
local window = tonumber(ARGV[5])
local clear_before = now - window

-- 1. Evict entries outside the sliding 60s window
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', clear_before)
redis.call('ZREMRANGEBYSCORE', KEYS[2], '-inf', clear_before)

-- 2. Validate RPM limit
local current_rpm = redis.call('ZCARD', KEYS[1])
if current_rpm >= max_rpm then
    return {0, "RPM_EXCEEDED"}
end

-- 3. Calculate sum of tokens in sliding TPM window
local tpm_entries = redis.call('ZRANGE', KEYS[2], 0, -1)
local current_tpm = 0
for _, entry in ipairs(tpm_entries) do
    local _, _, tokens = string.find(entry, ":(%d+)$")
    if tokens then
        current_tpm = current_tpm + tonumber(tokens)
    end
end

if (current_tpm + est_tokens) > max_tpm then
    return {0, "TPM_EXCEEDED"}
end

-- 4. Atomically commit usage & set TTL
local req_id = redis.call('INCR', 'gw:global_seq')
redis.call('ZADD', KEYS[1], now, req_id)
redis.call('ZADD', KEYS[2], now, req_id .. ":" .. est_tokens)
redis.call('EXPIRE', KEYS[1], window + 1)
redis.call('EXPIRE', KEYS[2], window + 1)

return {1, "ALLOWED"}
