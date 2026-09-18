CREATE TABLE IF NOT EXISTS virtual_keys (
    key_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL,
    rpm_limit INT NOT NULL DEFAULT 120,
    tpm_limit INT NOT NULL DEFAULT 100000,
    budget_limit_usd NUMERIC(10, 4) NOT NULL DEFAULT 1000.0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed production and test keys
INSERT INTO virtual_keys (key_id, organization_id, rpm_limit, tpm_limit, budget_limit_usd, is_active)
VALUES 
    ('sk-gw-tenant-alpha-001', 'org-finance', 120, 100000, 5000.0, TRUE),
    ('sk-gw-tenant-prod-001', 'org-core-ai', 1000, 500000, 10000.0, TRUE),
    ('sk-gw-tenant-revoked-999', 'org-legacy', 60, 50000, 100.0, FALSE)
ON CONFLICT (key_id) DO NOTHING;
