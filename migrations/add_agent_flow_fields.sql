-- 添加智能体流程图相关字段
-- 请在数据库中执行此SQL

ALTER TABLE agent 
ADD COLUMN IF NOT EXISTS flow_status VARCHAR(20) DEFAULT 'draft' NOT NULL;

COMMENT ON COLUMN agent.flow_status IS 'Flow status: draft/active';

ALTER TABLE agent 
ADD COLUMN IF NOT EXISTS flow_data_draft JSONB;

COMMENT ON COLUMN agent.flow_data_draft IS 'Flow data draft';

ALTER TABLE agent 
ADD COLUMN IF NOT EXISTS flow_data_published JSONB;

COMMENT ON COLUMN agent.flow_data_published IS 'Flow data published';
