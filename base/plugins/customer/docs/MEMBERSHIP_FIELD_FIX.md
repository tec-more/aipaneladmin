# 会员等级配置字段说明和修复方案

> 解决"小时数"和"总小时数"显示为0的问题 | 2026-03-29

---

## 🔴 问题分析

### 用户反馈的问题

在会员等级配置（MembershipLevel）中：
- **"小时数"**（duration_hours）显示为 0
- **"总小时数"** 也显示为 0
- **预期**: 总小时数 = 小时数 + 赠送小时

---

## 📊 字段定义说明

### 数据库模型 (MembershipLevel)

```python
class MembershipLevel(BaseModel):
    duration_hours = fields.IntField(default=0, description="有效期小时数")
    bonus_hours = fields.IntField(default=0, description="赠送小时数")
```

### 字段含义

| 数据库字段 | 显示名称 | 含义 | 示例 |
|-----------|---------|------|------|
| **duration_hours** | 小时数 | 套餐包含的基础时长 | 100 |
| **bonus_hours** | 赠送小时 | 购买时额外赠送的时长 | 20 |
| **（计算字段）** | 总小时数 | duration_hours + bonus_hours | 120 |

---

## ✅ 正确的理解

### 核心公式

```
给用户的总时长 = duration_hours（基础时长） + bonus_hours（赠送时长）
```

### 实际应用

**示例1：年度会员套餐**

```json
{
  "name": "年度SVIP会员",
  "duration_hours": 0,      // 小时数：0（无时间限制）
  "bonus_hours": 100,      // 赠送小时：100
  "总小时数（计算）": 100    // 0 + 100 = 100小时
}
```

**示例2：小时充值套餐**

```json
{
  "name": "100小时充值",
  "duration_hours": 100,   // 小时数：100
  "bonus_hours": 20,       // 赠送小时：20
  "总小时数（计算）": 120    // 100 + 20 = 120小时
}
```

---

## 🔍 问题原因分析

### 为什么"小时数"显示为0？

可能的原因：

#### 1. **配置错误** ⚠️
年度会员类型套餐通常 `duration_hours = 0`，因为：
- 年度会员按天计算有效期
- 没有小 时数的限制
- 所以显示为0是**正常的**

**示例**:
```
年度会员：
  duration_days: 365（按天计算）
  duration_hours: 0（无小时限制）
  bonus_hours: 100（赠送100小时）
```

#### 2. **前端显示问题** ⚠️
前端可能在显示"总小时数"时没有正确计算：
- 只显示了 `duration_hours`
- 没有加上 `bonus_hours`

#### 3. **数据未保存** ⚠️
创建或编辑套餐时，`duration_hours` 字段没有被正确赋值。

---

## 🛠️ 修复方案

### 方案1: 理解字段含义（推荐）⭐

#### 如果是年度会员类型

```json
{
  "name": "年度SVIP会员",
  "level_type": "yearly",
  "duration_hours": 0,        // ✅ 正确：年度会员无小时限制
  "bonus_hours": 100,        // ✅ 购买时赠送100小时
  "duration_days": 365,      // ✅ 有效期365天
  "price": 365.00
}
```

**说明**:
- `duration_hours = 0` 是正确的（年度会员按天数计算）
- 用户购买后 `total_hours += 100`
- 会员在365天后过期，但等级保留

---

#### 如果是小时充值类型

```json
{
  "name": "100小时充值",
  "level_type": "fibonacci",
  "duration_hours": 100,    // ✅ 套餐包含100小时
  "bonus_hours": 20,        // ✅ 购买时赠送20小时
  "duration_days": 30,       // ✅ 有效期30天（或0表示不限）
  "price": 99.00
}
```

**说明**:
- 用户购买后 `total_hours += 100 + 20 = 120`
- 等级基于120小时计算
- 会员在使用完120小时后过期

---

### 方案2: 修复前端显示逻辑

#### 前端计算"总小时数"

```javascript
// ❌ 错误：只显示 duration_hours
display_total_hours = membership.duration_hours;

// ✅ 正确：计算总小时数
display_total_hours = membership.duration_hours + membership.bonus_hours;

// 显示
<div class="total-hours">
  总小时数: {display_total_hours} 小时
  （基础: {membership.duration_hours} + 赠送: {membership.bonus_hours}）
</div>
```

#### Vue.js 示例

```vue
<template>
  <div class="membership-level">
    <h3>{{ level.name }}</h3>
    <p class="total-hours">
      总小时数: {{ totalHours }} 小时
    </p>
    <p class="breakdown">
      <span>基础: {{ level.duration_hours }}小时</span>
      <span> + 赠送: {{ level.bonus_hours }}小时</span>
    </p>
  </div>
</template>

<script>
export default {
  computed: {
    totalHours() {
      return this.level.duration_hours + this.level.bonus_hours;
    }
  }
}
</script>
```

---

### 方案3: 添加数据验证

### 后端添加字段验证

```python
from pydantic import BaseModel, Field, validator

class MembershipLevelCreate(BaseModel):
    """创建会员等级"""
    name: str = Field(..., min_length=1, description="套餐名称")
    duration_hours: int = Field(0, ge=0, description="基础时长")
    bonus_hours: int = Field(0, ge=0, description="赠送时长")
    duration_days: int = Field(..., gt=0, description="有效期天数")
    price: float = Field(..., gt=0, description="价格")

    @validator('duration_hours', 'bonus_hours')
    def validate_hours(cls, v, values):
        """验证时长逻辑"""
        # 如果是年度会员类型，允许duration_hours=0
        if values.get('level_type') == 'yearly' and v == 0:
            return v

        # 其他类型套餐必须有基础时长
        if v == 0:
            raise ValueError('小时数不能为0（年度会员除外）')

        # 验证总时长合理
        total = v + values.get('bonus_hours', 0)
        if total == 0:
            raise ValueError('总时长（基础+赠送）不能为0')

        return v
```

---

## 📊 正确的套餐配置示例

### 示例1：年度会员（无小时限制）

```json
{
  "id": 1,
  "name": "年度SVIP会员",
  "level_type": "yearly",
  "description": "一年期会员，赠送100小时",
  "duration_days": 365,
  "duration_hours": 0,        // 年度会员无小时限制
  "bonus_hours": 100,        // 购买时赠送100小时
  "price": 365.00,
  "features": ["无限翻译", "API访问"]
}
```

**业务逻辑**:
```
用户支付 ¥365
→ total_hours += 0 + 100 = 100小时
→ 等级: Level 10（白银会员）
→ 有效期: 365天
```

---

### 示例2：小时充值（有小时限制）

```json
{
  "id": 2,
  "name": "100小时充值",
  "level_type": "fibonacci",
  "description": "100小时充值套餐",
  "duration_days": 30,
  "duration_hours": 100,    // 套餐包含100小时
  "bonus_hours": 20,        // 购买赠送20小时
  "price": 99.00,
  "features": []
}
```

**业务逻辑**:
```
用户支付 ¥99
→ total_hours += 100 + 20 = 120小时
→ 等级: Level 10（白银会员）
→ 有效期: 30天（或使用完120小时）
```

---

### 示例3：体验会员

```json
{
  "id": 3,
  "name": "体验会员",
  "level_type": "trial",
  "description": "3天体验期",
  "duration_days": 3,
  "duration_hours": 5,     // 包含5小时
  "bonus_hours": 0,        // 无赠送
  "price": 0.01,
  "features": ["基础功能"]
}
```

**业务逻辑**:
```
用户支付 ¥0.01
→ total_hours += 5 + 0 = 5小时
→ 等级: Level 3（正式会员）
→ 有效期: 3天
```

---

## 🔍 检查现有配置

### 查看数据库中的实际配置

```sql
SELECT
  id,
  name,
  level_type,
  duration_hours AS "小时数",
  bonus_hours AS "赠送小时",
  (duration_hours + bonus_hours) AS "总小时数",
  duration_days AS "有效期天数",
  price
FROM customer_membership_level
ORDER BY id;
```

### 检查是否有"小时数"为0的套餐

```sql
SELECT
  id,
  name,
  level_type,
  duration_hours AS "小时数",
  bonus_hours AS "赠送小时"
FROM customer_membership_level
WHERE duration_hours = 0 AND level_type != 'yearly'
ORDER BY id;
```

**注意**: 只有年度会员（yearly）允许 `duration_hours = 0`

---

## 🛠️ 数据修复方案

### 修复脚本：更新小时数配置

```python
import asyncio
from tortoise import Tortoise
from base.plugins.customer.models import MembershipLevel

async def fix_membership_hours():
    """修复小时数配置"""
    await Tortoise.init(
        db_url='mysql://admin:123456@127.0.0.1:5432/aipaneladmin',
        modules=['base.plugins.customer.models']
    )

    # 查询所有level_type不是yearly但duration_hours为0的套餐
    levels = await MembershipLevel.filter(
        level_type__not_in=['yearly', 'lifetime'],
        duration_hours=0
    )

    print(f"找到 {len(levels)} 个需要修复的套餐:\n")

    for level in levels:
        print(f"ID: {level.id}")
        print(f"名称: {level.name}")
        print(f"类型: {level.level_type}")
        print(f"当前小时数: {level.duration_hours}")
        print(f"赠送小时数: {level.bonus_hours}")

        # 建议值
        if level.level_type == 'trial':
            suggested = 5
        elif level.level_type == 'monthly':
            suggested = 720  # 30天 * 24小时
        elif level.level_type == 'quarterly':
            suggested = 2160  # 90天 * 24小时
        else:
            suggested = 100

        print(f"建议修改为: {suggested}小时")
        print("-" * 70)

    await Tortoise.close_connections()

asyncio.run(fix_membership_hours())
```

---

## 📋 配置检查清单

### 创建或编辑套餐时检查

- [ ] **level_type**: 正确选择套餐类型
  - `yearly`: 年度会员，duration_hours可以是0
  - `fibonacci`: 小时充值，duration_hours必须>0
  - `trial`: 体验会员，需要填写小时数

- [ ] **duration_hours**: 基础时长
  - 年度会员: 设为0
  - 其他类型: 必须大于0

- [ ] **bonus_hours**: 赠送时长
  - 可以是0（无赠送）
  - 通常为 base_hours 的10%-20%

- [ ] **总时长计算**:
  - 前端显示: `duration_hours + bonus_hours`
  - 后端逻辑: `total_hours += duration_hours + bonus_hours`

---

## 🎯 总结

### 字段含义

| 字段 | 显示名称 | 定义 | 示例 |
|------|---------|------|------|
| **duration_hours** | 小时数 | 套餐包含的基础时长 | 100 |
| **bonus_hours** | 赠送小时 | 购买时额外赠送 | 20 |
| **（计算）** | 总小时数 | duration_hours + bonus_hours | 120 |

### 关键理解

1. ✅ **年度会员的"小时数"为0是正常的**
   - 年度会员按天数计算，不按小时计算
   - 所以 `duration_hours = 0` 是正确的

2. ✅ **总小时数 = 小时数 + 赠送小时**
   - 前端需要计算: `duration_hours + bonus_hours`
   - 后端累加时: `total_hours += duration_hours + bonus_hours`

3. ✅ **不同套餐类型有不同的规则**
   - 年度会员: duration_hours = 0, 按天计算
   - 小时充值: duration_hours > 0, 按小时计算
   - 体验会员: 两者都可以

---

**版本**: v1.0
**最后更新**: 2026-03-29
