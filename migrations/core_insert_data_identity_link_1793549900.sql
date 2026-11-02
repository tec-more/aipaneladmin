-- T1 存量迁移（Q-C）：customer.system_user_id 存量 -> identity_link（status='linked'，标注存量迁移来源）
-- 溯源：docs/arch/02 §4.3（system_user_id 废弃为只读）；N2-5
-- 幂等：NOT EXISTS 防重；customer_id/user_id 任一方已存在映射即跳过（D1 唯一性保护）
-- 注意：仅迁移 user 表中真实存在的 user_id，悬空引用跳过并计数告警
DO $$
DECLARE
    v_rows INT := 0;
    v_dangling INT := 0;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='customer')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='identity_link')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='user') THEN

        INSERT INTO identity_link (customer_id, user_id, status, verified_via, verified_at, audit, created_at, updated_at)
        SELECT c.id, c.system_user_id, 'linked', 'migration:legacy', NOW(),
               '[{"event":"legacy_migration","source":"customer.system_user_id","note":"存量自动迁移，按PRD-D8需重新核对"}]'::jsonb,
               NOW(), NOW()
        FROM customer c
        WHERE c.system_user_id IS NOT NULL
          AND EXISTS (SELECT 1 FROM "user" u WHERE u.id = c.system_user_id)
          AND NOT EXISTS (SELECT 1 FROM identity_link il WHERE il.customer_id = c.id OR il.user_id = c.system_user_id);
        GET DIAGNOSTICS v_rows = ROW_COUNT;
        RAISE NOTICE '[T1] identity_link 存量迁移行数: %', v_rows;

        SELECT COUNT(*) INTO v_dangling
        FROM customer c
        WHERE c.system_user_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id = c.system_user_id);
        IF v_dangling > 0 THEN
            RAISE WARNING '[T1] customer.system_user_id 悬空引用(用户不存在) % 行，未迁移，需人工核对', v_dangling;
        END IF;
    END IF;
END $$;

-- 迁移报告：identity_link 存量迁移结果
SELECT COUNT(*) AS t1_identity_link_migrated FROM identity_link WHERE verified_via = 'migration:legacy';
