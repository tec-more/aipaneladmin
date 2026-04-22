-- 添加 graph_definition 列到 agent 表
ALTER TABLE agent ADD COLUMN IF NOT EXISTS graph_definition JSONB;

-- 添加注释
COMMENT ON COLUMN agent.graph_definition IS '智能体结构图定义（nodes 和 edges）';
