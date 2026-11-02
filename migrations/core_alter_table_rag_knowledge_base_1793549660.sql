-- T1 变更表：rag_knowledge_base +owner_type/+owner_id（Q-A 多态归属）
-- 溯源：docs/arch/02 §4.3；C-15 放弃 DB 级 FK；created_by 保留只读
-- 索引策略 03 §4：(owner_type, owner_id) / (is_public)
ALTER TABLE IF EXISTS rag_knowledge_base ADD COLUMN IF NOT EXISTS owner_type VARCHAR(3) NOT NULL DEFAULT 'usr';
ALTER TABLE IF EXISTS rag_knowledge_base ADD COLUMN IF NOT EXISTS owner_id BIGINT NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='rag_knowledge_base') THEN
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rag_kb_owner ON rag_knowledge_base (owner_type, owner_id)';
        EXECUTE 'CREATE INDEX IF NOT EXISTS idx_rag_kb_is_public ON rag_knowledge_base (is_public)';
    END IF;
END $$;
