# PostgreSQL 订单系统迁移指南

## 📋 概述

本文档说明如何将旧的单一订单表（`customer_order`）迁移到新的订单主表+明细表结构（`orders` + `order_items`）。

**数据库类型**: PostgreSQL
**迁移类型**: 表重命名 + 数据迁移
**风险等级**: 低（有完整备份）

---

## 🎯 迁移目标

### **旧结构**
```
customer_order 表（单表）
- 存储所有订单信息
- 直接关联 membership_level
- 包含 hours, bonus_hours 等会员专用字段
```

### **新结构**
```
orders 表（订单主表）
- 存储订单基本信息和支付状态
- 支持多种商品类型

order_items 表（订单明细表）
- 存储订单中的每个商品
- 支持一个订单多个商品
- extra_info 字段存储扩展信息（JSONB）
```

---

## 📊 迁移步骤

### **前置准备**

#### 1. 确认当前表结构
```sql
-- 查看当前订单表
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND (table_name LIKE '%order%' OR table_name LIKE '%customer%')
ORDER BY table_name;
```

#### 2. 备份数据库（重要！）
```bash
# 使用 pg_dump 备份
pg_dump -h 127.0.0.1 -U admin -d aipaneladmin > backup_$(date +%Y%m%d_%H%M%S).sql

# 或只备份订单相关表
pg_dump -h 127.0.0.1 -U admin -d aipaneladmin -t customer_order > backup_customer_order.sql
```

---

### **执行迁移**

#### 方式一：使用自动化脚本（推荐）⭐

```bash
# 执行迁移脚本
python scripts/migrate_postgresql_orders.py
```

脚本会自动完成：
1. ✅ 备份原表
2. ✅ 重命名表
3. ✅ 创建新表
4. ✅ 添加新字段
5. ✅ 迁移数据
6. ✅ 验证结果

#### 方式二：手动执行SQL

##### 步骤1: 备份原表
```sql
-- 创建备份表
CREATE TABLE customer_order_backup AS
SELECT * FROM customer_order;
```

##### 步骤2: 删除旧的空表（如果存在）
```sql
DROP TABLE IF EXISTS "order" CASCADE;
```

##### 步骤3: 重命名主表
```sql
-- 将 customer_order 重命名为 orders
ALTER TABLE customer_order RENAME TO orders;
```

##### 步骤4: 创建明细表
```sql
-- 创建 order_items 表
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
```

##### 步骤5: 添加新字段
```sql
-- 添加金额字段到 orders 表
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'total_amount'
    ) THEN
        ALTER TABLE orders ADD COLUMN total_amount NUMERIC(10,2);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'discount_amount'
    ) THEN
        ALTER TABLE orders ADD COLUMN discount_amount NUMERIC(10,2) DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'orders'
        AND column_name = 'final_amount'
    ) THEN
        ALTER TABLE orders ADD COLUMN final_amount NUMERIC(10,2);
    END IF;
END $$;
```

##### 步骤6: 迁移数据到明细表
```sql
-- 从 orders 表迁移数据到 order_items 表
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
```

##### 步骤7: 更新金额字段
```sql
-- 更新 orders 表的金额字段
UPDATE orders
SET
    total_amount = amount,
    discount_amount = 0,
    final_amount = amount
WHERE total_amount IS NULL
OR final_amount IS NULL;
```

##### 步骤8: 验证迁移结果
```sql
-- 检查记录数
SELECT
    'Orders count:' as description,
    COUNT(*)::TEXT as count
FROM orders
UNION ALL
SELECT
    'Order items count:' as description,
    COUNT(*)::TEXT as count
FROM order_items;

-- 检查缺失明细的订单
SELECT
    id,
    order_no,
    'Missing order items' as issue
FROM orders co
WHERE NOT EXISTS (
    SELECT 1 FROM order_items
    WHERE order_id = co.id
)
LIMIT 10;

-- 查看迁移样本
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
```

---

## 🔍 验证检查清单

迁移完成后，请确认以下各项：

- [ ] `orders` 表存在且数据完整
- [ ] `order_items` 表存在且有数据
- [ ] `customer_order_backup` 备份表存在
- [ ] 所有订单都有对应的明细记录
- [ ] `extra_info` 字段包含正确的会员信息
- [ ] 金额字段（total_amount, final_amount）已填充
- [ ] 外键关系正确（order_items.order_id → orders.id）

---

## 📊 新表结构说明

### **orders 表（订单主表）**

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| id | BIGSERIAL | 主键 | 1 |
| order_no | VARCHAR(64) | 订单号 | ORD20260327... |
| customer_id | BIGINT | 客户ID | 1 |
| total_amount | NUMERIC(10,2) | 订单总金额 | 15.00 |
| discount_amount | NUMERIC(10,2) | 优惠金额 | 0.00 |
| final_amount | NUMERIC(10,2) | 实付金额 | 15.00 |
| payment_method | VARCHAR(20) | 支付方式 | wechat/alipay |
| payment_status | VARCHAR(20) | 支付状态 | pending/paid/... |
| trade_no | VARCHAR(128) | 第三方交易号 | wx123456... |
| pay_time | TIMESTAMP | 支付时间 | 2026-03-27 16:00:00 |
| expire_time | TIMESTAMP | 订单过期时间 | 2026-03-27 16:15:00 |
| membership_level_id | BIGINT | 会员等级ID（保留） | 2 |
| hours | INTEGER | 购买小时数（保留） | 100 |
| bonus_hours | INTEGER | 赠送小时数（保留） | 20 |
| total_hours | INTEGER | 总小时数（保留） | 120 |
| amount | NUMERIC(10,2) | 原金额字段（保留） | 15.00 |
| client_ip | VARCHAR(50) | 客户端IP | 192.168.1.100 |
| device_info | JSONB | 设备信息 | {...} |
| remark | TEXT | 备注 | 订单备注 |
| created_at | TIMESTAMP | 创建时间 | 自动生成 |
| updated_at | TIMESTAMP | 更新时间 | 自动更新 |

### **order_items 表（订单明细表）**

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| id | BIGSERIAL | 主键 | 1 |
| order_id | BIGINT | 订单ID（外键） | 1 |
| product_id | BIGINT | 产品ID | NULL |
| product_name | VARCHAR(255) | 产品名称（冗余） | SVIP会员 |
| product_type | VARCHAR(50) | 产品类型 | membership/points/item |
| product_image | VARCHAR(500) | 产品图片 | /image.jpg |
| quantity | INTEGER | 购买数量 | 1 |
| unit_price | NUMERIC(10,2) | 单价 | 15.00 |
| total_price | NUMERIC(10,2) | 小计 | 15.00 |
| extra_info | JSONB | 扩展信息 | {"hours": 100, ...} |
| created_at | TIMESTAMP | 创建时间 | 自动生成 |
| updated_at | TIMESTAMP | 更新时间 | 自动更新 |

**extra_info JSONB 字段示例**：
```json
{
  "membership_level_id": 1,
  "membership_level_name": "SVIP",
  "hours": 100,
  "bonus_hours": 20,
  "total_hours": 120,
  "recharge_type": "monthly"
}
```

---

## ⚠️ 注意事项

1. **生产环境必须先备份**
2. **迁移期间暂停订单相关功能**
3. **验证成功后再删除备份表**（建议保留至少一周）
4. **如果迁移失败，可以使用以下命令回滚**：
   ```sql
   -- 回滚：恢复原表
   DROP TABLE IF EXISTS orders CASCADE;
   DROP TABLE IF EXISTS order_items CASCADE;
   ALTER TABLE customer_order_backup RENAME TO customer_order;
   ```

---

## 🔧 相关文件

- **迁移脚本**: `scripts/migrate_postgresql_orders.py`
- **SQL脚本**: `scripts/migrate_postgresql_orders.sql`
- **模型定义**: `base/plugins/order/models/order.py`
- **迁移文档**: `docs/postgresql_migration.md`

---

**文档版本**: v1.0
**创建日期**: 2026-03-27
**适用数据库**: PostgreSQL 9.6+
