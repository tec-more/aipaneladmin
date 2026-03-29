# 会员等级配置定义和意义说明

> 理解系统的双层级会员体系 | 2026-03-29

---

## 📊 系统架构概述

当前系统有**两个会员等级体系**，它们协同工作：

### 1. **Fibonacci动态等级系统**（用户可见）
- **作用**: 显示用户的等级称号和特权
- **计算**: 基于用户累计充值时长自动计算
- **特点**: 无限等级，动态增长

### 2. **MembershipLevel套餐配置表**（后台管理）
- **作用**: 配置不同的充值套餐（产品）
- **存储**: 数据库表 `customer_membership_level`
- **特点**: 固定套餐，灵活配置

---

## 🎯 一、Fibonacci动态等级系统

### 定义

基于**Fibonacci数列**的无限等级系统，每充值1小时等级自动增长。

### 核心概念

#### 等级的含义
**等级n** = 累计充值了前n个Fibonacci数的时间单位

**示例**:
```
Level 0: 0小时
Level 1: F(1) = 1小时
Level 2: F(1)+F(2) = 1+1 = 2小时
Level 3: F(1)+F(2)+F(3) = 1+1+2 = 4小时
Level 4: F(1)+F(2)+F(3)+F(4) = 1+1+2+3 = 7小时
Level 5: F(1)+F(2)+F(3)+F(4)+F(5) = 1+1+2+3+5 = 12小时
Level 6: F(1)+...+F(6) = 20小时
...
```

#### 等级区间对照表

| 等级 | 累计时长 | 时长范围 | 称号 | 特权（主要） |
|------|---------|---------|------|-----------|
| 0 | 0 | 0 | 免费用户 | 基础功能 |
| 1-2 | 1-2 | 1-2 | 体验会员 | 100字/日 |
| 3-4 | 4 | 3-4 | 正式会员 | 500字/日、去广告 |
| 5-7 | 7 | 5-7 | 高级会员 | 2000字/日、优先客服 |
| 8-12 | 20 | 8-19 | 青铜会员 | 5000字/日、专属客服 |
| 13-20 | 33 | 20-32 | 白银会员 | 10000字/日、API访问 |
| 21-33 | 54 | 33-53 | 黄金会员 | 20000字/日、批量翻译 |
| 34-54 | 88 | 54-87 | 铂金会员 | 50000字/日、团队协作 |
| 55-88 | 143 | 88-142 | 钻石会员 | 100000字/日、专属经理 |
| 89-143 | 232 | 143-231 | 至尊会员 | 无限额度、7x24客服 |
| 144+ | 376+ | 376+ | 传奇会员 | 永久使用、平台合作 |

### 计算逻辑

```python
# 计算用户等级
def get_level_from_hours(total_hours):
    level = 0
    accumulated = 0

    while True:
        next_hours = get_fibonacci(level + 1)
        if accumulated + next_hours > total_hours:
            break
        accumulated += next_hours
        level += 1

    return level
```

**示例**:
- 充值1小时 → Level 1（体验会员）
- 充值3小时 → Level 3（正式会员）
- 充值10小时 → Level 5（高级会员）
- 充值100小时 → Level 11（黄金会员）

### 特权系统

每个等级段对应不同的特权：

**Level 1+ (体验会员)**:
- 每日100字翻译额度
- 标准客服支持

**Level 3+ (正式会员)**:
- 每日500字翻译额度
- 去除主界面广告

**Level 5+ (高级会员)**:
- 每日2000字翻译额度
- 优先客服支持
- 多语言互译

**Level 8+ (青铜会员)**:
- 每日5000字翻译额度
- 专属客服支持
- 离线翻译功能

**Level 13+ (白银会员)**:
- 每日10000字翻译额度
- API访问权限
- 定制化主题

**Level 21+ (黄金会员)**:
- 每日20000字翻译额度
- 优先功能体验
- 批量翻译

**Level 34+ (铂金会员)**:
- 每日50000字翻译额度
- 多账号管理
- 团队协作功能

**Level 55+ (钻石会员)**:
- 每日100000字翻译额度
- 专属客户经理
- 企业级支持

**Level 89+ (至尊会员)**:
- 无限翻译额度
- 7x24小时专属客服
- 定制开发服务

**Level 144+ (传奇会员)**:
- 所有功能永久使用
- 平台合作权益
- 品牌联名机会

---

## 💼 二、MembershipLevel套餐配置表

### 定义

数据库中的充值套餐配置表，用于后台管理不同的充值套餐。

### 数据模型

```python
class MembershipLevel(BaseModel):
    level_type: LevelType      # 套餐类型
    level: int                  # 数字等级（用于Fibonacci）
    name: str                   # 套餐名称（如：SVIP会员）
    description: str            # 描述
    duration_days: int          # 有效期天数
    duration_hours: int        # 有效期小时数
    price: Decimal             # 价格
    original_price: Decimal   # 原价
    bonus_hours: int          # 赠送小时数
    features: List            # 特性列表
    sort_order: int           # 排序
    is_active: bool          # 是否启用
```

### 字段说明

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| **level_type** | Enum | 套餐类型 | `monthly`, `yearly`, `fibonacci` 等 |
| **level** | Int | 数字等级（备用） | 用于区分不同套餐 |
| **name** | String | 套餐名称 | "SVIP会员"、"黄金套餐" |
| **duration_days** | Int | 有效期天数 | 365（年） |
| **duration_hours** | Int | 有效期小时数 | 0（年套餐无小时限制） |
| **price** | Decimal | 价格 | 99.00 |
| **bonus_hours** | Int | 赠送小时数 | 20（购买赠送20小时） |
| **features** | JSON | 特权列表 | ["API访问", "离线翻译"] |

### 套餐类型 (level_type)

```python
class LevelType(str, Enum):
    TRIAL = "trial"              # 体验会员
    MONTHLY = "monthly"          # 月度会员
    QUARTERLY = "quarterly"      # 季度会员
    HALF_YEARLY = "half_yearly"  # 半年会员
    YEARLY = "yearly"            # 年度会员
    LIFETIME = "lifetime"        # 终身会员
    FIBONACCI = "fibonacci"      # Fibonacci动态等级
```

### 实际应用示例

#### 示例1：年度会员套餐

```json
{
  "id": 1,
  "level_type": "yearly",
  "name": "年度SVIP会员",
  "description": "一年期SVIP会员，赠送100小时",
  "duration_days": 365,
  "duration_hours": 0,
  "price": 365.00,
  "bonus_hours": 100,
  "features": ["无限翻译", "API访问", "优先支持"],
  "is_active": true
}
```

**业务逻辑**:
1. 用户支付 ¥365 购买此套餐
2. 系统创建订单，关联 membership_level_id = 1
3. 支付成功后，用户 total_hours += 365 + 100 = 465小时
4. Fibonacci系统自动计算：465小时 → Level 11（黄金会员）
5. 用户获得Level 11的所有特权

---

#### 示例2：小时充值套餐

```json
{
  "id": 2,
  "level_type": "fibonacci",
  "name": "100小时充值",
  "description": "100小时充值套餐",
  "duration_days": 30,
  "duration_hours": 100,
  "price": 99.00,
  "bonus_hours": 20,
  "features": [],
  "is_active": true
}
```

**业务逻辑**:
1. 用户支付 ¥99 购买100小时
2. 支付成功后，用户 total_hours += 100 + 20 = 120小时
3. Fibonacci系统自动计算：120小时 → Level 10（白银会员）
4. 用户获得Level 10的所有特权

---

## 🔗 三、两个系统的关系

### 协作流程

```
1. 用户购买 MembershipLevel 套餐
   ↓
2. 系统创建订单
   ↓
3. 支付成功，增加用户 total_hours
   ↓
4. Fibonacci系统根据 total_hours 自动计算 level
   ↓
5. 显示对应的等级称号和特权
```

### 关键点

**MembershipLevel 的 level 字段**:
- 在某些实现中可能用于排序
- 不直接影响 Fibonacci 等级计算
- Fibonacci 等级完全基于 total_hours 计算

**total_hours 的计算**:
```python
total_hours = 套餐基础时长 + 赠送时长
           = duration_hours + bonus_hours
```

**示例**:
- 购买"年度会员"(365天，100小时赠) → total_hours += 100
- 购买"100小时充值"(100小时，20小时赠) → total_hours += 120

---

## 📊 四、用户会员信息表 (CustomerMembership)

### 定义

记录用户的会员状态和使用情况。

### 关键字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| **customer_id** | Int | 用户ID | 123 |
| **membership_level_id** | Int | 关联的套餐ID | 1 |
| **start_time** | DateTime | 开始时间 | 2026-03-29 10:00:00 |
| **expire_time** | DateTime | 过期时间 | 2027-03-29 10:00:00 |
| **total_hours** | Decimal | 累计充值总时长 | 465.00 |
| **used_hours** | Decimal | 已使用时长 | 50.25 |
| **remaining_hours** | Decimal | 剩余时长 | 414.75 |
| **level** | Int | Fibonacci等级 | 11 |
| **is_active** | Boolean | 是否激活 | true |

### 字段关系

```
total_hours（累计充值）- used_hours（已用） = remaining_hours（剩余）
```

**used_hours 的计算**:
- 从 `usage_logs` 表实时计算
- 累加所有使用记录的 `duration_seconds`
- 转换为小时：`total_seconds / 3600`

**level 的计算**:
```python
level = FibonacciMembershipSystem.get_level_from_hours(total_hours)
```

---

## 🎯 五、实际应用场景

### 场景1：新用户购买会员

**操作**: 用户购买"SVIP会员"套餐（¥365，100小时）

**流程**:
```
1. 创建订单
   - customer_id: 123
   - membership_level_id: 1
   - payment_method: wechat

2. 支付成功后
   - total_hours = 0 + 100 = 100

3. Fibonacci计算
   - 100小时 → Level 10（白银会员）

4. 保存到 customer_membership 表
   - total_hours: 100
   - used_hours: 0（从usage_logs计算）
   - remaining_hours: 100
   - level: 10

5. 用户显示
   - 称号：白银会员
   - 颜色：#9E9E9E（灰色）
   - 图标：card_membership
   - 特权：每日10000字、API访问等
```

---

### 场景2：用户使用功能

**操作**: 用户使用了翻译功能，消耗了5小时

**流程**:
```
1. 创建 usage_log 记录
   - customer_id: 123
   - duration_seconds: 18000 (5小时)

2. 定时任务更新会员数据
   - 从 usage_logs 计算实际 used_hours
   - 更新 customer_membership.used_hours
   - 重新计算 remaining_hours = total_hours - used_hours

3. 等级保持不变
   - total_hours 还是100，等级还是 Level 10
   - 只是 remaining_hours 减少了
```

---

### 场景3：用户续费

**操作**: 用户再次购买100小时

**流程**:
```
1. 创建新订单
   - total_hours = 100 + 100 = 200

2. Fibonacci计算
   - 200小时 → Level 11（黄金会员）

3. 用户升级
   - 从 Level 10（白银）升级到 Level 11（黄金）
   - 称号变更：白银会员 → 黄金会员
   - 特权增加：从10000字/日升级到20000字/日
```

---

## 📝 六、配置示例

### 数据库中的套餐配置

#### 套餐1：体验会员
```json
{
  "id": 1,
  "level_type": "trial",
  "name": "体验会员",
  "description": "3天体验期",
  "duration_days": 3,
  "duration_hours": 5,
  "price": 0.01,
  "bonus_hours": 0,
  "features": ["基础功能"],
  "sort_order": 1
}
```

#### 套餐2：年度SVIP
```json
{
  "id": 2,
  "level_type": "yearly",
  "name": "年度SVIP会员",
  "description": "一年期SVIP会员，赠送100小时",
  "duration_days": 365,
  "duration_hours": 0,
  "price": 365.00,
  "bonus_hours": 100,
  "features": ["无限翻译", "API访问", "优先支持"],
  "sort_order": 2
}
```

#### 套餐3：小时充值
```json
{
  "id": 3,
  "level_type": "fibonacci",
  "name": "10小时充值",
  "description": "10小时充值套餐",
  "duration_days": 30,
  "duration_hours": 10,
  "price": 9.90,
  "bonus_hours": 0,
  "features": [],
  "sort_order": 3
}
```

---

## 🎓 七、关键要点总结

### 1. 两个体系的作用

| 体系 | 作用 | 面向对象 |
|------|------|----------|
| **Fibonacci等级系统** | 显示等级称号和特权 | 用户 |
| **MembershipLevel表** | 配置充值套餐 | 管理员 |

### 2. 等级计算的依据

**只看 total_hours**:
- Level = f(total_hours)
- 不看购买了哪个套餐
- 不看套餐的有效期

### 3. total_hours 的来源

```
total_hours = 所有购买套餐的时长总和

例如：
- 第一次购买：100小时
- 第二次购买：50小时
- 第三次购买：20小时
- 总计：170小时 → Level 11（黄金会员）
```

### 4. 套餐有效期的意义

- 用于计算会员何时过期
- 与等级计算无关
- 例如：年度会员365天后过期，但total_hours永久保留

### 5. 剩余时长的计算

```
remaining_hours = total_hours - used_hours

- total_hours: 累计充值（永久保留）
- used_hours: 从usage_logs表实时计算
- remaining_hours: 实际可用的时长

当 remaining_hours = 0 时，is_active = false（停用）
```

---

## 🔍 八、常见问题

### Q1: 为什么有两个系统？

**A**:
- **MembershipLevel**: 方便管理员配置不同的销售套餐
- **Fibonacci系统**: 给用户一个统一的、可成长的等级体系

### Q2: total_hours 和 duration_hours 的区别？

**A**:
- **total_hours**: 累计充值的总时长（永久保留，用于计算等级）
- **duration_hours**: 套餐的有效期时长（用于计算过期时间）

例如：年度会员
- duration_days: 365（有效期1年）
- total_hours: 累计充值时长（用于等级计算）

### Q3: 购买套餐后等级会立即提升吗？

**A**: 是的
- 购买100小时 → total_hours增加100
- Fibonacci系统立即重新计算等级
- 如果达到新的等级阈值，等级立即提升

### Q4: 会员过期后等级会降吗？

**A**:
- **会员过期**: is_active = false（无法使用功能）
- **等级保持**: level 不变（total_hours保留）
- **恢复使用**: 续费后恢复到原等级

### Q5: used_hours 如何计算？

**A**:
- 从 `usage_logs` 表实时计算
- 定时任务每10分钟更新一次
- 累加所有使用记录的 `duration_seconds`

---

## 📚 相关文件

- **模型定义**: `base/plugins/customer/models/membership.py`
- **业务逻辑**: `base/plugins/customer/services/membership_service.py`
- **Fibonacci系统**: `fibonacci_membership_service.py`
- **用户会员**: `customer_membership.py`
- **使用记录**: `usage_log.py`

---

**版本**: v1.0
**最后更新**: 2026-03-29
**状态**: ✅ 当前系统设计
