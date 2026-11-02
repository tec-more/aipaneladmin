-- T1 新增表：quota_account（配额账户；Redis 实时计数 + DB 周期对账，03 §3.6）
-- 溯源：docs/arch/02 §4.2；索引策略 03 §4：UNIQUE(owner_type, owner_id)
CREATE TABLE IF NOT EXISTS quota_account (
    id BIGSERIAL PRIMARY KEY,
    owner_type VARCHAR(3) NOT NULL,
    owner_id BIGINT NOT NULL,
    plan_id BIGINT NULL,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    used JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='quota_plan')
       AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                       WHERE constraint_name='fk_quota_account_plan' AND table_name='quota_account') THEN
        EXECUTE 'ALTER TABLE quota_account ADD CONSTRAINT fk_quota_account_plan FOREIGN KEY (plan_id) REFERENCES quota_plan(id) ON DELETE SET NULL';
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_quota_account_owner ON quota_account (owner_type, owner_id);
