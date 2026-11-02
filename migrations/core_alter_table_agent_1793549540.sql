-- T1 变更表：agent +owner_type/+owner_id/+publish_status
-- 溯源：docs/arch/02 §4.3（publish_status: unpublished/published/suspended，M12）
ALTER TABLE IF EXISTS agent ADD COLUMN IF NOT EXISTS owner_type VARCHAR(3) NOT NULL DEFAULT 'usr';
ALTER TABLE IF EXISTS agent ADD COLUMN IF NOT EXISTS owner_id BIGINT NULL;
ALTER TABLE IF EXISTS agent ADD COLUMN IF NOT EXISTS publish_status VARCHAR(20) NOT NULL DEFAULT 'unpublished';
