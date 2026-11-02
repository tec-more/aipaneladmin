-- T6/M2：workflow_execution 增加 kind 列（run/dry_run 执行类别标记）
-- 溯源：docs/arch/04 F2（试跑标记 execution.kind=dry_run，可筛选）；§2.1 GET /v1/u/executions kind 过滤
-- 幂等：ADD COLUMN IF NOT EXISTS，可重复执行；存量行默认 run
ALTER TABLE workflow_execution ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'run';
