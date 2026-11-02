-- T1 存量归属回填（Q-C）+ access_level 收敛（Q3）
-- 1) workflow/agent/workflow_execution 存量 -> owner_type='usr', owner_id=首个在职超管
-- 2) rag_knowledge_base 存量 -> owner_type='usr', owner_id=created_by（空则回退超管）
-- 3) access_level 收敛为 private/public：'dept' 及非法值 -> 'private'（dept 授权已先行写入 resource_grant）
-- 幂等：仅处理 owner_id IS NULL 的行；超管不存在时跳过（保持 NULL 待人工处理并告警）
DO $$
DECLARE
    v_super_id BIGINT;
    v_rows INT := 0;
BEGIN
    SELECT id INTO v_super_id FROM "user" WHERE is_superuser = TRUE AND is_active = TRUE ORDER BY id LIMIT 1;
    IF v_super_id IS NULL THEN
        RAISE WARNING '[T1] 未找到在职超管(is_superuser=TRUE)，workflow/agent/workflow_execution 归属回填跳过，需人工处理';
    END IF;

    -- 1) workflow / agent / workflow_execution -> usr + 超管
    IF v_super_id IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='workflow') THEN
        UPDATE workflow SET owner_type='usr', owner_id=v_super_id WHERE owner_id IS NULL;
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        RAISE NOTICE '[T1] workflow 归属回填行数: %', v_rows;
    END IF;

    IF v_super_id IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='agent') THEN
        UPDATE agent SET owner_type='usr', owner_id=v_super_id WHERE owner_id IS NULL;
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        RAISE NOTICE '[T1] agent 归属回填行数: %', v_rows;
    END IF;

    IF v_super_id IS NOT NULL AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='workflow_execution') THEN
        UPDATE workflow_execution SET owner_type='usr', owner_id=v_super_id WHERE owner_id IS NULL;
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        RAISE NOTICE '[T1] workflow_execution 归属回填行数: %', v_rows;
    END IF;

    -- 2) rag_knowledge_base -> usr + created_by（Q-A/Q-C；FK 列名 created_by_id）
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='rag_knowledge_base') THEN
        IF EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema='public' AND table_name='rag_knowledge_base' AND column_name='created_by_id') THEN
            UPDATE rag_knowledge_base
            SET owner_type='usr',
                owner_id = COALESCE(created_by_id, v_super_id)
            WHERE owner_id IS NULL;
        ELSE
            -- 极端兜底：created_by_id 列不存在时全部回退超管
            UPDATE rag_knowledge_base
            SET owner_type='usr', owner_id = v_super_id
            WHERE owner_id IS NULL;
        END IF;
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        RAISE NOTICE '[T1] rag_knowledge_base 归属回填行数: %', v_rows;

        -- 3) access_level 收敛：dept/非法值 -> private（Q3）
        UPDATE rag_knowledge_base SET access_level='private' WHERE access_level NOT IN ('private', 'public');
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        RAISE NOTICE '[T1] rag_knowledge_base access_level 收敛(dept->private)行数: %', v_rows;
    END IF;
END $$;

-- 迁移报告：各表回填后仍未归属的行数（应为 0，非 0 需人工介入）
SELECT 'workflow' AS tbl, COUNT(*) AS unowned FROM workflow WHERE owner_id IS NULL
UNION ALL
SELECT 'agent', COUNT(*) FROM agent WHERE owner_id IS NULL
UNION ALL
SELECT 'workflow_execution', COUNT(*) FROM workflow_execution WHERE owner_id IS NULL
UNION ALL
SELECT 'rag_knowledge_base', COUNT(*) FROM rag_knowledge_base WHERE owner_id IS NULL;
