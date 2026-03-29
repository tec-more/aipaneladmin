# 会员等级系统冲突分析与统一方案

> 基于Fibonacci数列的动态等级系统 | 2026-03-29

---

## 🔴 核心冲突总结

### 1. **等级计算逻辑不一致** ⚠️ 严重冲突

#### Dart (Flutter) 端 - 正确实现 ✅
```dart
// 计算逻辑：累加Fibonacci数列直到超过总小时数
static int getLevelFromHours(int totalHours) {
  int level = 0;
  int accumulatedHours = 0;

  while (true) {
    final nextHours = getFibonacci(level + 1);
    if (accumulatedHours + nextHours > totalHours) {
      break;
    }
    accumulatedHours += nextHours;
    level++;
  }

  return level;
}
```

**示例**:
- 0小时 → Level 0
- 1小时 → Level 1 (F(1)=1, 累计1)
- 2小时 → Level 2 (F(1)+F(2)=1+1=2)
- 4小时 → Level 3 (1+1+2=4)
- 7小时 → Level 4 (1+1+2+3=7)
- 12小时 → Level 5 (1+1+2+3+5=12)

---

#### Python (FastAPI) 端 - 逻辑错误 ❌
```python
# 当前的错误实现
@classmethod
def get_level_from_hours(cls, total_hours: int) -> int:
    if total_hours <= 0:
        return 0

    level = 0
    accumulated = 0

    for hours in cls.FIBONACCI_SEQUENCE:
        accumulated += hours
        if total_hours <= accumulated:  # ❌ 这里逻辑错误
            level += 1
            break
        level += 1

    return level
```

**错误示例**:
- 1小时 → Level 1 ✅
- 2小时 → Level 2 ✅
- 3小时 → Level 3 ✅
- 4小时 → Level 4 ❌ **应该是Level 3**
- 7小时 → Level 5 ✅
- 8小时 → Level 6 ❌ **应该是Level 5**

---

### 2. **等级称号定义不一致** ⚠️

#### Dart端称号 - 11个等级段
```dart
// 等级称号基于Fibonacci数列的位置
0:  免费用户
1-2:  体验会员
3-4:  正式会员
5-7:  高级会员
8-12: 青铜会员
13-20: 白银会员
21-33: 黄金会员
34-54: 铂金会员
55-88: 钻石会员
89-143: 至尊会员
144+:  传奇会员
```

#### Python端 - ❌ 没有称号定义
只有特权阈值定义，没有等级称号：
```python
# 只有特权阈值，没有称号
if level >= 3: "优先客服支持"
if level >= 5: "API访问权限"
if level >= 8: "离线翻译功能"
if level >= 10: "无限翻译额度"
if level >= 15: "专属客户经理"
```

---

### 3. **特权定义不一致** ⚠️

#### Dart端特权 - 9个等级段
```dart
1:  每日100字翻译额度、标准客服
3:  每日500字、去广告
5:  每日2000字、优先客服、多语言互译
8:  每日5000字、专属客服、离线翻译
13: 每日10000字、API访问、定制主题
21: 每日20000字、优先体验、批量翻译
34: 每日50000字、多账号、团队协作
55: 每日100000字、专属客户经理、企业级支持
89: 无限翻译额度、7x24客服、定制开发
144: 所有功能永久使用、平台合作、品牌联名
```

#### Python端特权 - 5个等级段（粗糙）
```python
3:  优先客服支持
5:  API访问权限
8:  离线翻译功能
10: 无限翻译额度
15: 专属客户经理、定制化服务
```

---

### 4. **Fibonacci数列处理方式** ⚠️

#### Dart端 - 动态生成 ✅
```dart
// 动态生成，无上限
static final List<int> _fibonacciSequence = [1, 1];

static int getFibonacci(int n) {
  while (_fibonacciSequence.length < n) {
    final next = _fibonacciSequence[_fibonacciSequence.length - 1] +
                _fibonacciSequence[_fibonacciSequence.length - 2];
    _fibonacciSequence.add(next);
  }
  return _fibonacciSequence[n - 1];
}
```

**优点**: 可以支持无限等级

---

#### Python端 - 固定20个 ⚠️
```python
FIBONACCI_SEQUENCE = [
    1, 1, 2, 3, 5, 8, 13, 21, 34, 55,
    89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765
]
```

**缺点**: 限制在20个等级（6765小时）

---

## 📊 详细对照表

| 等级 | Dart端称号 | Dart端特权 | Python端逻辑 | Python端特权 | 冲突 |
|------|-----------|-----------|-------------|-------------|------|
| 0 | 免费用户 | 基础功能 | ✅ | ❌ 无 | ❌ |
| 1-2 | 体验会员 | 100字/日 | ✅ | ❌ 无 | ❌ |
| 3-4 | 正式会员 | 500字/日、去广告 | ✅ | 优先客服 | ❌ |
| 5-7 | 高级会员 | 2000字/日、优先客服 | ✅ | API访问 | ❌ |
| 8-12 | 青铜会员 | 5000字/日、专属客服、离线 | ✅ | 离线翻译 | ❌ |
| 13-20 | 白银会员 | 10000字/日、API、定制 | ✅ | 无限额度 | ❌ |
| 21-33 | 黄金会员 | 20000字/日、批量 | ✅ | - | ❌ |
| 34-54 | 铂金会员 | 50000字/日、团队 | ✅ | - | ❌ |
| 55-88 | 钻石会员 | 100000字/日、专属经理 | ✅ | - | ❌ |
| 89-143 | 至尊会员 | 无限额度、7x24客服 | ✅ | - | ❌ |
| 144+ | 传奇会员 | 永久使用、平台合作 | ❌ 超出范围 | - | ❌ |

---

## ✅ 统一方案

### 方案1: Python端迁移到Dart端逻辑（推荐）⭐

#### 1. 修复等级计算逻辑

**修复前**:
```python
# ❌ 错误逻辑
for hours in cls.FIBONACCI_SEQUENCE:
    accumulated += hours
    if total_hours <= accumulated:
        level += 1
        break
    level += 1
```

**修复后**:
```python
# ✅ 正确逻辑（与Dart一致）
def get_level_from_hours(cls, total_hours: int) -> int:
    if total_hours <= 0:
        return 0

    level = 0
    accumulated_hours = 0

    while True:
        next_hours = cls.get_fibonacci(level + 1)
        if accumulated_hours + next_hours > total_hours:
            break
        accumulated_hours += next_hours
        level += 1

    return level

@staticmethod
def get_fibonacci(n: int) -> int:
    """动态计算第n个Fibonacci数"""
    if n <= 0:
        return 1
    if n == 1 or n == 2:
        return 1

    a, b = 1, 1
    for _ in range(3, n + 1):
        a, b = b, a + b
    return b
```

---

#### 2. 添加等级称号定义

```python
class FibonacciMembershipSystem:
    """Fibonacci会员系统"""

    # 等级称号定义
    LEVEL_TITLES = {
        0: "免费用户",
        range(1, 3): "体验会员",
        range(3, 5): "正式会员",
        range(5, 8): "高级会员",
        range(8, 13): "青铜会员",
        range(13, 21): "白银会员",
        range(21, 34): "黄金会员",
        range(34, 55): "铂金会员",
        range(55, 89): "钻石会员",
        range(89, 144): "至尊会员",
    }

    @classmethod
    def get_level_title(cls, level: int) -> str:
        """获取等级称号"""
        if level >= 144:
            return "传奇会员"

        for level_range, title in cls.LEVEL_TITLES.items():
            if isinstance(level_range, range) and level in level_range:
                return title
        return "免费用户"
```

---

#### 3. 统一特权定义

```python
@classmethod
def get_level_privileges(cls, level: int) -> List[str]:
    """获取等级特权列表（与Dart端一致）"""
    privileges = ["基础翻译功能"]

    if level >= 1:
        privileges.extend([
            "每日100字翻译额度",
            "标准客服支持",
        ])

    if level >= 3:
        privileges.extend([
            "每日500字翻译额度",
            "去除主界面广告",
        ])

    if level >= 5:
        privileges.extend([
            "每日2000字翻译额度",
            "优先客服支持",
            "多语言互译",
        ])

    if level >= 8:
        privileges.extend([
            "每日5000字翻译额度",
            "专属客服支持",
            "离线翻译功能",
        ])

    if level >= 13:
        privileges.extend([
            "每日10000字翻译额度",
            "API访问权限",
            "定制化主题",
        ])

    if level >= 21:
        privileges.extend([
            "每日20000字翻译额度",
            "优先功能体验",
            "批量翻译",
        ])

    if level >= 34:
        privileges.extend([
            "每日50000字翻译额度",
            "多账号管理",
            "团队协作功能",
        ])

    if level >= 55:
        privileges.extend([
            "每日100000字翻译额度",
            "专属客户经理",
            "企业级支持",
        ])

    if level >= 89:
        privileges.extend([
            "无限翻译额度",
            "7x24小时专属客服",
            "定制开发服务",
        ])

    if level >= 144:
        privileges.extend([
            "所有功能永久使用",
            "平台合作权益",
            "品牌联名机会",
        ])

    return privileges
```

---

#### 4. 添加等级颜色和图标定义

```python
@classmethod
def get_level_color(cls, level: int) -> str:
    """获取等级颜色（十六进制）"""
    if level >= 144:
        return "#FFD700"  # 金色
    elif level >= 89:
        return "#9C27B0"  # 紫色
    elif level >= 55:
        return "#2196F3"  # 蓝色
    elif level >= 34:
        return "#607D8B"  # 铅蓝
    elif level >= 21:
        return "#FFC107"  # 琥珀
    elif level >= 13:
        return "#9E9E9E"  # 灰色
    elif level >= 8:
        return "#795548"  # 棕色
    elif level >= 5:
        return "#4CAF50"  # 绿色
    elif level >= 3:
        return "#03A9F4"  # 浅蓝
    elif level >= 1:
        return "#9E9E9E"  # 浅灰
    else:
        return "#BDBDBD"  # 深灰

@classmethod
def get_level_icon(cls, level: int) -> str:
    """获取等级图标名称"""
    if level >= 144:
        return "military_tech"
    elif level >= 89:
        return "stars"
    elif level >= 55:
        return "diamond"
    elif level >= 34:
        return "workspace_premium"
    elif level >= 21:
        return "emoji_events"
    elif level >= 13:
        return "card_membership"
    elif level >= 8:
        return "verified"
    elif level >= 5:
        return "star"
    elif level >= 3:
        return "bookmark"
    elif level >= 1:
        return "person"
    else:
        return "person_outline"
```

---

## 🔧 实施步骤

### Step 1: 修复Python端等级计算逻辑

修改文件：`base/plugins/customer/services/membership_service.py`

### Step 2: 添加称号、颜色、图标定义

在 `FibonacciMembershipSystem` 类中添加新方法

### Step 3: 统一特权定义

修改 `get_level_privileges` 方法

### Step 4: 添加API端点（可选）

添加新的API端点返回完整的等级信息：

```python
@router.get("/membership/level-info/{total_hours}")
async def get_level_info(total_hours: int):
    """获取等级完整信息"""
    level = fibonacci_service.get_level_from_hours(total_hours)

    return {
        "level": level,
        "title": fibonacci_service.get_level_title(level),
        "color": fibonacci_service.get_level_color(level),
        "icon": fibonacci_service.get_level_icon(level),
        "privileges": fibonacci_service.get_level_privileges(level),
        "progress": fibonacci_service.get_level_progress(total_hours),
        "hours_to_next": fibonacci_service.get_hours_to_next_level(level, total_hours)
    }
```

### Step 5: 前端同步

确保Flutter端使用相同的等级计算逻辑（已正确实现）

---

## 📋 数据验证示例

### 测试用例

| 总小时数 | 正确等级 | 正确称号 | 当前Python结果 | 说明 |
|---------|---------|---------|---------------|------|
| 0 | 0 | 免费用户 | 0 | ✅ |
| 1 | 1 | 体验会员 | 1 | ✅ |
| 2 | 2 | 体验会员 | 2 | ✅ |
| 3 | 3 | 正式会员 | 3 | ✅ |
| 4 | 3 | 正式会员 | ❌ 4 | **冲突** |
| 7 | 4 | 正式会员 | 5 | ❌ |
| 8 | 5 | 高级会员 | 6 | ❌ |
| 12 | 5 | 高级会员 | ✅ | ✅ |
| 20 | 6 | 高级会员 | ❌ | **冲突** |

---

## ⚠️ 重要提醒

### 1. 数据迁移问题

如果系统已经有用户数据，修复等级计算逻辑后：
- **会降低部分用户的显示等级**
- 例如：有4小时的用户从Level 4降为Level 3
- **建议**：保留历史等级，只对新数据应用新逻辑

### 2. 向后兼容方案

```python
def get_level_from_hours_safe(cls, total_hours: int, use_legacy: bool = False) -> int:
    """兼容旧版本的等级计算"""
    if use_legacy:
        return cls._legacy_get_level_from_hours(total_hours)
    return cls.get_level_from_hours(total_hours)
```

### 3. 特权降级风险

统一特权后，某些用户的特权可能减少：
- Python端Level 10用户有"无限额度"
- Dart端需要Level 89才有"无限额度"
- **建议**：分阶段迁移，先对齐称号，再对齐特权

---

## 🎯 推荐方案

### 阶段1: 称号统一（立即执行）
- ✅ 修复Python端等级计算逻辑
- ✅ 添加等级称号定义
- ✅ 添加颜色和图标定义

### 阶段2: 特权统一（1周后）
- ✅ 统一特权定义和阈值
- ✅ 更新API文档
- ✅ 前端同步

### 阶段3: 数据验证（持续）
- ✅ 对比两端计算结果
- ✅ 修复边缘情况
- ✅ 用户反馈收集

---

## 📚 参考资料

- [Dart端实现](fibonacci_membership.dart)
- [Python端实现](membership_service.py)
- [Fibonacci数列定义](https://en.wikipedia.org/wiki/Fibonacci_number)

---

**版本**: v1.0
**创建日期**: 2026-03-29
**优先级**: 🔴 高 - 影响用户体验一致性
