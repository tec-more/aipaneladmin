"""
客户使用记录模型
"""

from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class UsageLog(BaseModel, TimestampMixin):
    """客户使用记录表"""

    customer = fields.ForeignKeyField(
        "models.Customer",
        related_name="usage_logs",
        on_delete=fields.CASCADE
    )
    session_id = fields.CharField(max_length=64, description="会话ID")
    duration_seconds = fields.IntField(description="使用时长(秒)")
    service_type = fields.CharField(max_length=50, default="translation", description="服务类型")
    details = fields.JSONField(default=dict, description="使用详情")
    characters_count = fields.IntField(default=0, description="字符数")
    api_cost = fields.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        description="API成本"
    )

    class Meta:
        table = "customer_usage_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Usage {self.session_id} - {self.duration_seconds}s"
