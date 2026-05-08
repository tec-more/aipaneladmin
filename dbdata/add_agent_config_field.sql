-- 为 agent 表添加 config 字段
-- 添加 config JSON 字段用于存储 agent 的配置（技能等）

ALTER TABLE agent ADD COLUMN IF NOT EXISTS config JSONB DEFAULT NULL;

COMMENT ON COLUMN agent.config IS 'Agent configuration (skills, tools, etc.)';
