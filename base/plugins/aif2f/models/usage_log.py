"""
使用记录模型
"""

from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class UsageLog(BaseModel):
    """翻译使用记录表"""

    user = fields.ForeignKeyField(
        "models.User",
        related_name="aif2f_usage_logs",
        on_delete="CASCADE"
    )
    session_id = fields.CharField(max_length=64, description="会话ID")
    duration_seconds = fields.IntField(description="使用时长(秒)")
    source_text = fields.TextField(description="原文")
    translated_text = fields.TextField(description="译文")
    source_lang = fields.CharField(max_length=10, description="源语言")
    target_lang = fields.CharField(max_length=10, description="目标语言")
    characters_count = fields.IntField(description="字符数")
    api_cost = fields.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        description="API成本"
    )
    asr_provider = fields.CharField(max_length=20, null=True, description="ASR服务商")
    translation_provider = fields.CharField(
        max_length=20,
        null=True,
        description="翻译服务商"
    )

    class Meta:
        table = "aif2f_usage_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Usage {self.session_id} - {self.duration_seconds}s"
