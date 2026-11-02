-- T1 新增表：resource_grant（M8 资源授权核心，Q1：base/common/authz）
-- 溯源：docs/arch/02 §4.2；PRD §7.2
-- 索引策略 03 §4：UNIQUE(owner_type, owner_id, resource_type, resource_id) / (resource_type, resource_id)
CREATE TABLE IF NOT EXISTS resource_grant (
    id BIGSERIAL PRIMARY KEY,
    owner_type VARCHAR(3) NOT NULL,
    owner_id BIGINT NOT NULL,
    resource_type VARCHAR(20) NOT NULL,
    resource_id VARCHAR(64) NOT NULL,
    effect VARCHAR(10) NOT NULL DEFAULT 'allow',
    granted_by VARCHAR(64) NOT NULL DEFAULT 'admin',
    expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_resource_grant_quad ON resource_grant (owner_type, owner_id, resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_resource_grant_resource ON resource_grant (resource_type, resource_id);
