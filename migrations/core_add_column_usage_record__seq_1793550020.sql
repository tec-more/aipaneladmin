-- D1 补迁移：usage_record 增加 seq 列 + UNIQUE(execution_id,node_id,seq) 幂等键
-- 溯源：docs/arch/06 R-09（结算幂等键 execution_id,node_id,seq）；docs/arch/04 §5.1 seq 全局单调递增
-- 幂等：ADD COLUMN IF NOT EXISTS / CREATE UNIQUE INDEX IF NOT EXISTS，可重复执行
-- openGauss 红线（R-06）：仅使用基础 DDL，无 pgcrypto/ON CONFLICT/GIN/RETURNING
ALTER TABLE usage_record ADD COLUMN IF NOT EXISTS seq BIGINT NOT NULL DEFAULT 0;

CREATE UNIQUE INDEX IF NOT EXISTS uniq_usage_record_execution_node_seq
    ON usage_record (execution_id, node_id, seq);
