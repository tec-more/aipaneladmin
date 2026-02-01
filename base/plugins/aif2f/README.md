# AIF2F 插件 - AI传译系统集成

## 📖 简介

AIF2F 插件将 Flutter AI传译应用的用户管理、会员系统、支付功能完整集成到 AIPanelAdmin 后台管理系统中。

## ✨ 核心功能

### 1. Fibonacci 会员系统
- 基于 Fibonacci 数列的无限等级设计
- 每充值 1 小时等级 +1
- 等级越高，特权越多
- 支持传统会员等级（月度、季度、年度）

### 2. 支付系统集成
- 微信支付（Native 扫码支付）
- 支付宝（扫码支付）
- 订单管理和状态跟踪
- 支付回调处理

### 3. 用户管理
- 用户资料管理
- 会员信息查询
- 使用记录统计

## 📁 目录结构

```
aif2f/
├── models/                 # 数据模型
│   ├── membership.py       # 会员等级模型
│   ├── user_membership.py  # 用户会员关系
│   ├── recharge_order.py   # 充值订单
│   ├── payment_transaction.py  # 支付交易
│   └── usage_log.py        # 使用记录
├── api/v1/                 # API 接口
│   ├── user.py             # 用户 API
│   ├── membership.py       # 会员 API
│   ├── payment.py          # 支付 API
│   └── __init__.py
├── schemas/                # Pydantic Schema
│   ├── membership.py
│   ├── payment.py
│   └── user.py
├── services/               # 业务逻辑
│   ├── membership_service.py  # 会员服务
│   └── payment_service.py     # 支付服务
├── hooks.py                # 插件钩子
├── manifest.json           # 插件配置
└── README.md               # 说明文档
```

## 🚀 快速开始

### 1. 数据库迁移

```bash
# 初始化 Aerich
aerich init -t base.common.database.TORTOISE_ORM

# 生成迁移文件
aerich migrate

# 执行迁移
aerich upgrade
```

### 2. 配置支付

编辑 `config.conf`，填写支付配置：

```ini
[aif2f.payment.wechat]
wechat_app_id = your_app_id
wechat_mch_id = your_mch_id
wechat_api_key = your_api_key
# ... 其他配置

[aif2f.payment.alipay]
alipay_app_id = your_app_id
alipay_private_key_path = /path/to/key
# ... 其他配置
```

### 3. 启动应用

```bash
python run.py
```

应用启动后，插件会自动：
- 初始化默认会员等级
- 注册 API 路由
- 注册管理菜单
- 创建权限定义

## 📊 Fibonacci 会员系统说明

### 等级计算规则

Fibonacci 数列：1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ...

| 等级 | 需要小时数 | 说明 |
|-----|----------|-----|
| 1 | 1小时 | 基础翻译 |
| 2 | 2小时 (1+1) | 基础翻译 |
| 3 | 4小时 (1+1+2) | 基础翻译 |
| 4 | 7小时 (1+1+2+3) | 优先客服 |
| 5 | 12小时 (1+1+2+3+5) | 优先客服 |
| 6 | 20小时 | API访问 |
| 7 | 33小时 | API访问 |
| 8 | 54小时 | 离线翻译 |
| 9+ | ... | 更多特权 |

### 等级特权

| 等级范围 | 特权 |
|---------|-----|
| 1-3 | 基础翻译功能 |
| 4-5 | 优先客服支持 |
| 6-8 | API访问权限 |
| 9-10 | 离线翻译功能、无限额度 |
| 15+ | 专属客户经理、定制化服务 |

## 🔌 API 接口

### 用户相关
- `GET /api/v1/aif2f/user/profile` - 获取用户资料
- `PUT /api/v1/aif2f/user/profile` - 更新用户资料
- `GET /api/v1/aif2f/user/membership` - 获取我的会员信息

### 会员相关
- `GET /api/v1/aif2f/membership/levels` - 获取会员等级列表
- `GET /api/v1/aif2f/membership/fibonacci-level` - 计算 Fibonacci 等级
- `GET /api/v1/aif2f/membership/my-level` - 获取我的会员等级

### 支付相关
- `POST /api/v1/aif2f/payment/create-order` - 创建充值订单
- `GET /api/v1/aif2f/payment/order/{order_no}` - 查询订单状态
- `POST /api/v1/aif2f/payment/cancel-order/{order_no}` - 取消订单
- `POST /api/v1/aif2f/payment/wechat/notify` - 微信支付回调
- `POST /api/v1/aif2f/payment/alipay/notify` - 支付宝回调

## 🔐 权限说明

插件会自动创建以下权限：

- `aif2f:user:view` - 查看用户信息
- `aif2f:user:edit` - 编辑用户信息
- `aif2f:membership:view` - 查看会员信息
- `aif2f:membership:edit` - 编辑会员信息
- `aif2f:order:view` - 查看订单
- `aif2f:order:refund` - 订单退款
- `aif2f:statistics:view` - 查看统计数据

## 📱 Flutter 集成

详见部署指南：`docs/aif2f_deployment_guide.md`

简要步骤：

1. 配置 API 基础 URL
2. 实现用户认证（JWT Token）
3. 调用会员和支付 API
4. 处理支付流程

## 🛠️ 开发计划

- [x] 数据模型设计
- [x] Fibonacci 会员系统实现
- [x] 支付服务框架
- [x] API 接口实现
- [ ] 完整的微信支付 SDK 集成
- [ ] 完整的支付宝 SDK 集成
- [ ] 定时任务（检查过期订单）
- [ ] 数据统计功能
- [ ] 前端管理界面

## 📝 注意事项

1. **支付安全**
   - 务必使用 HTTPS
   - 验证所有回调签名
   - 防止重复通知

2. **数据库备份**
   - 定期备份订单数据
   - 备份支付交易记录

3. **日志监控**
   - 记录所有支付操作
   - 监控异常交易

## 📄 相关文档

- [集成方案设计](../../docs/aif2f_integration_design.md)
- [部署指南](../../docs/aif2f_deployment_guide.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
