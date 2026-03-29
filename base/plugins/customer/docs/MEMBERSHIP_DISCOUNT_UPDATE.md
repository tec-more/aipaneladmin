# 会员等级折扣功能更新说明

> 添加手动设置折扣百分比功能 | 2026-03-29

---

## 📋 更新概述

为会员等级配置添加了 `discount_percentage`（折扣百分比）字段，允许管理员手动设置折扣，而不仅仅依赖原价自动计算。

---

## ✅ 更新内容

### 1. 数据库模型更新

**文件**: `base/plugins/customer/models/membership.py`

**新增字段**:
```python
discount_percentage = fields.IntField(default=0, description="折扣百分比(0-100)")
```

**字段说明**:
- 类型: `IntegerField`
- 默认值: `0`（表示无折扣）
- 范围: 0-100
- 优先级: 高于自动计算的折扣

---

### 2. Schema 更新

**文件**: `base/plugins/customer/schemas/membership.py`

**MembershipLevelIn** 和 **MembershipLevelOut** 都添加了:
```python
discount_percentage: int = 0
```

---

### 3. API 更新

**文件**: `base/plugins/customer/api/v1/customer.py`

更新了以下接口的返回数据，包含 `discount_percentage` 字段：

1. **GET /v1/customer/membership-levels** - 获取会员等级列表
2. **POST /v1/customer/membership-levels** - 创建会员等级
3. **PUT /v1/customer/membership-levels/{level_id}** - 更新会员等级
4. **PATCH /v1/customer/membership-levels/{level_id}** - 切换状态

---

### 4. 前端页面更新

**文件**: `web/src/views/customer/membership-levels/index.vue`

#### 表格显示逻辑

```vue
<el-table-column label="折扣">
  <template #default="{ row }">
    <!-- 优先显示手动设置的折扣 -->
    <el-tag v-if="row.discount_percentage > 0" type="danger">
      {{ row.discount_percentage }}% OFF
    </el-tag>

    <!-- 如果没有手动设置，则显示根据原价计算的折扣 -->
    <el-tag v-else-if="row.original_price && row.original_price > row.price" type="warning">
      {{ Math.round((1 - row.price / row.original_price) * 100) }}% OFF
    </el-tag>

    <!-- 都没有则不显示折扣 -->
    <span v-else>-</span>
  </template>
</el-table-column>
```

#### 表单编辑

新增了折扣百分比输入字段：

```vue
<el-form-item label="折扣(%)" prop="discount_percentage">
  <el-input-number
    v-model="form.discount_percentage"
    :min="0"
    :max="100"
    placeholder="手动设置折扣百分比"
  />
  <div style="font-size: 12px; color: #909399; margin-top: 4px;">
    手动设置折扣，优先显示此折扣值（0表示不显示折扣）
  </div>
</el-form-item>
```

#### 折扣预览

智能折扣预览，优先显示手动设置的折扣：

```vue
<!-- 1. 手动设置的折扣（优先） -->
<div v-if="form.discount_percentage > 0">
  ¥99  ¥199  [30% OFF]
  ⭐ 手动设置折扣
</div>

<!-- 2. 自动计算的折扣（次优先） -->
<div v-else-if="form.original_price && form.original_price > form.price">
  ¥99  ¥199  [50% OFF]
  ⚠️ 根据原价自动计算折扣
</div>

<!-- 3. 无折扣 -->
<div v-else>
  无折扣（价格: ¥99）
</div>
```

---

## 🎯 使用场景

### 场景1: 手动设置折扣

```json
{
  "name": "春季特惠套餐",
  "price": 99,
  "original_price": 199,
  "discount_percentage": 30
}
```

**显示效果**:
- 价格: ¥99
- 原价: ¥199（划线）
- 折扣: 30% OFF ⭐

**说明**: 虽然根据原价计算应该是50%折扣，但因为手动设置了30%，所以显示30%

---

### 场景2: 自动计算折扣

```json
{
  "name": "夏季促销套餐",
  "price": 99,
  "original_price": 199,
  "discount_percentage": 0
}
```

**显示效果**:
- 价格: ¥99
- 原价: ¥199（划线）
- 折扣: 50% OFF ⚠️

**说明**: 因为 `discount_percentage` 为 0，所以根据原价自动计算折扣

---

### 场景3: 无折扣

```json
{
  "name": "标准套餐",
  "price": 99,
  "original_price": null,
  "discount_percentage": 0
}
```

**显示效果**:
- 价格: ¥99
- 原价: -
- 折扣: -

---

## 📊 折扣显示优先级

```
1. discount_percentage > 0
   └─ 显示: 手动设置的折扣百分比
   └─ 标签: ⭐ 手动设置折扣

2. original_price > price
   └─ 显示: 根据原价自动计算的折扣
   └─ 标签: ⚠️ 根据原价自动计算折扣

3. 其他情况
   └─ 显示: 无折扣
```

---

## 🔧 字段关系

| 字段 | 类型 | 说明 | 是否必填 |
|------|------|------|----------|
| **price** | Decimal | 实际售价 | ✅ 必填 |
| **original_price** | Decimal | 原价（用于划线显示） | ❌ 可选 |
| **discount_percentage** | Int | 折扣百分比（0-100） | ❌ 可选（默认0） |

### 计算公式

```python
# 自动计算折扣（当 discount_percentage = 0 时）
if original_price and original_price > price:
    auto_discount = round((1 - price / original_price) * 100)
```

---

## 🚀 数据库迁移

**迁移文件**: `migrations/models/16_20260329100000_add_discount_percentage.py`

### 升级（添加字段）

```sql
ALTER TABLE "customer_membership_level"
ADD COLUMN IF NOT EXISTS "discount_percentage" INT NOT NULL DEFAULT 0;
```

### 降级（移除字段）

```sql
ALTER TABLE "customer_membership_level"
DROP COLUMN IF EXISTS "discount_percentage";
```

### 执行迁移

```bash
# 方式1: 使用 Aerich（推荐）
aerich upgrade

# 方式2: 手动执行 SQL
psql -U admin -d aipaneladmin -f migrations/models/16_20260329100000_add_discount_percentage.py
```

---

## 💡 最佳实践

### 1. 何时使用手动设置折扣？

- ✅ **促销活动**: "双11特惠 30% OFF"，但实际价格可能不是精确的30%折扣
- ✅ **营销展示**: 想要显示特定的折扣数字，如 "50% OFF" 更有吸引力
- ✅ **套装优惠**: 多个商品组合，折扣无法简单计算

### 2. 何时使用自动计算折扣？

- ✅ **常规定价**: 设置原价和现价，让系统自动计算折扣
- ✅ **精确折扣**: 需要显示真实的折扣百分比
- ✅ **简化管理**: 不想手动维护折扣值

### 3. 字段设置建议

```json
// 推荐配置1: 有手动折扣
{
  "price": 99,
  "original_price": 199,
  "discount_percentage": 50  // 手动设置，显示50% OFF
}

// 推荐配置2: 自动计算
{
  "price": 99,
  "original_price": 199,
  "discount_percentage": 0  // 自动计算，显示50% OFF
}

// 推荐配置3: 无折扣
{
  "price": 99,
  "original_price": null,
  "discount_percentage": 0
}
```

---

## ⚠️ 注意事项

1. **默认值为 0**
   - 新建套餐时，`discount_percentage` 默认为 0
   - 0 表示不显示手动折扣，会尝试自动计算

2. **优先级规则**
   - `discount_percentage` 的优先级高于自动计算
   - 设置 `discount_percentage` 后，会忽略基于 `original_price` 的计算

3. **数据验证**
   - `discount_percentage` 范围: 0-100
   - 前端已设置 `:max="100"` 限制
   - 后端也有范围验证

4. **历史数据兼容**
   - 迁移脚本设置了默认值 0
   - 已有的套餐会自动使用自动计算折扣
   - 不影响现有功能

---

## 📝 更新日志

**版本**: v1.1
**日期**: 2026-03-29
**作者**: Claude Code

### 变更内容

- ✅ 数据库模型添加 `discount_percentage` 字段
- ✅ Schema 更新，支持新字段
- ✅ API 接口返回数据包含新字段
- ✅ 前端表格显示逻辑优化
- ✅ 前端表单添加折扣百分比输入
- ✅ 添加折扣预览功能
- ✅ 创建数据库迁移文件

---

## 🔗 相关文档

- [会员等级配置说明](base/plugins/customer/docs/MEMBERSHIP_LEVEL_EXPLAINED.md)
- [会员字段修复说明](base/plugins/customer/docs/MEMBERSHIP_FIELD_FIX.md)
- [会员购买流程分析](base/plugins/customer/docs/MEMBERSHIP_PURCHASE_FLOW_ANALYSIS.md)

---

**状态**: ✅ 已完成
**需要重启服务**: 是（需要执行数据库迁移）
