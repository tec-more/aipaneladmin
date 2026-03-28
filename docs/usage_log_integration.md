# 使用记录集成指南

## 概述

使用记录（UsageLog）用于记录客户对 AI 服务和 API 的调用情况，支持计费、统计和分析功能。

## 数据模型

```python
class UsageLog(BaseModel, TimestampMixin):
    customer = fields.ForeignKeyField("models.Customer", ...)
    session_id = fields.CharField(max_length=64)              # 会话ID
    duration_seconds = fields.IntField()                      # 使用时长(秒)
    service_type = fields.CharField(max_length=50)               # 服务类型
    details = fields.JSONField(default=dict)                     # 详细信息
    characters_count = fields.IntField(default=0)                 # 字符数
    api_cost = fields.DecimalField(max_digits=10, decimal_places=4) # API成本
```

## 服务类型说明

| service_type | 说明 | 示例 |
|--------------|------|------|
| `text_generation` | 文本生成 | GPT、Claude 等文本生成 API |
| `image_generation` | 图像生成 | DALL-E、Stable Diffusion |
| `tts` | 语音合成 | 文字转语音 API |
| `translation` | 翻译服务 | Google Translate、DeepL |
| `asr` | 语音识别 | Whisper、语音转文字 |

## 集成示例

### 1. 创建使用记录工具函数

创建 `base/common/usage_tracker.py`:

```python
from decimal import Decimal
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from base.plugins.customer.models.usage_log import UsageLog

class UsageTracker:
    """使用记录追踪器"""

    @staticmethod
    async def log_usage(
        customer_id: int,
        service_type: str,
        duration_seconds: int,
        api_cost: float,
        details: Dict[str, Any],
        characters_count: int = 0,
        session_id: Optional[str] = None
    ) -> UsageLog:
        """
        记录服务使用情况

        Args:
            customer_id: 客户ID
            service_type: 服务类型（text_generation/image_generation/tts 等）
            duration_seconds: 使用时长（秒）
            api_cost: API 成本
            details: 详细信息（JSON 格式）
            characters_count: 字符数（可选）
            session_id: 会话ID（可选，自动生成）

        Returns:
            创建的使用记录对象
        """
        # 生成会话ID（如果未提供）
        if not session_id:
            session_id = str(uuid.uuid4())[:32]

        # 创建使用记录
        log = await UsageLog.create(
            customer_id=customer_id,
            session_id=session_id,
            duration_seconds=duration_seconds,
            service_type=service_type,
            details=details,
            characters_count=characters_count,
            api_cost=Decimal(str(api_cost))
        )

        return log

    @staticmethod
    async def log_openai_usage(
        customer_id: int,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_seconds: int,
        details: Optional[Dict[str, Any]] = None
    ) -> UsageLog:
        """
        记录 OpenAI API 使用（便捷方法）

        Args:
            customer_id: 客户ID
            model: 模型名称（如 gpt-4, claude-3-opus）
            prompt_tokens: 提示 Token 数
            completion_tokens: 完成 Token 数
            duration_seconds: 请求时长
            details: 额外详细信息

        Returns:
            使用记录对象
        """
        # 计算成本（示例价格，需根据实际情况调整）
        price_per_1k_tokens = {
            "gpt-4": 0.03,
            "gpt-3.5-turbo": 0.001,
            "claude-3-opus": 0.015,
        }

        total_tokens = prompt_tokens + completion_tokens
        cost = (total_tokens / 1000) * price_per_1k_tokens.get(model, 0.001)

        # 构建详细信息
        log_details = details or {}
        log_details.update({
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        })

        return await UsageTracker.log_usage(
            customer_id=customer_id,
            service_type="text_generation",
            duration_seconds=duration_seconds,
            api_cost=cost,
            details=log_details,
            characters_count=total_tokens * 4  # 粗略估计：1 token ≈ 4 字符
        )
```

### 2. 在 API 服务中使用

**示例：文本生成服务**

```python
from base.common.usage_tracker import UsageTracker

class TextGenerationService:
    """文本生成服务"""

    async def generate_text(self, customer_id: int, prompt: str):
        # 1. 记录开始时间
        start_time = datetime.now()

        # 2. 调用 AI API（示例）
        response = await openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        # 3. 计算时长
        duration_seconds = int((datetime.now() - start_time).total_seconds())

        # 4. 记录使用
        await UsageTracker.log_openai_usage(
            customer_id=customer_id,
            model="gpt-4",
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            duration_seconds=duration_seconds,
            details={"prompt": prompt[:100]}  # 保存前100字符
        )

        return response
```

**示例：图像生成服务**

```python
class ImageGenerationService:
    """图像生成服务"""

    async def generate_image(self, customer_id: int, prompt: str):
        start_time = datetime.now()

        # 调用图像生成 API
        image_url = await dall_e_client.generate(prompt)

        # 计算时长和成本
        duration_seconds = int((datetime.now() - start_time).total_seconds())
        cost = 0.025  # DALL-E 3 固定价格

        # 记录使用
        await UsageTracker.log_usage(
            customer_id=customer_id,
            service_type="image_generation",
            duration_seconds=duration_seconds,
            api_cost=cost,
            details={
                "model": "dall-e-3",
                "image_size": "1024x1024",
                "prompt": prompt
            }
        )

        return image_url
```

### 3. 测试接口

**创建测试数据**:
```bash
curl -X POST "http://127.0.0.1:9998/api/v1/customer/usage-logs/test"
```

**查询使用记录**:
```bash
curl "http://127.0.0.1:9998/api/v1/customer/usage-logs?page=1&page_size=10"
```

## 实际应用场景

### 场景1：会员充值后赠送 AI 配额

```python
async def process_payment_callback(order_no: str, ...):
    """支付回调处理"""
    # 更新订单状态
    order = await OrderService.get_order_by_no(order_no)

    # 获取订单明细
    items = await OrderItem.filter(order_id=order.id)

    for item in items:
        if item.product_type == "ai_credits":
            # 解析扩展信息中的配额
            credits = item.extra_info.get("credits", 0)

            # 为客户创建使用记录预留（充值）
            # 实际使用时再扣除
            pass
```

### 场景2：实时扣费

```python
async def deduct_usage_hours(customer_id: int, hours: float):
    """扣除使用时长"""

    # 获取会员信息
    membership = await CustomerMembership.get_or_none(customer_id=customer_id)

    # 检查余额
    if membership.remaining_hours < hours:
        raise ValueError("余额不足")

    # 扣除
    membership.used_hours += hours
    membership.remaining_hours -= hours
    await membership.save()

    return True
```

## 使用建议

1. **在 API 入口记录**：每次调用付费 API 都记录
2. **批量导入**：可以从第三方平台导出使用记录后导入
3. **定时任务**：定期同步外部平台的使用数据
4. **实时监控**：结合 WebSocket 实时显示使用情况

## 注意事项

1. **性能考虑**：高频调用时考虑异步批量写入
2. **数据准确性**：API 成本计算要准确，避免计费错误
3. **隐私保护**：details 字段不要记录敏感信息
4. **存储优化**：定期归档历史数据，避免表过大
