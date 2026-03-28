-- =====================================================
-- 修复 orders 表的旧字段约束
-- 将旧的会员相关字段改为可空（NULL）
-- =====================================================

-- 修改旧字段为可空
ALTER TABLE orders ALTER COLUMN membership_level_id DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN amount DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN hours DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN bonus_hours DROP NOT NULL;
ALTER TABLE orders ALTER COLUMN total_hours DROP NOT NULL;

-- 新字段已经可以NULL，无需修改
-- total_amount, discount_amount, final_amount

-- 验证修改
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'orders'
AND column_name IN (
    'membership_level_id',
    'amount',
    'hours',
    'bonus_hours',
    'total_hours',
    'total_amount',
    'discount_amount',
    'final_amount'
)
ORDER BY ordinal_position;

SELECT '========== Fields updated successfully ==========' AS "";
