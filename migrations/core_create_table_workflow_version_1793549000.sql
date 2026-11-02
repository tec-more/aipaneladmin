-- T1 新增表：workflow_version（工作流发布版本，不可变快照）
-- 溯源：docs/arch/02 §4.2；索引策略 03 §4：UNIQUE(workflow_id, version_no)
-- Q4：workflow_id 建单向 FK；反向 workflow.current_version_id 不建 FK
-- 幂等：IF NOT EXISTS，可重复执行
CREATE TABLE IF NOT EXISTS workflow_version (
    id BIGSERIAL PRIMARY KEY,
    workflow_id BIGINT NOT NULL,
    version_no INT NOT NULL,
    graph_json JSONB NOT NULL,
    schema_version VARCHAR(10) NOT NULL DEFAULT 'v2',
    published_by_type VARCHAR(3) NOT NULL,
    published_by_id BIGINT NOT NULL,
    published_at TIMESTAMPTZ NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'published',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 基表存在时补 FK（openGauss 兼容：用唯一约束内联 UNIQUE 替代部分索引）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='workflow')
       AND NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                       WHERE constraint_name='fk_workflow_version_workflow' AND table_name='workflow_version') THEN
        EXECUTE 'ALTER TABLE workflow_version ADD CONSTRAINT fk_workflow_version_workflow FOREIGN KEY (workflow_id) REFERENCES workflow(id) ON DELETE CASCADE';
    END IF;
END $$;

-- UNIQUE(workflow_id, version_no) 版本定位
CREATE UNIQUE INDEX IF NOT EXISTS uq_workflow_version_wf_no ON workflow_version (workflow_id, version_no);
