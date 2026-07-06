-- 审批模块：将「审批规则」合并进「审批流程」
-- 生成时间: 2026-07-07
--
-- 变更说明：
-- 1. approval_flow 增加规则维度字段 model / action / methods / priority
--    （流程本身即审批规则，门禁按 model+action+methods+priority 直接匹配流程）
-- 2. 删除 approval_rule 表（规则概念已合并进流程，不再保留）

-- 1) approval_flow 增加四列（幂等，可重复执行）
ALTER TABLE approval_flow ADD COLUMN IF NOT EXISTS model VARCHAR(50);
ALTER TABLE approval_flow ADD COLUMN IF NOT EXISTS action VARCHAR(50);
ALTER TABLE approval_flow ADD COLUMN IF NOT EXISTS methods JSONB DEFAULT '["POST", "PUT", "DELETE"]'::jsonb;
ALTER TABLE approval_flow ADD COLUMN IF NOT EXISTS priority INT DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_approval_flow_model ON approval_flow(model);
CREATE INDEX IF NOT EXISTS idx_approval_flow_action ON approval_flow(action);
CREATE INDEX IF NOT EXISTS idx_approval_flow_priority ON approval_flow(priority);

-- 旧规则数据无需迁移（用户确认直接删除规则功能），仅把 model 列用 business_type 回填做兜底
UPDATE approval_flow SET model = business_type WHERE model IS NULL AND business_type IS NOT NULL;

-- 2) 删除 approval_rule 表（含索引）
DROP TABLE IF EXISTS approval_rule;
