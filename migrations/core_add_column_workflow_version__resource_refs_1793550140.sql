-- T5/M3：workflow_version 增加 resource_refs 列（发布时资源快照 ID 清单）
-- 溯源：docs/arch/04 F1（发布绑定资源快照ID清单）；T5 任务口径
-- 幂等：ADD COLUMN IF NOT EXISTS，可重复执行；存量行默认空对象
ALTER TABLE workflow_version ADD COLUMN IF NOT EXISTS resource_refs JSONB NULL;
