-- ============================================================================
-- T1 数据模型与迁移 - 回滚脚本（手工执行，严禁放入 migrations/ 根目录自动执行）
-- 用法：psql/asyncpg 逐条执行；与 T1 前向脚本（时间戳 1793549000~1793549960）一一对应
-- 注意：
--   1. memory 脏数据删除不可逆，前向脚本执行前必须备份：
--      CREATE TABLE memory_backup_t1 AS SELECT * FROM memory;
--   2. identity_link / resource_grant 仅删除"迁移来源"标注的行，不动人工后续产生的数据
--   3. access_level 从 private 无法精确还原 dept（需结合 resource_grant 反推，见末节说明）
-- ============================================================================

-- ---------- 1. 回滚存量数据（先数据后结构，避免 FK 阻碍） ----------

-- 1.1 memory 清洗回滚：仅从备份恢复（无备份则无法恢复）
-- INSERT INTO memory SELECT b.* FROM memory_backup_t1 b
-- WHERE NOT EXISTS (SELECT 1 FROM memory m WHERE m.id = b.id);

-- 1.2 identity_link 存量迁移回滚（仅删迁移标注行）
DELETE FROM identity_link WHERE verified_via = 'migration:legacy';

-- 1.3 resource_grant dept 迁移回滚（仅删迁移标注行）
DELETE FROM resource_grant WHERE granted_by = 'migration:dept_to_grant';

-- 1.4 归属回填回滚：清空 T1 回填的 owner 字段（不影响后续人工/服务层写入的非超管归属）
-- 如需精确还原，请先记录当前 owner_id 分布再执行
UPDATE workflow SET owner_id = NULL, owner_type = 'usr' WHERE owner_type = 'usr';
UPDATE agent SET owner_id = NULL, owner_type = 'usr' WHERE owner_type = 'usr';
UPDATE workflow_execution SET owner_id = NULL, owner_type = 'usr' WHERE owner_type = 'usr';
UPDATE rag_knowledge_base SET owner_id = NULL, owner_type = 'usr' WHERE owner_type = 'usr';
-- 1.5 access_level 还原说明：dept 知识库已被置为 private，如需还原：
-- 通过 resource_grant(granted_by='migration:dept_to_grant') 的 kb 集合可识别原 dept 库，
-- 但成员-部门快照已变化，建议由管理员人工核对后逐个改回，不做脚本自动还原。

-- ---------- 2. 回滚索引 ----------
DROP INDEX IF EXISTS idx_workflow_owner;
DROP INDEX IF EXISTS idx_workflow_current_version_id;
DROP INDEX IF EXISTS idx_workflow_execution_owner;
DROP INDEX IF EXISTS idx_workflow_execution_wf_version;
DROP INDEX IF EXISTS idx_workflow_execution_status;
DROP INDEX IF EXISTS idx_rag_kb_owner;
DROP INDEX IF EXISTS idx_rag_kb_is_public;
DROP INDEX IF EXISTS idx_memory_customer_agent;
DROP INDEX IF EXISTS idx_memory_user_agent;

-- ---------- 3. 回滚变更列 ----------
ALTER TABLE IF EXISTS workflow DROP COLUMN IF EXISTS owner_type;
ALTER TABLE IF EXISTS workflow DROP COLUMN IF EXISTS owner_id;
ALTER TABLE IF EXISTS workflow DROP COLUMN IF EXISTS visibility;
ALTER TABLE IF EXISTS workflow DROP COLUMN IF EXISTS current_version_id;
ALTER TABLE IF EXISTS workflow DROP COLUMN IF EXISTS schema_version;

ALTER TABLE IF EXISTS agent DROP COLUMN IF EXISTS owner_type;
ALTER TABLE IF EXISTS agent DROP COLUMN IF EXISTS owner_id;
ALTER TABLE IF EXISTS agent DROP COLUMN IF EXISTS publish_status;

ALTER TABLE IF EXISTS workflow_execution DROP COLUMN IF EXISTS owner_type;
ALTER TABLE IF EXISTS workflow_execution DROP COLUMN IF EXISTS owner_id;
ALTER TABLE IF EXISTS workflow_execution DROP COLUMN IF EXISTS version_id;

ALTER TABLE IF EXISTS rag_knowledge_base DROP COLUMN IF EXISTS owner_type;
ALTER TABLE IF EXISTS rag_knowledge_base DROP COLUMN IF EXISTS owner_id;

-- ---------- 4. 回滚新增表（依赖序：成员/账户在前） ----------
DROP TABLE IF EXISTS customer_organization_member;
DROP TABLE IF EXISTS customer_organization;
DROP TABLE IF EXISTS identity_link;
DROP TABLE IF EXISTS usage_record;
DROP TABLE IF EXISTS quota_account;
DROP TABLE IF EXISTS quota_plan;
DROP TABLE IF EXISTS resource_grant;
DROP TABLE IF EXISTS workflow_version;
