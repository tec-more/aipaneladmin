"""
使用统计模型
"""
from tortoise import fields
from decimal import Decimal
from base.common.model import BaseModel, TimestampMixin


class LLMUsage(BaseModel, TimestampMixin):
    """使用统计表"""

    conversation = fields.ForeignKeyField(
        "models.LLMConversation",
        related_name="usages",
        on_delete=fields.CASCADE
    )
    model = fields.ForeignKeyField(
        "models.LLMModel",
        related_name="usages",
        on_delete=fields.SET_NULL,
        null=True
    )
    customer_id = fields.IntField(description="客户ID")
    prompt_tokens = fields.IntField(default=0, description="提示词Token数")
    completion_tokens = fields.IntField(default=0, description="完成Token数")
    total_tokens = fields.IntField(default=0, description="总Token数")
    cost = fields.DecimalField(max_digits=10, decimal_places=4, default=0, description="成本")

    class Meta:
        table = "llm_usage"

    def __str__(self):
        return f"Usage {self.id} - {self.total_tokens} tokens"
