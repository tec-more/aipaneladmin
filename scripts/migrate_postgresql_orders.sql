-- =====================================================
-- PostgreSQL 订单系统迁移SQL脚本
-- 功能：将 customer_order 表迁移到 orders + order_items 结构
-- 数据库：PostgreSQL 9.6+
-- =====================================================

-- =====================================================
-- Step 1: 备份原表
-- =====================================================
CREATE TABLE IF NOT EXISTS customer_order_backup AS
SELECT * FROM customer_order;

-- =====================================================
-- Step 2: 删除旧的空表（如果存在）
-- =====================================================
DROP TABLE IF EXISTS "order" CASCADE;

-- =====================================================
-- Step 3: 重命名主表
-- =====================================================
ALTER TABLE customer_order RENAME TO orders;

-- =====================================================
-- Step 4: 创建订单明细表
-- =====================================================
CREATE TABLE IF NOT EXISTS order_items (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT,
    product_name VARCHAR(255) NOT NULL,
    product_type VARCHAR(50) NOT NULL,
    product_image VARCHAR(500),
    quantity INTEGER DEFAULT 1 NOT NULL,
    unit_price NUMERIC(10,2) NOT NULL,
    total_price NUMERIC(10,2) NOT NULL,
    extra_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_order_items_order_id
        FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_order_items_product_type
    ON order_items(product_type);

-- =====================================================
-- Step 5: 添加新字段到 orders 表
-- =====================================================
DO $$
BEGIN
    -- 添加 total_amount 字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'total_amount'
    ) THEN
        ALTER TABLE orders ADD COLUMN total_amount NUMERIC(10,2);
    END IF;

    -- 添加 discount_amount 字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'discount_amount'
    ) THEN
        ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10,2) DEFAULT 0;
    END IF;

    -- 添加 final_amount 字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'final_amount'
    ) THEN
        ALTER TABLE orders ADD COLUMN final_amount NUMERIC(10,2);
    END IF;
END $$;

-- =====================================================
-- Step 6: 迁移数据到 order_items 表
-- =====================================================
INSERT INTO order_items (
    order_id,
    product_id,
    product_name,
    product_type,
    product_image,
    quantity,
    unit_price,
    total_price,
    extra_info,
    created_at,
    updated_at
)
SELECT
    co.id AS order_id,
    NULL::BIGINT AS product_id,
    COALESCE(ml.name, 'Unknown') AS product_name,
    'membership'::VARCHAR(50) AS product_type,
    NULL::VARCHAR(500) AS product_image,
    1 AS quantity,
    co.amount AS unit_price,
    co.amount AS total_price,
    jsonb_build_object(
        'membership_level_id', co.membership_level_id,
        'membership_level_name', ml.name,
        'hours', co.hours,
        'bonus_hours', co.bonus_hours,
        'total_hours', co.total_hours
    ) AS extra_info,
    co.created_at,
    co.updated_at
FROM orders co
LEFT JOIN customer_membership_level ml
    ON co.membership_level_id = ml.id
WHERE NOT EXISTS (
    SELECT 1 FROM order_items
    WHERE order_id = co.id
);

-- =====================================================
-- Step 7: 更新 orders 表的金额字段
-- =====================================================
UPDATE orders
SET
    total_amount = amount,
    discount_amount = 0,
    final_amount = amount
WHERE total_amount IS NULL
OR final_amount IS NULL;

-- =====================================================
-- Step 8: 验证迁移结果
-- =====================================================
-- 显示验证结果
SELECT '========== Migration Verification ==========' AS "";

SELECT
    'Orders table:' AS description,
    COUNT(*)::TEXT AS count
FROM orders
UNION ALL
SELECT
    'Order items table:' AS description,
    COUNT(*)::TEXT AS count
FROM order_items;

SELECT '' AS "";
SELECT '========== Orders Missing Items ==========' AS "";

SELECT
    id,
    order_no,
    'Missing order items' AS issue
FROM orders co
WHERE NOT EXISTS (
    SELECT 1 FROM order_items
    WHERE order_id = co.id
)
LIMIT 10;

SELECT '' AS "";
SELECT '========== Sample Data (First 5) ==========' AS "";

SELECT
    oi.id,
    oi.order_id,
    oi.product_name,
    oi.quantity,
    oi.unit_price,
    oi.extra_info
FROM order_items oi
ORDER BY oi.id
LIMIT 5;

-- =====================================================
-- 完成
-- =====================================================
SELECT '========== Migration Completed Successfully ==========' AS "";
