"""
对话记录模型
"""
from tortoise import fields
from decimal import Decimal
from base.common.model import BaseModel, TimestampMixin


class LLMConversation(BaseModel, TimestampMixin):
    """对话记录表"""

    conversation_id = fields.CharField(max_length=100, unique=True, description="对话ID")
    customer_id = fields.IntField(description="客户ID")
    model = fields.ForeignKeyField(
        "models.LLMModel",
        related_name="conversations",
        on_delete=fields.SET_NULL,
        null=True
    )
    messages = fields.JSONField(default=list, description="对话历史")
    total_tokens = fields.IntField(default=0, description="总Token数")
    total_cost = fields.DecimalField(max_digits=10, decimal_places=4, default=0, description="总成本")
    status = fields.CharField(max_length=20, default="active", description="状态")

    class Meta:
        table = "llm_conversation"

    def __str__(self):
        return f"Conversation {self.conversation_id}"
