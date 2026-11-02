-- T1 存量清洗（Q-C）：memory.customer_id 曾错写 user.id 的脏数据
-- 步骤1：按 customer.system_user_id 映射修正（user.id -> 对应 customer.id）
-- 步骤2：无法映射的（customer_id 在 customer 表无对应记录）删除并计数记录
-- 幂等：修正后重跑步骤1为 no-op；步骤2仅删无映射行
-- 注意：本脚本删除不可逆，执行前请备份 memory 表（回滚方案见 migrations/rollback_t1/）
DO $$
DECLARE
    v_fixed INT := 0;
    v_deleted INT := 0;
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='memory')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='public' AND table_name='customer') THEN

        -- 步骤1：错写 user.id -> 按 system_user_id 映射回 customer.id（自映射巧合行不变）
        UPDATE memory m
        SET customer_id = c.id
        FROM customer c
        WHERE m.customer_id IS NOT NULL
          AND c.system_user_id = m.customer_id
          AND c.id <> m.customer_id;
        GET DIAGNOSTICS v_fixed = ROW_COUNT;
        RAISE NOTICE '[T1] memory 脏数据按 system_user_id 映射修正行数: %', v_fixed;

        -- 步骤2：删除无法映射的脏行（customer_id 指向不存在的 customer）
        DELETE FROM memory m
        WHERE m.customer_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM customer c WHERE c.id = m.customer_id);
        GET DIAGNOSTICS v_deleted = ROW_COUNT;
        RAISE NOTICE '[T1] memory 无法映射脏数据删除行数: %', v_deleted;
    END IF;
END $$;

-- 迁移报告：memory 清洗后统计
SELECT
    (SELECT COUNT(*) FROM memory) AS memory_total_after,
    (SELECT COUNT(*) FROM memory WHERE customer_id IS NOT NULL) AS memory_customer_rows,
    (SELECT COUNT(*) FROM memory WHERE user_id IS NOT NULL) AS memory_user_rows;
