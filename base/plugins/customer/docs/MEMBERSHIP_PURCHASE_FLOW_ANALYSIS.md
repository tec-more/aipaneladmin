# 会员购买和充值时长关系分析

> 深入理解充值套餐、时长累计、等级计算的关系 | 2026-03-29

---

## 📊 核心概念

### 三个关键"时长"字段

在会员系统中，有三个容易混淆的"时长"概念：

| 字段 | 含义 | 作用 | 持久性 |
|------|------|------|--------|
| **duration_hours** | 套餐包含的基础时长 | 计算有效期 | 一次性消费 |
| **bonus_hours** | 赠送时长 | 增加total_hours | 永久保留 |
| **total_hours** | 累计充值总时长 | 计算等级 | **永久累计** |

---

## 🎯 一、购买流程详解

### 购买公式

```python
# 支付成功后
total_hours = total_hours + duration_hours + bonus_hours
```

**关键点**:
- `duration_hours`: 套餐的基础时长（可能为0）
- `bonus_hours`: 购买时赠送的额外时长
- `total_hours`: 累计值，每次购买都会累加

---

## 📋 二、实际场景分析

### 场景1: 购买年度会员（时间限制型套餐）

#### 套餐配置
```json
{
  "name": "年度SVIP会员",
  "price": 365.00,
  "duration_days": 365,
  "duration_hours": 0,      // 注意：无时间限制
  "bonus_hours": 100       // 购买赠送100小时
}
```

#### 购买流程

**初始状态**:
```
total_hours: 0
level: 0 (免费用户)
```

**支付成功后**:
```
total_hours = 0 + 0 + 100 = 100小时
level = Level 10 (白银会员)
```

**有效期**:
```
start_time: 2026-03-29
expire_time: 2027-03-29 (365天后)
```

**关键理解**:
1. ✅ `duration_hours = 0` 表示套餐本身无时间限制
2. ✅ `bonus_hours = 100` 是实际充值的时长
3. ✅ `total_hours` 累计100小时，等级达到Level 10
4. ✅ 365天后会员过期，但 `total_hours` 保留为100
5. ✅ 续费后 `total_hours` 继续累加

---

### 场景2: 购买小时充值套餐（时间限制型）

#### 套餐配置
```json
{
  "name": "100小时充值",
  "price": 99.00,
  "duration_days": 30,
  "duration_hours": 100,    // 套餐包含100小时
  "bonus_hours": 20        // 购买赠送20小时
}
```

#### 购买流程

**初始状态**:
```
total_hours: 0
```

**支付成功后**:
```
total_hours = 0 + 100 + 20 = 120小时
level = Level 10 (白银会员)
```

**有效期**:
```
start_time: 2026-03-29
expire_time: 2026-04-28 (30天后)
```

**关键理解**:
1. ✅ 实际充值了 `duration_hours + bonus_hours = 120小时`
2. ✅ `total_hours` 累计120小时
3. ✅ 等级基于 `total_hours` 计算，达到Level 10
4. ✅ 30天后会员过期，但 `total_hours` 保留为120
5. ✅ 会员过期后，等级称号保留（但不享受特权）
6. ✅ 续费后从120小时继续累加

---

### 场景3: 多次购买的累计效应

#### 第一次购买：100小时套餐

```json
{
  "duration_hours": 100,
  "bonus_hours": 20
}
```

```
total_hours = 0 + 100 + 20 = 120小时
level = Level 10 (白银会员)
```

#### 第二次购买：50小时套餐

```json
{
  "duration_hours": 50,
  "bonus_hours": 10
}
```

```
total_hours = 120 + 50 + 10 = 180小时
level = Level 11 (黄金会员)  // 升级了！
```

#### 第三次购买：100小时套餐

```
total_hours = 180 + 100 + 20 = 300小时
level = Level 12 (黄金会员)
```

**关键理解**:
1. ✅ `total_hours` 是**永久累计**的
2. ✅ 每次购买都会累加
3. ✅ 累加到一定程度会触发等级提升
4. ✅ 会员过期不影响 `total_hours` 的累计

---

## 🔍 三、时长字段的详细对比

### 1. duration_hours（套餐基础时长）

**定义**: 套餐本身包含的基础时长

**用途**:
- 计算会员的有效期
- 如果 `duration_hours > 0`，会员会在使用完这些时长后过期

**示例**:
```
duration_hours: 100
使用50小时后
remaining_hours = 100 - 50 = 50
继续使用到0小时 → 会员过期
```

**特殊情况**:
```
duration_hours: 0  // 无时间限制
表示套餐本身没有时长限制
会员根据 duration_days 计算过期时间
```

---

### 2. bonus_hours（赠送时长）

**定义**: 购买时额外赠送的时长

**用途**:
- 增加 `total_hours`
- 提升用户等级
- 不计入有效期消耗（纯赠送）

**示例**:
```
套餐：100小时基础时长 + 20小时赠送

支付成功后：
total_hours += 100 + 20 = 120小时（全部计入等级）
有效期：消耗100小时后过期（赠送的20小时不消耗）
```

**或者**（更常见的理解）:
```
套餐：100小时基础时长，赠送20小时

支付成功后：
total_hours += 100 + 20 = 120小时（全部计入等级）
有效期：消耗120小时后过期（基础+赠送一起消耗）
```

---

### 3. total_hours（累计充值总时长）

**定义**: 所有购买充值的总时长累计

**特性**:
- ✅ **永久累计**，只增不减
- ✅ 用于计算Fibonacci等级
- ✅ 决定用户等级称号和特权
- ✅ 不受会员过期影响

**计算公式**:
```
total_hours = Σ(所有购买的 duration_hours + bonus_hours)
```

**示例**:
```
购买历史：
1. 购买100小时套餐（100+20） → total_hours = 120
2. 购买50小时套餐（50+10）  → total_hours = 180
3. 购买200小时套餐（200+50） → total_hours = 430

最终：total_hours = 430小时 → Level 12（黄金会员）
```

---

## 📐 四、等级计算对照表

### Fibonacci数列累计值

| 等级 | 累计时长 | 等级称号 | 需要购买 |
|------|---------|---------|---------|
| 0 | 0 | 免费用户 | - |
| 1 | 1 | 体验会员 | 1小时 |
| 2 | 2 | 体验会员 | +1小时 |
| 3 | 4 | 正式会员 | +2小时 |
| 4 | 7 | 正式会员 | +3小时 |
| 5 | 12 | 高级会员 | +5小时 |
| 6 | 20 | 高级会员 | +8小时 |
| 7 | 33 | 高级会员 | +13小时 |
| 8 | 54 | 青铜会员 | +21小时 |
| 9 | 88 | 青铜会员 | +34小时 |
| 10 | 143 | 白银会员 | +55小时 |
| 11 | 232 | 白银会员 | +89小时 |
| 12 | 376 | 黄金会员 | +144小时 |
| 13 | 609 | 黄金会员 | +233小时 |
| 14 | 986 | 黄金会员 | +377小时 |

### 实际充值示例

#### 用户充值历程

| 次数 | 购买套餐 | 累计时长 | 等级 | 称号 |
|------|---------|---------|------|------|
| 初始 | - | 0 | 0 | 免费用户 |
| 1 | 100小时套餐 | 120 | 10 | 白银会员 |
| 2 | 50小时套餐 | 180 | 11 | 白银会员 |
| 3 | 100小时套餐 | 300 | 12 | 黄金会员 ✨ |

**说明**:
- 第一次购买120小时 → Level 10（白银）
- 第二次购买+70小时 → Level 11（白银）
- 第三次购买+120小时 → Level 12（黄金）

---

## 💳 五、会员有效期 vs 等级

### 关键区别

```
┌─────────────────────────────────────────────────┐
│ 会员有效期（expire_time）                          │
│ - 决定用户能否使用功能                            │
│ - 基于 duration_days 计算                           │
│ - 过期后 is_active = false                         │
│ - 过期后不能使用功能，但可以续费                    │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│ Fibonacci等级（level）                            │
│ - 决定用户的称号和特权                            │
│ - 基于 total_hours 计算                            │
│ - 永久保留，不受会员过期影响                        │
│ - 续费后继续累加                                  │
└─────────────────────────────────────────────────┘
```

### 示例场景

```
用户购买"年度SVIP"（365天，100小时赠送）

【购买后】
total_hours: 100
level: 10（白银会员）
expire_time: 2027-03-29
is_active: true

【使用50小时后】
total_hours: 100 (不变)
level: 10 (不变)
used_hours: 50
remaining_hours: 50
is_active: true

【365天后过期】
total_hours: 100 (不变)
level: 10 (不变)
is_active: false
is_expired: true

【续费购买50小时】
total_hours: 150 (累加)
level: 11 (升级到黄金会员)
is_active: true (重新激活)
```

---

## 🎯 六、购买建议和策略

### 策略1: 快速升级（新用户）

**目标**: 快速达到高级会员（Level 5+，需要7小时）

**推荐购买**:
```
1. 购买"10小时充值套餐"（¥9.9）
   - total_hours: 10
   - level: Level 5（高级会员）✨
```

---

### 策略2: 长期使用（重度用户）

**目标**: 大量使用，需要高等级

**推荐购买**:
```
1. 购买"年度SVIP"（¥365）
   - 获赠100小时
   - total_hours: 100
   - level: Level 10（白银会员）

2. 再购买"100小时充值"（¥99）
   - total_hours: 220
   - level: Level 12（黄金会员）✨
```

---

### 策略3: 性价比最高

**计算**: 每¥1能获得的等级提升

**最优策略**: 购买含赠送时长的套餐

```
套餐A: 100小时，¥99（0赠送）
  性价比: 1.01元/小时

套餐B: 100小时+20赠送，¥99
  性价比: 0.825元/小时 ✅ 更优

套餐C: 年度会员（365天+100赠送），¥365
  性价比: 3.65元/天 + 100小时永久
```

---

## 🔧 七、代码实现

### 购买会员时的时长累加

```python
async def create_customer_membership(
    customer_id: int,
    membership_level_id: int,
    hours: int  # 注意：这个参数是套餐时长，不是total_hours
):
    # 获取套餐配置
    level_config = await MembershipLevel.get_or_none(id=membership_level_id)

    # 计算实际增加的时长
    added_hours = level_config.duration_hours + level_config.bonus_hours

    # 累加到 total_hours
    total_hours = existing.total_hours + added_hours

    # 计算新的等级
    new_level = fibonacci_service.get_level_from_hours(total_hours)

    # 保存
    membership.total_hours = total_hours
    membership.level = new_level
```

---

## 📊 八、完整示例

### 用户从0到黄金会员的完整历程

#### 初始状态
```
用户: 新用户
total_hours: 0
level: 0 (免费用户)
remaining_hours: 0
```

#### 第一次购买：100小时套餐（¥99）
```
套餐配置:
  duration_hours: 100
  bonus_hours: 20

支付后:
  total_hours: 120
  level: Level 10（白银会员）
  expire_time: 30天后
```

#### 使用80小时
```
used_hours: 80
remaining_hours: 40
level: 10（不变）
```

#### 第二次购买：100小时套餐（¥99）
```
支付后:
  total_hours: 220（120 + 100）
  level: Level 11（黄金会员）✨
  expire_time: 重新计算
```

#### 最终状态
```
total_hours: 220
used_hours: 80
remaining_hours: 140
level: 11（黄金会员）
```

---

## 🎓 九、常见问题

### Q1: duration_hours 为 0 表示什么？

**A**:
- 套餐本身没有时间限制
- 会员的有效期由 `duration_days` 决定
- 例如：年度会员 duration_hours=0，但有效期365天

### Q2: 会员过期后等级会降吗？

**A**:
- 不会！`total_hours` 是永久保留的
- 会员过期只是 `is_active = false`
- 续费后 `is_active = true`，等级保持不变

### Q3: bonus_hours 算入有效期吗？

**A**: 有两种设计：

**设计1**: 不计入有效期（推荐）
```
total_hours += duration_hours + bonus_hours（都计入等级）
有效期只消耗 duration_hours
```

**设计2**: 计入有效期
```
total_hours += duration_hours + bonus_hours（都计入等级）
有效期消耗 duration_hours + bonus_hours
```

**当前系统**: 需要根据代码确认

### Q4: 如何快速升级到高等级？

**A**:
查看等级对照表，累计对应的时长：
- Level 5（高级会员）: 需要7小时
- Level 8（青铜会员）: 需要33小时
- Level 13（白银会员）: 需要88小时
- Level 21（黄金会员）: 需要143小时

### Q5: 购买时长和等级的关系？

**A**:
```
购买时长 → 增加total_hours → 计算等级
```

不是直接的关系，而是通过 `total_hours` 间接计算。

---

## 📚 总结

### 核心公式

```
购买订单:
total_hours += duration_hours + bonus_hours

计算等级:
level = fibonacci_service.get_level_from_hours(total_hours)

计算剩余:
remaining_hours = total_hours - used_hours
```

### 关键点

1. ✅ **total_hours 是永久累计的**
2. ✅ **等级只看 total_hours**
3. ✅ **会员过期不影响 total_hours**
4. ✅ **续费后 total_hours 继续累加**

---

**版本**: v1.0
**最后更新**: 2026-03-29
