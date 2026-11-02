-- T1 新增表：usage_record（计量流水，M6/M2 上报；保留 13 个月对账，03 §3.6）
-- 溯源：docs/arch/02 §4.2；PRD §7.3（计量精确到 用户+工作流+节点）
-- 索引策略 03 §4：(owner_type, owner_id, created_at) / (execution_id)
CREATE TABLE IF NOT EXISTS usage_record (
    id BIGSERIAL PRIMARY KEY,
    owner_type VARCHAR(3) NOT NULL,
    owner_id BIGINT NOT NULL,
    execution_id BIGINT NULL,
    node_id VARCHAR(100) NULL,
    resource_type VARCHAR(50) NOT NULL,
    amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    tokens_in BIGINT NOT NULL DEFAULT 0,
    tokens_out BIGINT NOT NULL DEFAULT 0,
    cost NUMERIC(12,6) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_usage_record_owner ON usage_record (owner_type, owner_id, created_at);
CREATE INDEX IF NOT EXISTS idx_usage_record_execution ON usage_record (execution_id);
