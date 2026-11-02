-- T6 新增表：trace_event（执行 Trace 事件流，M10 基础）
-- 溯源：docs/arch/03 §3.3（表结构/批量缓冲/30 天清理）；索引策略 §03-4：(execution_id, seq) 回放 / (created_at) 清理
-- 幂等：IF NOT EXISTS，可重复执行
CREATE TABLE IF NOT EXISTS trace_event (
    id BIGSERIAL PRIMARY KEY,
    execution_id BIGINT NOT NULL,
    seq INT NOT NULL,
    event_type VARCHAR(32) NOT NULL,
    node_id VARCHAR(100) NULL,
    payload JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- (execution_id, seq) 回放分页（cursor=seq 断线补齐）
CREATE INDEX IF NOT EXISTS idx_trace_event_exec_seq ON trace_event (execution_id, seq);
-- (created_at) 每日清理
CREATE INDEX IF NOT EXISTS idx_trace_event_created_at ON trace_event (created_at);
