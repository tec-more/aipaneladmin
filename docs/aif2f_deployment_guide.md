# AIF2F 插件部署指南

## 1. 数据库迁移

插件已创建，需要执行数据库迁移来创建数据表。

### 1.1 初始化迁移

```bash
# 在项目根目录执行
aerich init -t base.common.database.TORTOISE_ORM

# 生成迁移文件
aerich migrate

# 执行迁移
aerich upgrade
```

### 1.2 创建的数据表

执行迁移后，会创建以下数据表：

- `aif2f_membership_level` - 会员等级配置表
- `aif2f_user_membership` - 用户会员关系表
- `aif2f_recharge_order` - 充值订单表
- `aif2f_payment_transaction` - 支付交易记录表
- `aif2f_usage_log` - 使用记录表

## 2. 初始化数据

### 2.1 初始化会员等级

应用启动后，会自动初始化默认会员等级。也可以手动调用：

```python
from base.plugins.aif2f.hooks import init_default_membership_levels
await init_default_membership_levels()
```

默认会员等级包括：

| 等级名称 | 类型 | 价格 | 时长 | 赠送 |
|---------|-----|------|------|-----|
| 体验会员 | TRIAL | 免费 | 7天 | 0 |
| 月度会员 | MONTHLY | ¥29.9 | 30天 | 0 |
| 季度会员 | QUARTERLY | ¥79.9 | 90天 | 0 |
| 1小时 | FIBONACCI | ¥1.0 | 1小时 | 0 |
| 5小时 | FIBONACCI | ¥5.0 | 5小时 | 1小时 |
| 20小时 | FIBONACCI | ¥20.0 | 20小时 | 5小时 |
| 50小时 | FIBONACCI | ¥50.0 | 50小时 | 10小时 |

## 3. 配置支付

### 3.1 微信支付配置

编辑 `config.conf`，填写微信支付配置：

```ini
[aif2f.payment.wechat]
wechat_app_id = your_app_id
wechat_mch_id = your_mch_id
wechat_api_key = your_api_key
wechat_api_cert_path = /path/to/cert.pem
wechat_api_key_path = /path/to/key.pem
wechat_notify_url = https://yourdomain.com/api/v1/aif2f/payment/wechat/notify
```

### 3.2 支付宝配置

编辑 `config.conf`，填写支付宝配置：

```ini
[aif2f.payment.alipay]
alipay_app_id = your_app_id
alipay_private_key_path = /path/to/private_key.pem
alipay_public_key_path = /path/to/public_key.pem
alipay_notify_url = https://yourdomain.com/api/v1/aif2f/payment/alipay/notify
```

### 3.3 获取支付凭证

#### 微信支付
1. 登录 [微信支付商户平台](https://pay.weixin.qq.com/)
2. 获取商户号(mch_id)和API密钥(api_key)
3. 下载API证书
4. 配置回调URL

#### 支付宝
1. 登录 [支付宝开放平台](https://open.alipay.com/)
2. 创建应用并获取APPID
3. 上传公钥并获取支付宝公钥
4. 配置回调URL

## 4. API 接口说明

### 4.1 用户相关

#### 获取用户资料
```http
GET /api/v1/aif2f/user/profile
Authorization: Bearer {token}
```

#### 更新用户资料
```http
PUT /api/v1/aif2f/user/profile
Authorization: Bearer {token}
Content-Type: application/json

{
  "nickname": "新昵称",
  "avatar": "https://..."
}
```

#### 获取我的会员信息
```http
GET /api/v1/aif2f/user/membership
Authorization: Bearer {token}
```

### 4.2 会员相关

#### 获取会员等级列表
```http
GET /api/v1/aif2f/membership/levels?active_only=true
```

#### 计算Fibonacci等级
```http
GET /api/v1/aif2f/membership/fibonacci-level?hours=30
```

### 4.3 支付相关

#### 创建充值订单
```http
POST /api/v1/aif2f/payment/create-order
Authorization: Bearer {token}
Content-Type: application/json

{
  "membership_level_id": 4,
  "payment_method": "wechat"
}
```

响应：
```json
{
  "code": 200,
  "data": {
    "order_no": "ORD20250201123456789",
    "amount": "20.00",
    "qr_code": "weixin://wxpay/bizpayurl?pr=xxxxx",
    "expire_time": "2025-02-01T12:35:00"
  }
}
```

#### 查询订单状态
```http
GET /api/v1/aif2f/payment/order/{order_no}
Authorization: Bearer {token}
```

#### 取消订单
```http
POST /api/v1/aif2f/payment/cancel-order/{order_no}
Authorization: Bearer {token}
```

## 5. Flutter 集成示例

### 5.1 配置 API 基础URL

```dart
// lib/core/config/api_config.dart
class ApiConfig {
  static const String baseUrl = 'https://yourdomain.com/api/v1';
  static const String aif2fBaseUrl = '$baseUrl/aif2f';
}
```

### 5.2 用户服务示例

```dart
// lib/user/services/user_service.dart
import 'dart:convert';
import 'package:dio/dio.dart';

class UserService {
  final Dio _dio = Dio();
  final String _baseUrl = ApiConfig.aif2fBaseUrl;

  // 获取用户资料
  Future<Map<String, dynamic>> getUserProfile(String token) async {
    final response = await _dio.get(
      '$_baseUrl/user/profile',
      options: Options(
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return response.data['data'];
  }

  // 获取会员信息
  Future<Map<String, dynamic>> getMembershipInfo(String token) async {
    final response = await _dio.get(
      '$_baseUrl/user/membership',
      options: Options(
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return response.data['data'];
  }

  // 获取会员等级列表
  Future<List<dynamic>> getMembershipLevels() async {
    final response = await _dio.get('$_baseUrl/membership/levels');
    return response.data['data'];
  }

  // 创建充值订单
  Future<Map<String, dynamic>> createRechargeOrder({
    required String token,
    required int membershipLevelId,
    required String paymentMethod,
  }) async {
    final response = await _dio.post(
      '$_baseUrl/payment/create-order',
      data: {
        'membership_level_id': membershipLevelId,
        'payment_method': paymentMethod,
      },
      options: Options(
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return response.data['data'];
  }

  // 查询订单状态
  Future<Map<String, dynamic>> checkOrderStatus({
    required String token,
    required String orderNo,
  }) async {
    final response = await _dio.get(
      '$_baseUrl/payment/order/$orderNo',
      options: Options(
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return response.data['data'];
  }
}
```

### 5.3 会员界面示例

```dart
// lib/user/screens/membership_screen.dart
import 'package:flutter/material.dart';

class MembershipScreen extends StatefulWidget {
  @override
  _MembershipScreenState createState() => _MembershipScreenState();
}

class _MembershipScreenState extends State<MembershipScreen> {
  List<dynamic> membershipLevels = [];
  Map<String, dynamic>? myMembership;
  bool isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    // 加载会员等级列表
    levels = await UserService().getMembershipLevels();
    // 加载我的会员信息
    myMembership = await UserService().getMembershipInfo(token);
    setState(() {
      isLoading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('会员中心')),
      body: isLoading
          ? Center(child: CircularProgressIndicator())
          : ListView.builder(
              itemCount: membershipLevels.length,
              itemBuilder: (context, index) {
                final level = membershipLevels[index];
                return MembershipCard(
                  level: level,
                  onTap: () => _purchaseMembership(level),
                );
              },
            ),
    );
  }

  Future<void> _purchaseMembership(dynamic level) async {
    // 创建订单
    final order = await UserService().createRechargeOrder(
      token: userToken,
      membershipLevelId: level['id'],
      paymentMethod: 'wechat',
    );

    // 显示支付二维码
    showDialog(
      context: context,
      builder: (context) => PaymentDialog(
        orderNo: order['order_no'],
        qrCode: order['qr_code'],
        amount: order['amount'],
      ),
    );

    // 轮询检查支付状态
    _checkPaymentStatus(order['order_no']);
  }

  Future<void> _checkPaymentStatus(String orderNo) async {
    while (true) {
      await Future.delayed(Duration(seconds: 3));
      final status = await UserService().checkOrderStatus(
        token: userToken,
        orderNo: orderNo,
      );

      if (status['payment_status'] == 'paid') {
        Navigator.of(context).pop();
        _loadData();
        break;
      }
    }
  }
}
```

## 6. 测试

### 6.1 测试用户注册/登录

使用现有的用户系统进行注册/登录。

### 6.2 测试会员功能

1. 获取会员等级列表
2. 查看Fibonacci等级计算
3. 创建测试订单

### 6.3 测试支付（沙箱环境）

微信支付和支付宝都提供沙箱环境用于测试：

- 微信支付沙箱：https://pay.weixin.qq.com/wiki/doc/api/sl/ppt.php?chapter=23_1
- 支付宝沙箱：https://opendocs.alipay.com/open/270/105899

## 7. 部署检查清单

- [ ] 数据库迁移已执行
- [ ] 会员等级数据已初始化
- [ ] 微信支付配置已填写
- [ ] 支付宝配置已填写
- [ ] 回调URL已配置并可访问
- [ ] HTTPS证书已配置（支付必须HTTPS）
- [ ] 防火墙已开放必要端口
- [ ] 定时任务已配置（检查过期订单）

## 8. 常见问题

### Q: 订单创建成功但支付失败？
A: 检查支付配置是否正确，确认回调URL可以访问。

### Q: 支付成功后会员状态未更新？
A: 检查支付回调是否正常处理，查看日志中的错误信息。

### Q: Fibonacci等级计算不对？
A: 确认总小时数正确，等级计算基于Fibonacci数列累加。

### Q: 如何测试支付功能？
A: 使用沙箱环境测试，不要使用真实金额。

## 9. 后续优化建议

1. **定时任务**：添加定时任务自动检查过期订单和会员
2. **通知系统**：支付成功、会员过期等事件通知用户
3. **数据统计**：添加收入统计、用户增长统计等
4. **风控系统**：添加防刷、异常交易检测
5. **推广系统**：邀请奖励、优惠码等营销功能
