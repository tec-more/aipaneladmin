# AIF2F 集成方案设计文档

## 1. 项目概述

将 Flutter AI传译应用（aif2f）的用户管理、会员系统、支付功能集成到 AIPanelAdmin 后台管理系统。

## 2. 系统架构

### 2.1 技术栈
- **后端框架**: FastAPI + Tortoise ORM
- **数据库**: PostgreSQL
- **支付**: 微信支付、支付宝
- **状态同步**: RESTful API
- **认证**: JWT Token

### 2.2 模块划分

```
aif2f/
├── models/              # 数据模型
│   ├── aif2f_user.py           # AIF2F用户扩展
│   ├── membership.py           # 会员等级配置
│   ├── user_membership.py      # 用户会员关系
│   ├── recharge_order.py       # 充值订单
│   ├── payment_transaction.py  # 支付交易记录
│   └── usage_log.py            # 使用记录
├── api/v1/              # API接口
│   ├── user.py                # 用户管理API
│   ├── membership.py          # 会员API
│   ├── payment.py             # 支付API
│   └── webhook.py             # 支付回调Webhook
├── schemas/             # Pydantic Schema
│   ├── user.py
│   ├── membership.py
│   └── payment.py
├── services/            # 业务逻辑
│   ├── membership_service.py   # 会员服务
│   ├── payment_service.py      # 支付服务
│   ├── wechat_pay.py          # 微信支付
│   └── alipay.py              # 支付宝
├── manifest.json       # 插件配置
└── __init__.py
```

## 3. 数据库设计

### 3.1 会员等级表 (MembershipLevel)

```python
class MembershipLevel(BaseModel):
    """会员等级配置表"""
    level_type = fields.CharEnumField(LevelType, max_length=20)  # TRIAL, MONTHLY, QUARTERLY等
    level = fields.IntField(description="等级数字(用于Fibonacci系统)")
    name = fields.CharField(max_length=50, description="等级名称")
    duration_days = fields.IntField(description="有效期天数")
    duration_hours = fields.IntField(default=0, description="有效期小时数")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="价格")
    original_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="原价")
    bonus_hours = fields.IntField(default=0, description="赠送小时数")
    features = fields.JSONField(default=list, description="特权列表")
    sort_order = fields.IntField(default=0, description="排序")
    is_active = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "aif2f_membership_level"
```

### 3.2 用户会员关系表 (UserMembership)

```python
class UserMembership(BaseModel):
    """用户会员信息表"""
    user = fields.ForeignKeyField("models.User", related_name="aif2f_memberships")
    membership_level = fields.ForeignKeyField("models.MembershipLevel", related_name="users")
    start_time = fields.DatetimeField(description="开始时间")
    expire_time = fields.DatetimeField(description="过期时间")
    total_hours = fields.IntField(default=0, description="总小时数")
    used_hours = fields.DecimalField(max_digits=10, decimal_places=2, default=0, description="已使用小时数")
    remaining_hours = fields.DecimalField(max_digits=10, decimal_places=2, default=0, description="剩余小时数")
    level = fields.IntField(default=0, description="Fibonacci等级")
    is_active = fields.BooleanField(default=True, description="是否激活")
    auto_renew = fields.BooleanField(default=False, description="是否自动续费")

    class Meta:
        table = "aif2f_user_membership"
```

### 3.3 充值订单表 (RechargeOrder)

```python
class RechargeOrder(BaseModel):
    """充值订单表"""
    order_no = fields.CharField(max_length=64, unique=True, description="订单号")
    user = fields.ForeignKeyField("models.User", related_name="recharge_orders")
    membership_level = fields.ForeignKeyField("models.MembershipLevel", related_name="orders")
    amount = fields.DecimalField(max_digits=10, decimal_places=2, description="支付金额")
    hours = fields.IntField(description="购买小时数")
    bonus_hours = fields.IntField(default=0, description="赠送小时数")
    payment_method = fields.CharEnumField(PaymentMethod, max_length=20)  # WECHAT, ALIPAY
    payment_status = fields.CharEnumField(OrderStatus, max_length=20, default=OrderStatus.PENDING)
    trade_no = fields.CharField(max_length=128, null=True, description="第三方交易号")
    pay_time = fields.DatetimeField(null=True, description="支付时间")
    expire_time = fields.DatetimeField(description="订单过期时间")
    client_ip = fields.CharField(max_length=50, null=True, description="客户端IP")
    device_info = fields.JSONField(null=True, description="设备信息")

    class Meta:
        table = "aif2f_recharge_order"
```

### 3.4 支付交易记录表 (PaymentTransaction)

```python
class PaymentTransaction(BaseModel):
    """支付交易记录表"""
    order = fields.ForeignKeyField("models.RechargeOrder", related_name="transactions")
    transaction_id = fields.CharField(max_length=128, unique=True, description="交易ID")
    transaction_type = fields.CharEnumField(PaymentMethod, max_length=20)
    amount = fields.DecimalField(max_digits=10, decimal_places=2, description="交易金额")
    status = fields.CharEnumField(TransactionStatus, max_length=20)
    notify_data = fields.JSONField(description="回调通知数据")
    processed_at = fields.DatetimeField(auto_now_add=True, description="处理时间")

    class Meta:
        table = "aif2f_payment_transaction"
```

### 3.5 使用记录表 (UsageLog)

```python
class UsageLog(BaseModel):
    """翻译使用记录表"""
    user = fields.ForeignKeyField("models.User", related_name="aif2f_usage_logs")
    session_id = fields.CharField(max_length=64, description="会话ID")
    duration_seconds = fields.IntField(description="使用时长(秒)")
    source_text = fields.TextField(description="原文")
    translated_text = fields.TextField(description="译文")
    source_lang = fields.CharField(max_length=10, description="源语言")
    target_lang = fields.CharField(max_length=10, description="目标语言")
    characters_count = fields.IntField(description="字符数")
    api_cost = fields.DecimalField(max_digits=10, decimal_places=4, description="API成本")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "aif2f_usage_log"
```

## 4. API接口设计

### 4.1 用户管理 API

#### 4.1.1 获取用户信息
```
GET /api/v1/aif2f/user/profile
Response: {
  "code": 200,
  "data": {
    "id": 1,
    "username": "test",
    "email": "test@example.com",
    "membership": {
      "level": "MONTHLY",
      "level_name": "月度会员",
      "expire_time": "2025-03-01T00:00:00",
      "remaining_hours": 25.5,
      "total_hours": 30
    }
  }
}
```

#### 4.1.2 更新用户信息
```
PUT /api/v1/aif2f/user/profile
Body: {
  "nickname": "新昵称",
  "avatar": "https://..."
}
```

### 4.2 会员系统 API

#### 4.2.1 获取会员等级列表
```
GET /api/v1/aif2f/membership/levels
Response: {
  "code": 200,
  "data": [
    {
      "level": 1,
      "name": "体验会员",
      "duration_hours": 7,
      "price": "0.00",
      "features": ["基础翻译", "7天有效期"]
    }
  ]
}
```

#### 4.2.2 获取我的会员信息
```
GET /api/v1/aif2f/membership/my
Response: {
  "code": 200,
  "data": {
    "level": 5,
    "remaining_hours": 25.5,
    "expire_time": "2025-03-01T00:00:00",
    "is_expired": false
  }
}
```

#### 4.2.3 计算Fibonacci等级
```
GET /api/v1/aif2f/membership/fibonacci-level?hours=30
Response: {
  "code": 200,
  "data": {
    "level": 8,
    "next_level_hours": 34,
    "remaining_to_next": 4
  }
}
```

### 4.3 支付系统 API

#### 4.3.1 创建充值订单
```
POST /api/v1/aif2f/payment/create-order
Body: {
  "membership_level_id": 1,
  "payment_method": "WECHAT"
}
Response: {
  "code": 200,
  "data": {
    "order_no": "ORD20250201123456789",
    "amount": "0.01",
    "qr_code": "https://...",  // 二维码链接
    "expire_time": "2025-02-01T12:35:00"
  }
}
```

#### 4.3.2 查询订单状态
```
GET /api/v1/aif2f/payment/order/{order_no}
Response: {
  "code": 200,
  "data": {
    "order_no": "ORD20250201123456789",
    "status": "PAID",
    "pay_time": "2025-02-01T12:30:00"
  }
}
```

### 4.4 支付回调 Webhook

#### 4.4.1 微信支付回调
```
POST /api/v1/aif2f/payment/wechat/notify
Content-Type: application/xml
```

#### 4.4.2 支付宝回调
```
POST /api/v1/aif2f/payment/alipay/notify
```

## 5. 支付集成方案

### 5.1 微信支付
- **方式**: Native支付（扫码支付）或 H5支付
- **流程**:
  1. 客户端请求创建订单
  2. 后端调用微信统一下单API
  3. 返回支付链接或二维码
  4. 用户完成支付
  5. 微信回调通知后端
  6. 后端验证并更新订单状态
  7. 客户端轮询获取支付结果

### 5.2 支付宝
- **方式**: 手机网站支付或当面付
- **流程**: 类似微信支付

### 5.3 安全措施
- 订单签名验证
- 回调通知签名验证
- 防重复通知处理
- 订单过期机制（15分钟）
- IP白名单（可选）

## 6. 权限设计

集成到现有RBAC系统：

### 6.1 新增权限
```
aif2f:user:view          # 查看用户信息
aif2f:user:edit          # 编辑用户信息
aif2f:membership:view    # 查看会员信息
aif2f:membership:edit    # 编辑会员信息
aif2f:order:view         # 查看订单
aif2f:order:refund       # 订单退款
aif2f:statistics:view    # 查看统计数据
```

### 6.2 角色配置
- **普通用户**: aif2f:user:view, aif2f:membership:view
- **VIP用户**: 同普通用户
- **管理员**: 所有权限

## 7. Fibonacci会员系统实现

### 7.1 Fibonacci数列
```python
FIBONACCI_SEQUENCE = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, ...]

def calculate_level(total_hours: int) -> int:
    """
    根据总充值小时数计算等级
    每1小时等级+1，等级对应Fibonacci数列位置
    """
    # 等级1: 1小时
    # 等级2: 1小时
    # 等级3: 2小时
    # 等级4: 3小时
    # 等级5: 5小时
    # ...
    pass
```

### 7.2 等级特权
| 等级 | 所需小时 | 特权 |
|-----|---------|-----|
| 1-3 | 1-2小时 | 基础翻译 |
| 4-5 | 3-5小时 | 优先客服 |
| 6-8 | 8-21小时 | API访问 |
| 9+ | 34+小时 | 离线翻译、无限额度 |

## 8. 实施计划

### Phase 1: 数据模型和基础API (Week 1)
- [ ] 创建数据模型
- [ ] 实现用户API
- [ ] 实现会员API
- [ ] 编写单元测试

### Phase 2: 支付系统 (Week 2)
- [ ] 集成微信支付SDK
- [ ] 集成支付宝SDK
- [ ] 实现支付API
- [ ] 实现回调处理

### Phase 3: 业务逻辑 (Week 3)
- [ ] 实现Fibonacci等级计算
- [ ] 实现会员过期检测
- [ ] 实现使用记录统计
- [ ] 实现数据报表

### Phase 4: 测试和优化 (Week 4)
- [ ] 集成测试
- [ ] 性能优化
- [ ] 安全加固
- [ ] 文档完善

## 9. 配置文件

### config.conf 新增配置
```ini
[aif2f]
# AIF2F插件配置
enabled = true

[aif2f.payment]
# 支付配置
wechat_app_id =
wechat_mch_id =
wechat_api_key =
wechat_api_cert_path =
wechat_api_key_path =
alipay_app_id =
alipay_private_key_path =
alipay_public_key_path =

[aif2f.membership]
# 会员配置
default_free_hours = 0
max_fibonacci_level = 20
```

## 10. 监控和日志

### 10.1 关键指标
- 日活用户数 (DAU)
- 充值订单数
- 支付成功率
- 会员转化率
- 平均使用时长

### 10.2 日志记录
- 所有支付交易
- 会员变更记录
- API调用日志
- 异常错误日志
