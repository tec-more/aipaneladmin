"""
API密钥模型
"""
from tortoise import fields
from datetime import datetime, timedelta
from base.common.model import BaseModel, TimestampMixin


class LLMApiKey(BaseModel, TimestampMixin):
    """API密钥表"""

    provider = fields.ForeignKeyField(
        "models.LLMProvider",
        related_name="api_keys",
        on_delete=fields.CASCADE
    )
    name = fields.CharField(max_length=100, description="密钥名称")
    api_key = fields.CharField(max_length=255, description="加密后的API密钥")
    api_secret = fields.CharField(max_length=255, null=True, description="API密钥(某些厂商需要)")
    endpoint_url = fields.CharField(max_length=255, null=True, description="自定义端点URL")
    max_quota = fields.IntField(default=100000, description="每日配额限制(tokens/天)")
    used_quota = fields.IntField(default=0, description="已使用配额")
    quota_reset_date = fields.DateField(auto_now_add=False, default=None, description="配额重置日期")
    status = fields.CharField(max_length=20, default="active", description="状态")
    last_used_at = fields.DatetimeField(null=True, description="最后使用时间")
    expires_at = fields.DatetimeField(null=True, description="过期时间")
    description = fields.TextField(null=True, description="备注")

    class Meta:
        table = "llm_api_key"

    def __str__(self):
        return f"{self.provider.name} - {self.name}"

    @property
    def is_available(self) -> bool:
        """是否可用"""
        if self.status != "active":
            return False
        if self.expires_at and self.expires_at < datetime.now():
            return False
        if self.max_quota > 0 and self.used_quota >= self.max_quota:
            return False
        return True

    @property
    def remaining_quota(self) -> int:
        """剩余配额"""
        return max(0, self.max_quota - self.used_quota)

    async def reset_quota_if_needed(self):
        """如果需要，重置配额"""
        today = datetime.now().date()
        if self.quota_reset_date < today:
            self.used_quota = 0
            self.quota_reset_date = today
            await self.save()
