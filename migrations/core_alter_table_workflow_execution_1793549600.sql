-- T1 变更表：workflow_execution（架构文档所称 execution 表）+owner_type/+owner_id/+version_id
-- 溯源：docs/arch/02 §4.3；C-08 执行绑定发布版本快照
-- 索引策略 03 §4：(owner_type, owner_id, created_at) / (workflow_id, version_id) / (status, created_at)
ALTER TABLE IF EXISTS workflow_execution ADD COLUMN IF NOT EXISTS owner_type VARCHAR(3) NOT NULL DEFAULT 'usr';
ALTER TABLE IF EXISTS workflow_execution ADD COLUMN IF NOT EXISTS owner_id BIGINT NULL;
ALTER TABLE IF EXISTS workflow_execution ADD COLUMN IF NOT EXISTS version_id BIGINT NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='workflow_execution') THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_workflow_execution_owner ON workflow_execution (owner_type, owner_id, created_at)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_workflow_execution_wf_version ON workflow_execution (workflow_id, version_id)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_workflow_execution_status ON workflow_execution (status, created_at)';
    END IF;
END $$;
