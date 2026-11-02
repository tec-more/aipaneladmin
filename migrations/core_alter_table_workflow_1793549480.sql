-- T1 变更表：workflow +owner_type/+owner_id/+visibility/+current_version_id/+schema_version
-- 溯源：docs/arch/02 §4.3；Q4：current_version_id 为 BigInt+索引，不建 DB 级 FK
-- 索引策略 03 §4：(owner_type, owner_id, visibility) / (current_version_id)
-- 幂等：IF EXISTS / IF NOT EXISTS 全量防重
ALTER TABLE IF EXISTS workflow ADD COLUMN IF NOT EXISTS owner_type VARCHAR(3) NOT NULL DEFAULT 'usr';
ALTER TABLE IF EXISTS workflow ADD COLUMN IF NOT EXISTS owner_id BIGINT NULL;
ALTER TABLE IF EXISTS workflow ADD COLUMN IF NOT EXISTS visibility VARCHAR(20) NOT NULL DEFAULT 'private';
ALTER TABLE IF EXISTS workflow ADD COLUMN IF NOT EXISTS current_version_id BIGINT NULL;
ALTER TABLE IF EXISTS workflow ADD COLUMN IF NOT EXISTS schema_version VARCHAR(10) NOT NULL DEFAULT 'v1';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='workflow') THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_workflow_owner ON workflow (owner_type, owner_id, visibility)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_workflow_current_version_id ON workflow (current_version_id)';
    END IF;
END $$;
