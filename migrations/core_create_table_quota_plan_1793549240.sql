-- T1 新增表：quota_plan（统一配额套餐，Q-D；会员等级与后台角色双向映射由服务层维护）
-- 溯源：docs/arch/02 §4.2；01 C-17
CREATE TABLE IF NOT EXISTS quota_plan (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL,
    scope VARCHAR(10) NOT NULL DEFAULT 'both',
    quota_items JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_quota_plan_code ON quota_plan (code);
