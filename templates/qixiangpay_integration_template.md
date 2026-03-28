# 七相支付集成 - AI开发任务

> 使用本模板让AI生成符合项目框架规范的七相支付集成代码

---

## 📋 需求概述

**功能名称**: 七相聚合支付集成

**一句话描述**: 集成七相支付接口，支持支付宝和微信支付的扫码支付、H5支付

**业务背景**:
- 项目需要接入第三方聚合支付平台（七相支付）
- 支持PC端扫码支付和移动端H5支付
- 支付后通过异步通知和轮询查询两种方式确认支付状态
- 七相支付作为聚合支付平台，无需企业资质，适合个人开发者

**为什么选择七相支付**:
- ✅ 支持微信支付和支付宝（一个接口搞定）
- ✅ 无需企业资质（个人/个体户可申请）
- ✅ 自适应支付链接（PC扫码/手机H5自动识别）
- ✅ 简单的MD5签名（易于集成）
- ✅ D+1结算到银行卡（资金安全）

**用户场景**:
```
1. 用户在平台购买会员套餐
2. 系统调用七相支付统一下单接口
3. PC端显示支付二维码，移动端唤起支付
4. 用户完成支付
5. 七相支付异步通知或前端轮询确认支付成功
6. 系统更新订单状态，用户获得会员权限
```

---

## 📚 参考文档

### 官方文档
- 文档地址：https://www.qixiangpay.cn/doc_old.html
- 测试账号：PID=1003, KEY=联系客服

### 核心接口信息

#### 1️⃣ 统一下单接口（主要使用）

**接口地址**: `https://api.payqixiang.cn/mapi.php`
**请求方式**: `POST`
**数据格式**: `application/x-www-form-urlencoded`
**返回格式**: `JSON`

**请求参数**:
| 字段名 | 变量名 | 必填 | 类型 | 示例值 | 说明 |
|--------|--------|------|------|--------|------|
| 商户ID | pid | 是 | Int | 1001 | 商户ID |
| 支付方式 | type | 是 | String | alipay | alipay:支付宝, wxpay:微信支付 |
| 商户订单号 | out_trade_no | 是 | String | 20160806151343349 | 商户系统内部订单号 |
| 异步通知地址 | notify_url | 是 | String | http://xxx.com/notify | 服务器异步通知地址 |
| 跳转通知地址 | return_url | 是 | String | http://xxx.com/return | 页面跳转通知地址 |
| 商品名称 | name | 是 | String | VIP会员 | 商品描述 |
| 商品金额 | money | 是 | String | 1.00 | 单位：元，最大2位小数 |
| 用户IP | clientip | 是 | String | 192.168.1.100 | 可随意传入 |
| 设备类型 | device | 是 | String | jump | 必须传jump才能返回支付链接 |
| 业务扩展参数 | param | 否 | String | | 支付后原样返回 |
| 签名字符串 | sign | 是 | String | | MD5签名 |
| 签名类型 | sign_type | 是 | String | MD5 | 固定值MD5 |

**响应参数**:
```json
{
  "code": 1,           // 1为成功，其它为失败
  "msg": "",
  "trade_no": "20160806151343349021",  // 七相订单号
  "payurl": "https://api.payqixiang.cn/pay/submit/xxx/",  // 支付跳转URL
  "qrcode": "weixin://wxpay/bizpayurl?pr=xxx"  // 二维码链接（可选）
}
```

**说明**:
- payurl是自适应页面，PC端打开显示二维码，手机端打开唤起支付
- 如果返回qrcode字段，可直接生成二维码

---

#### 2️⃣ 支付结果通知

**通知方式**:
1. **异步通知（notify_url）**: 服务器POST通知，需返回"success"
2. **跳转通知（return_url）**: 页面GET跳转

**通知参数**:
| 字段名 | 变量名 | 类型 | 说明 |
|--------|--------|------|------|
| 商户ID | pid | Int | |
| 七相订单号 | trade_no | String | |
| 商户订单号 | out_trade_no | String | |
| 支付方式 | type | String | alipay/wxpay |
| 商品名称 | name | String | |
| 商品金额 | money | String | |
| 支付状态 | trade_status | String | TRADE_SUCCESS为成功 |
| 业务扩展参数 | param | String | |
| 签名字符串 | sign | String | |
| 签名类型 | sign_type | String | MD5 |

**重要**:
- 收到异步通知后，必须返回字符串"success"
- 注意trade_status是大写的TRADE_SUCCESS
- 回调参数如果没有name就不用参加签名

---

#### 3️⃣ 查询订单接口

**接口地址**: `https://api.payqixiang.cn/api.php?act=order&pid={pid}&key={key}&out_trade_no={订单号}`

**请求参数**:
| 字段名 | 变量名 | 必填 | 类型 | 说明 |
|--------|--------|------|------|------|
| 操作类型 | act | 是 | String | 固定值order |
| 商户ID | pid | 是 | Int | 商户ID |
| 商户密钥 | key | 是 | String | 商户密钥 |
| 商户订单号 | out_trade_no | 选择 | String | 二选一 |
| 系统订单号 | trade_no | 选择 | String | 二选一，优先 |

**响应参数**:
```json
{
  "code": 1,
  "msg": "查询订单号成功！",
  "trade_no": "2016080622555342651",
  "out_trade_no": "20160806151343349",
  "api_trade_no": "第三方订单号",
  "type": "alipay",
  "pid": 1001,
  "addtime": "2016-08-06 22:55:52",
  "endtime": "2016-08-06 22:55:52",
  "name": "VIP会员",
  "money": "1.00",
  "status": 1,  // 1为支付成功，0为未支付
  "param": "",
  "buyer": ""
}
```

---

### 签名算法（MD5）

```
1. 将所有参数按ASCII码从小到大排序（a-z）
2. sign、sign_type和空值不参与签名
3. 拼接成键值对格式：a=b&c=d&e=f
4. 与商户密钥KEY拼接：a=b&c=d&e=f + KEY
5. MD5加密得出sign（小写）
```

**示例**:
```python
# 排序后
money=1.00&name=VIP会员&out_trade_no=20160806151343349&...
# 拼接KEY
money=1.00&name=VIP会员&out_trade_no=20160806151343349&...YOUR_KEY
# MD5加密
sign = md5("money=1.00&name=VIP会员&out_trade_no=20160806151343349&...YOUR_KEY")
```

---

## 🎯 开发要求

### 需要实现的接口

#### 1. 创建支付订单
- **路径**: `POST /v1/qixiang/create`
- **功能**: 调用七相统一下单接口，创建支付订单
- **输入**:
  - order_no: 商户订单号（必填）
  - pay_type: 支付类型 alipay/wxpay（必填）
  - amount: 金额（必填）
  - subject: 商品名称（必填）
- **输出**:
  - payurl: 支付跳转URL
  - qrcode: 二维码链接（如有）
  - trade_no: 七相订单号

#### 2. 查询支付状态
- **路径**: `GET /v1/qixiang/query/{order_no}`
- **功能**: 查询订单支付状态（用于前端轮询）
- **输入**: order_no
- **输出**:
  - status: pending/success/failed
  - trade_no: 七相订单号
  - amount: 金额

#### 3. 支付异步回调
- **路径**: `POST /v1/qixiang/notify`
- **功能**: 接收七相支付异步通知，验证签名，更新订单状态
- **输入**: 七相支付回调的所有参数
- **输出**: 字符串"success"

---

## 🏗️ 项目技术栈

- **框架**: FastAPI
- **ORM**: Tortoise-ORM
- **数据库**: MySQL
- **配置管理**: configparser (config.ini)
- **响应格式**: 统一使用 `SuccessResponse`

---

## 📁 项目结构要求

### 插件目录结构
```
base/plugins/qixiang_pay/
├── manifest.json          # 插件配置文件
├── models/                # 数据模型（如需要）
│   └── qixiang_pay.py
├── schemas/               # Pydantic Schema
│   └── qixiang_schema.py
├── services/              # 业务逻辑层
│   └── qixiang_service.py
└── api/v1/                # API路由
    └── qixiang_pay.py
```

### manifest.json 配置
```json
{
  "name": "qixiang_pay",
  "display_name": "七相支付",
  "version": "1.0.0",
  "description": "七相聚合支付接口集成（支持微信支付、支付宝）",
  "route_prefix": "/v1/qixiang",
  "routes": ["api/v1"],
  "dependencies": ["customer", "order"],
  "is_installed": true,
  "is_enabled": true
}
```

**说明**:
- 七相支付已包含微信支付和支付宝，无需额外依赖wechat_pay或alipay插件
- customer依赖：用于获取客户信息、更新会员状态
- order依赖：用于创建和更新订单记录

---

## 🔧 配置管理

### config.conf 配置项
```conf
[qixiang_pay]
pid = 1003
key = YOUR_KEY_HERE
api_url = https://api.payqixiang.cn/mapi.php
query_url = https://api.payqixiang.cn/api.php
notify_url = http://yourdomain.com/v1/qixiang/notify
return_url = http://yourdomain.com/payment/result
```

### 读取配置示例
```python
from base.common.config import config

def get_qixiang_config():
    return {
        "pid": config.get("qixiang_pay", "pid", fallback=""),
        "key": config.get("qixiang_pay", "key", fallback=""),
        "api_url": config.get("qixiang_pay", "api_url", fallback=""),
        "query_url": config.get("qixiang_pay", "query_url", fallback=""),
        "notify_url": config.get("qixiang_pay", "notify_url", fallback=""),
        "return_url": config.get("qixiang_pay", "return_url", fallback="")
    }
```

---

## 📖 参考代码

### 请参考以下文件的代码风格

#### 1. 订单插件（推荐参考）
```
base/plugins/order/api/v1/order.py
```
**参考要点**:
- 路由定义和装饰器使用
- 配置读取方式
- SuccessResponse统一响应格式
- Service层封装模式

#### 2. Schema定义
```
base/plugins/order/schemas/order_schema.py
```
**参考要点**:
- Pydantic BaseModel定义
- Field验证器的使用
- Optional类型的使用
- 请求/响应模型设计

#### 3. 支付服务
```
base/plugins/customer/services/payment_service.py
```
**参考要点**:
- 支付回调处理逻辑
- 订单状态更新
- 错误日志记录
- 异步回调处理

#### 4. 通用代码风格示例
```python
# 路由定义
from fastapi import APIRouter, HTTPException
from base.common.response import SuccessResponse

router = APIRouter(prefix="/v1/qixiang", tags=["七相支付"])

@router.post("/create")
async def create_order(order_data: CreateOrderIn):
    """创建七相支付订单"""
    try:
        service = QixiangPayService()
        result = await service.create_order(order_data.model_dump())
        return SuccessResponse(data=result, msg="创建订单成功")
    except Exception as e:
        logger.error(f"创建订单失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**说明**:
- 七相支付是独立的聚合支付插件
- 已包含微信支付和支付宝功能
- 代码风格参考订单模块而非特定支付插件

---

## ✅ AI任务清单

请按以下步骤执行：

### Step 1: 信息提取 📊
从参考文档中提取：
- [ ] 统一下单接口的所有参数（名称、类型、必填）
- [ ] 支付通知的所有回调参数
- [ ] 查询订单接口的参数和响应
- [ ] MD5签名算法的详细步骤
- [ ] 错误码和异常情况
- [ ] 支付状态映射（status字段含义）

### Step 2: 设计数据结构 📐
设计以下内容：
- [ ] 请求Schema（CreateOrderIn, QueryOrderIn）
- [ ] 响应Schema（CreateOrderOut, QueryOrderOut）
- [ ] Service层接口（QixiangPayService类）
- [ ] 辅助函数（签名生成、签名验证）

### Step 3: 实现代码 💻
实现以下模块：

#### 3.1 Schema定义 (schemas/qixiang_schema.py)
```python
from pydantic import BaseModel, Field
from typing import Optional

class CreateOrderIn(BaseModel):
    """创建支付订单请求"""
    order_no: str = Field(..., description="商户订单号")
    pay_type: str = Field(..., description="支付类型: alipay/wxpay")
    amount: float = Field(..., gt=0, description="支付金额")
    subject: str = Field(..., description="商品名称")
    client_ip: Optional[str] = Field("127.0.0.1", description="客户端IP")

class CreateOrderOut(BaseModel):
    """创建支付订单响应"""
    trade_no: str  # 七相订单号
    payurl: str    # 支付跳转URL
    qrcode: Optional[str]  # 二维码链接

class QueryOrderOut(BaseModel):
    """查询订单响应"""
    order_no: str
    trade_no: str
    status: str  # pending/success/failed
    amount: float
```

#### 3.2 Service层 (services/qixiang_service.py)
```python
import hashlib
import logging
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)

class QixiangPayService:
    """七相支付服务"""

    @staticmethod
    def generate_sign(params: Dict[str, Any], key: str) -> str:
        """
        生成MD5签名

        Args:
            params: 请求参数字典
            key: 商户密钥

        Returns:
            MD5签名字符串（小写）
        """
        # TODO: 实现签名逻辑
        pass

    @staticmethod
    def verify_sign(params: Dict[str, Any], key: str, sign: str) -> bool:
        """
        验证签名

        Args:
            params: 回调参数字典
            key: 商户密钥
            sign: 待验证的签名

        Returns:
            验证结果
        """
        # TODO: 实现验签逻辑
        pass

    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建支付订单

        Args:
            order_data: 订单数据

        Returns:
            包含payurl和qrcode的字典
        """
        # TODO: 调用七相统一下单接口
        pass

    async def query_order(self, order_no: str) -> Dict[str, Any]:
        """
        查询订单状态

        Args:
            order_no: 商户订单号

        Returns:
            订单状态信息
        """
        # TODO: 调用七相查询接口
        pass

    async def process_notify(self, notify_data: Dict[str, Any]) -> bool:
        """
        处理支付异步通知

        Args:
            notify_data: 回调数据

        Returns:
            处理是否成功
        """
        # TODO: 验证签名并更新订单状态
        pass
```

#### 3.3 API路由 (api/v1/qixiang_pay.py)
```python
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from typing import Dict, Any

from base.common.response import SuccessResponse
from base.plugins.qixiang_pay.schemas.qixiang_schema import CreateOrderIn
from base.plugins.qixiang_pay.services.qixiang_service import QixiangPayService

router = APIRouter(prefix="/v1/qixiang", tags=["七相支付"])

@router.post("/create")
async def create_order(order_data: CreateOrderIn):
    """创建七相支付订单"""
    try:
        service = QixiangPayService()
        result = await service.create_order(order_data.model_dump())
        return SuccessResponse(data=result, msg="创建订单成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/query/{order_no}")
async def query_order(order_no: str):
    """查询七相支付订单"""
    try:
        service = QixiangPayService()
        result = await service.query_order(order_no)
        return SuccessResponse(data=result, msg="查询成功")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notify")
async def payment_notify(request: Request):
    """七相支付异步回调"""
    try:
        # 获取回调数据
        notify_data = dict(await request.form())
        # 或如果是JSON: notify_data = await request.json()

        service = QixiangPayService()
        success = await service.process_notify(notify_data)

        if success:
            # 必须返回字符串"success"
            return PlainTextResponse(content="success")
        else:
            return PlainTextResponse(content="fail", status_code=400)

    except Exception as e:
        logger.error(f"处理七相支付回调异常: {str(e)}", exc_info=True)
        return PlainTextResponse(content="fail", status_code=500)
```

### Step 4: 提供示例 📝
提供以下使用示例：
- [ ] 配置文件示例（config.ini）
- [ ] API调用示例（curl命令）
- [ ] Python调用示例
- [ ] 测试数据示例

### Step 5: 质量检查 🔍
使用以下清单检查代码：

#### 代码质量
- [ ] 所有函数都有详细的中文文档字符串
- [ ] 所有异常都正确处理
- [ ] 日志记录完整（使用logging模块）
- [ ] 类型注解完整
- [ ] 敏感信息（KEY）不记录到日志

#### 功能完整性
- [ ] MD5签名生成正确
- [ ] MD5签名验证正确
- [ ] 参数排序按ASCII码
- [ ] 签名时不包含sign和sign_type
- [ ] 异步通知返回"success"字符串
- [ ] 查询订单正确映射status字段（1=success, 0=pending）

#### 错误处理
- [ ] 网络请求异常处理
- [ ] 七相支付返回错误的处理（code != 1）
- [ ] 签名验证失败的处理
- [ ] 订单不存在的处理

---

## ⚠️ 重要注意事项

### 0. 插件关系说明（重要）
- **七相支付是独立的聚合支付插件**
- 已内置支持微信支付和支付宝，无需额外依赖
- 与项目中的wechat_pay插件是**并列关系**，不是依赖关系
- 七相支付适合个人/小商户快速接入（无需企业资质）
- wechat_pay插件适合有企业资质的场景（官方直连）

**插件选择建议**:
- 个人开发者/小商户 → 使用七相支付
- 有企业资质的大商户 → 使用官方微信/支付宝SDK

### 1. 签名算法关键点
- 参数按ASCII码排序（使用sorted()）
- sign、sign_type和空值不参与签名
- 最终MD5结果为**小写**
- 拼接格式：`a=b&c=d&e=f + KEY`（注意+是拼接符）

### 2. 回调处理关键点
- 必须返回纯文本字符串`"success"`，不是JSON
- trade_status是大写的`TRADE_SUCCESS`才是成功
- 如果回调没有name参数，不参与签名验证
- status字段：1=支付成功，0=未支付

### 3. 设备类型参数
- 统一下单时device必须传`"jump"`才能返回支付链接
- 返回的payurl是自适应的（PC扫码/手机H5）

### 4. 金额格式
- 单位是**元**，不是分
- 最多2位小数
- 直接传递字符串或浮点数即可

### 5. 订单号
- out_trade_no是商户订单号（我们系统的订单号）
- trade_no是七相系统的订单号
- 两个都要记录到数据库

---

## 🚀 开始执行

请按照以下顺序输出结果：

### 输出1: 分析结果 📊
```markdown
## 📊 文档分析结果

### 提取的接口信息
- 统一下单接口参数：[列出所有参数]
- 查询订单接口参数：[列出所有参数]
- 支付回调参数：[列出所有参数]

### 签名算法分析
[详细说明MD5签名的实现步骤]

### 状态映射
- 七相status → 本系统status
- 1 → "success"
- 0 → "pending"
```

### 输出2: 数据结构设计 📐
```python
## Schema定义
[完整的Pydantic Schema代码]

## 辅助函数设计
[签名生成、签名验证函数]
```

### 输出3: 完整代码实现 💻
```python
## 1. Schema定义 (schemas/qixiang_schema.py)
[完整代码]

## 2. Service层 (services/qixiang_service.py)
[完整代码]

## 3. API路由 (api/v1/qixiang_pay.py)
[完整代码]

## 4. manifest.json
[完整配置]
```

### 输出4: 配置和使用示例 📝
```markdown
## 配置文件
[config.ini配置示例]

## API调用示例
### 创建订单
```bash
curl -X POST "http://localhost:8000/v1/qixiang/create" \
  -H "Content-Type: application/json" \
  -d '{
    "order_no": "20240327001",
    "pay_type": "alipay",
    "amount": 99.00,
    "subject": "VIP会员"
  }'
```

### 查询订单
```bash
curl -X GET "http://localhost:8000/v1/qixiang/query/20240327001"
```

## 测试数据
- 测试PID: 1003
- 测试订单号: 20240327001
- 测试金额: 0.01
```

---

## 📞 审查要点

生成代码后，请重点审查：

1. **签名算法是否正确**
   - 参数排序是否按ASCII码
   - 是否排除了sign和sign_type
   - MD5结果是否为小写

2. **回调处理是否正确**
   - 是否返回纯文本"success"
   - 是否验证了签名
   - 是否正确映射了支付状态

3. **错误处理是否完整**
   - 网络异常
   - 七相返回code!=1
   - 签名验证失败
   - 订单不存在

4. **日志记录是否合理**
   - 不记录敏感信息（KEY）
   - 记录关键操作（下单、查询、回调）
   - 记录异常信息

---

**模板版本**: v1.0
**创建日期**: 2026-03-27
**适用框架**: FastAPI + Tortoise-ORM + configparser
