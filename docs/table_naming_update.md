# 订单表名统一说明

## 📋 表名变更

为了统一和简化命名，订单系统的表名已更新如下：

| 旧表名 | 新表名 | 说明 |
|--------|--------|------|
| `customer_order` | `orders` | 订单主表 |
| `order_item` | `order_items` | 订单明细表 |

---

## 🔄 已更新的文件

### **1. 模型定义**
- ✅ `base/plugins/order/models/order.py`
  - CustomerOrder.Meta.table = "orders"
  - OrderItem.Meta.table = "order_items"

### **2. 迁移脚本**
- ✅ `scripts/migrate_orders.sql`
- ✅ `scripts/migrate_orders_simple.py`
- ✅ `scripts/migrate_orders_flexible.py`

### **3. 文档**
- ✅ `docs/order_migration.md`
- ✅ `docs/order_api_usage.md`
- ✅ `docs/table_naming_update.md` (本文档)

---

## 📊 新表结构

### **orders（订单主表）**
```sql
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(64) UNIQUE NOT NULL,
    customer_id INT NOT NULL,
    total_amount DECIMAL(10,2) NOT NULL,
    discount_amount DECIMAL(10,2) DEFAULT 0,
    final_amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    payment_status VARCHAR(20) DEFAULT 'pending',
    trade_no VARCHAR(128),
    pay_time DATETIME,
    expire_time DATETIME NOT NULL,
    client_ip VARCHAR(50),
    device_info JSON,
    remark TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_customer_id (customer_id),
    INDEX idx_order_no (order_no),
    INDEX idx_payment_status (payment_status),
    INDEX idx_created_at (created_at)
);
```

### **order_items（订单明细表）**
```sql
CREATE TABLE order_items (
    id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    product_id INT,
    product_name VARCHAR(255) NOT NULL,
    product_type VARCHAR(50) NOT NULL,
    product_image VARCHAR(500),
    quantity INT DEFAULT 1,
    unit_price DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,
    extra_info JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    INDEX idx_order_id (order_id),
    INDEX idx_product_id (product_id),
    INDEX idx_product_type (product_type)
);
```

---

## 🔧 数据库迁移SQL

如果需要重命名现有表：

```sql
-- 重命名订单主表
RENAME TABLE customer_order TO orders;

-- 重命名订单明细表（如果存在）
RENAME TABLE order_item TO order_items;
```

或者，如果需要保留旧表并创建新表：

```sql
-- 1. 备份旧表
CREATE TABLE customer_order_backup AS SELECT * FROM customer_order;

-- 2. 创建新表结构
-- （使用上面的 CREATE TABLE 语句）

-- 3. 迁移数据
-- （参考 docs/order_migration.md）
```

---

## ⚠️ 重要提示

1. **外键约束**：新表结构中 `order_items.order_id` 有外键约束指向 `orders.id`
2. **级联删除**：删除订单时会自动删除对应的订单明细
3. **索引优化**：新表结构包含必要的索引，提升查询性能
4. **向后兼容**：模型类名保持不变（CustomerOrder, OrderItem），只是表名改变

---

## 📝 使用示例

### **查询订单及其明细**
```sql
SELECT
    o.order_no,
    o.final_amount,
    o.payment_status,
    oi.product_name,
    oi.quantity,
    oi.unit_price
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
WHERE o.customer_id = 1
ORDER BY o.created_at DESC;
```

### **统计订单总金额和明细数量**
```sql
SELECT
    o.id,
    o.order_no,
    o.final_amount,
    COUNT(oi.id) as item_count
FROM orders o
LEFT JOIN order_items oi ON o.id = oi.order_id
GROUP BY o.id
ORDER BY o.created_at DESC;
```

---

## 🔄 相关文档

- [订单数据迁移方案](order_migration.md)
- [订单API使用说明](order_api_usage.md)

---

**更新日期**: 2026-03-27
**版本**: v2.0
