-- T1 存量迁移（Q3）：access_level='dept' 知识库 -> 为 visible_departments 关联部门下
-- 每个在职用户写入 resource_grant（owner_type='usr', resource_type='kb', granted_by 标注迁移来源）
-- 必须在 access_level 收敛（core_update_data_owner_backfill）之前执行（时间戳更小）
-- 行为变化（交付物注明）：此后新部门成员不再自动获得授权，需管理员维护 resource_grant
-- 幂等：NOT EXISTS 防重，可重复执行
DO $$
DECLARE
    v_rows INT := 0;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='rag_knowledge_base')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='rag_knowledge_base_department')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='resource_grant')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='user') THEN

        INSERT INTO resource_grant (owner_type, owner_id, resource_type, resource_id, effect, granted_by, created_at, updated_at)
        SELECT DISTINCT 'usr', u.id, 'kb', kb.id::text, 'allow', 'migration:dept_to_grant', NOW(), NOW()
        FROM rag_knowledge_base kb
        JOIN rag_knowledge_base_department kbd ON kbd.rag_knowledge_base_id = kb.id
        JOIN "user" u ON u.dept_id = kbd.department_id AND u.is_active = TRUE
        WHERE kb.access_level = 'dept'
          AND NOT EXISTS (
              SELECT 1 FROM resource_grant g
              WHERE g.owner_type = 'usr' AND g.owner_id = u.id
                AND g.resource_type = 'kb' AND g.resource_id = kb.id::text
          );
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        RAISE NOTICE '[T1] Q3 dept->resource_grant 迁移生成行数: %', v_rows;
    END IF;
END $$;

-- 迁移报告：resource_grant 中迁移来源行总数
SELECT COUNT(*) AS t1_dept_grant_total FROM resource_grant WHERE granted_by = 'migration:dept_to_grant';
