-- T5/M3：workflow 增加 draft_version 乐观锁列（草稿保存并发控制）
-- 溯源：docs/arch/04 F1（乐观锁: draft_ver）、§2.1 PUT /v1/u/workflows/{id}/draft
-- 幂等：ADD COLUMN IF NOT EXISTS，可重复执行；存量行默认 1
ALTER TABLE workflow ADD COLUMN IF NOT EXISTS draft_version INTEGER NOT NULL DEFAULT 1;
