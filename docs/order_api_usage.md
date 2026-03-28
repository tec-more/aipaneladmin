# 订单系统使用说明

## 📋 概述

订单系统已重构为**订单主表 + 订单明细表**的标准电商结构，支持多种商品类型（会员、点券、道具等）。

---

## 🎯 核心概念

### **订单主表（CustomerOrder）**
- 存储订单的基本信息：客户、金额、支付状态等
- 一个订单可以有多个明细

### **订单明细表（OrderItem）**
- 存储订单中的每个商品信息
- 包含产品名称、数量、单价、扩展信息等

---

## 📡 API 接口说明

### **1. 创建订单（通用接口）**

**接口**: `POST /v1/orders/create`

**适用场景**：购买多种商品组合

**请求示例**：
```json
{
  "customer_id": 1,
  "items": [
    {
      "product_id": null,
      "product_name": "SVIP会员",
      "product_type": "membership",
      "quantity": 1,
      "unit_price": 15.00,
      "extra_info": {
        "membership_level_id": 1,
        "membership_level_name": "SVIP",
        "hours": 100,
        "bonus_hours": 20,
        "total_hours": 120
      }
    },
    {
      "product_id": 2,
      "product_name": "点券充值",
      "product_type": "points",
      "quantity": 100,
      "unit_price": 0.10,
      "extra_info": {
        "points": 10000
      }
    }
  ],
  "payment_method": "wechat",
  "client_ip": "192.168.1.100",
  "device_info": {
    "platform": "web",
    "user_agent": "Chrome"
  }
}
```

**响应示例**：
```json
{
  "success": true,
  "msg": "订单创建成功",
  "data": {
    "order_id": 123,
    "order_no": "ORD20260327153045123456",
    "total_amount": 25.00,
    "final_amount": 25.00
  }
}
```

---

### **2. 创建会员充值订单（便捷接口）**

**接口**: `POST /v1/orders/create-membership`

**适用场景**：只购买一个会员等级（最常用）

**请求参数**：
- `customer_id`: 客户ID
- `membership_level_id`: 会员等级ID
- `payment_method`: 支付方式
- `client_ip`: 客户端IP（可选）

**前端调用示例**：
```javascript
// 前端调用示例
import { request } from '@/utils/request'

// 创建会员订单
const response = await request.post('/v1/orders/create-membership', {
  customer_id: 1,
  membership_level_id: 2,
  payment_method: 'wechat',
  client_ip: '192.168.1.100'
})

console.log(response.data.order_no) // 订单号
```

---

### **3. 查询订单详情**

**接口**: `GET /v1/orders/{order_id}` 或 `GET /v1/orders/by-order-no/{order_no}`

**响应示例**：
```json
{
  "success": true,
  "msg": "获取订单详情成功",
  "data": {
    "id": 123,
    "order_no": "ORD20260327153045123456",
    "customer_id": 1,
    "customer_name": "张三",
    "total_amount": 25.00,
    "discount_amount": 0.00,
    "final_amount": 25.00,
    "payment_method": "wechat",
    "payment_status": "pending",
    "pay_time": null,
    "expire_time": "2026-03-27 15:45:45",
    "created_at": "2026-03-27 15:30:45",
    "items": [
      {
        "id": 1,
        "product_name": "SVIP会员",
        "product_type": "membership",
        "quantity": 1,
        "unit_price": 15.00,
        "total_price": 15.00,
        "extra_info": {
          "membership_level_id": 1,
          "hours": 100,
          "bonus_hours": 20,
          "total_hours": 120
        }
      }
    ]
  }
}
```

---

### **4. 查询订单列表**

**接口**: `GET /v1/orders/` 或 `GET /v1/orders/customer/{customer_id}`

**查询参数**：
- `page`: 页码（默认1）
- `page_size`: 每页数量（默认20）

---

### **5. 更新支付状态**

**接口**: `PATCH /v1/orders/{order_id}/payment-status`

**请求示例**：
```json
{
  "payment_status": "paid",
  "payment_method": "wechat",
  "transaction_id": "4200001234567890"
}
```

---

## 💻 前端集成示例

### **创建订单流程**

```javascript
// 1. 用户选择会员套餐
const selectedPackage = {
  id: 2,
  name: "SVIP会员",
  price: 15.00,
  hours: 100
}

// 2. 创建订单
const createOrder = async () => {
  try {
    // 方式一：使用便捷接口（推荐）
    const response = await request.post('/v1/orders/create-membership', {
      customer_id: userId,
      membership_level_id: selectedPackage.id,
      payment_method: 'wechat'
    })

    const { order_no, final_amount } = response.data

    // 3. 调用微信支付
    const payResponse = await request.post('/v1/pay/wechat/native/create', {
      order_no: order_no,
      total_fee: final_amount * 100, // 转换为分
      body: selectedPackage.name
    })

    // 4. 显示支付二维码
    showQRCode(payResponse.data.code_url)

    // 5. 开始轮询支付状态
    startPolling(order_no)

  } catch (error) {
    console.error('创建订单失败:', error)
  }
}

// 轮询支付状态
const startPolling = (orderNo) => {
  const timer = setInterval(async () => {
    const response = await request.get(`/v1/pay/wechat/native/poll/${orderNo}`)

    if (response.data.status === 'success') {
      clearInterval(timer)
      // 支付成功，跳转或刷新页面
      router.push('/order/success')
    } else if (response.data.status === 'closed') {
      clearInterval(timer)
      // 订单已关闭
      alert('订单已关闭')
    }
  }, 3000) // 每3秒轮询一次

  // 15分钟后停止轮询
  setTimeout(() => clearInterval(timer), 15 * 60 * 1000)
}
```

---

## 🔌 后端调用示例

### **在支付回调中处理订单**

```python
from base.plugins.order.services.order_service import OrderService

async def process_payment_callback(order_no: str, transaction_id: str, amount: float):
    """处理支付回调"""
    success = await OrderService.process_payment_callback(
        order_no=order_no,
        transaction_id=transaction_id,
        transaction_type="wechat_pay",
        amount=amount,
        notify_data={...}
    )

    if success:
        print(f"订单 {order_no} 支付成功")
        # 发送通知、更新会员等
    else:
        print(f"订单 {order_no} 处理失败")
```

---

## 📊 数据库变更说明

### **新增字段**

**customer_order 表**：
- `total_amount`: 订单总金额
- `discount_amount`: 优惠金额
- `final_amount`: 实际支付金额

**order_item 表**（新建）：
- 所有字段都是新增的

### **删除字段**

迁移完成后可以删除：
- `membership_level_id`: 已移到 `extra_info`
- `hours`: 已移到 `extra_info`
- `bonus_hours`: 已移到 `extra_info`
- `total_hours`: 已移到 `extra_info`
- `amount`: 已改为 `total_amount` 和 `final_amount`

---

## ⚠️ 重要提示

1. **订单创建时机**：在选择套餐后、展示支付二维码前创建订单
2. **订单过期**：订单创建后15分钟自动过期
3. **幂等性**：相同订单号多次支付会返回成功（避免重复扣款）
4. **扩展信息**：`extra_info` 字段用于存储特定业务数据，灵活扩展

---

## 🔄 版本兼容

### **向后兼容**

- 保留了旧版 Schema 的别名
- 旧的 API 仍然可用（建议逐步迁移）
- 数据迁移脚本确保旧数据可用

### **迁移建议**

1. **第一步**：执行数据迁移
2. **第二步**：更新前端调用（使用新接口）
3. **第三步**：删除旧字段（至少一周后）

---

**文档版本**: v1.0
**更新日期**: 2026-03-27
