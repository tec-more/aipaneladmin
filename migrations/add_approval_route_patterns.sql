-- 审批流程表新增 route_patterns 字段
-- 用于全局审批组件按当前前端路由反查命中的审批流程
-- 采用条件检查防止重复执行报错（幂等）
ALTER TABLE approval_flow ADD COLUMN IF NOT EXISTS route_patterns JSONB DEFAULT '[]';

-- 为已存在的采购审批默认流程补填路由模式（若已存在则跳过）
UPDATE approval_flow
SET route_patterns = '["/panel/purchase/order", "/panel/purchase/order/:id"]'
WHERE code = 'default_purchase_approval'
  AND (route_patterns IS NULL OR route_patterns = '[]' OR route_patterns = 'null');
