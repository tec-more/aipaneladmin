-- T15 缺陷修复 BUG-T15-002 + BUG-T15-004：workflow_version 增加 description 列（发布说明）
-- 溯源：PublishDialog 前端已收集"版本描述"，序列化路由访问 v.description 但模型缺字段
-- openGauss 兼容（BUG-T15-004）：Oracle 兼容模式下空串 '' 即 NULL，DEFAULT '' 必失败；
-- 改用 nullable 列，序列化层 `v.description or ""` 兜底，契约对外仍表现为字符串
-- 幂等：ADD COLUMN IF NOT EXISTS，可重复执行
ALTER TABLE workflow_version ADD COLUMN IF NOT EXISTS description TEXT NULL;
