"""
API密钥模型
"""
from tortoise import fields
from datetime import datetime, timedelta
from base.common.model import BaseModel, TimestampMixin
from base.plugins.llm.models.enums import ModelServiceType


class LLMApiKey(BaseModel, TimestampMixin):
    """API密钥表"""

    provider = fields.ForeignKeyField(
        "models.LLMProvider",
        related_name="api_keys",
        on_delete=fields.CASCADE
    )

    # ========== 服务类型（新增） ==========
    model_service_type = fields.CharField(
        max_length=50,
        default=ModelServiceType.LLM.value,
        description="模型服务类型"
    )

    # ========== 统一的认证字段 ==========
    api_id = fields.CharField(max_length=255, null=True, description="API ID")
    api_key = fields.CharField(max_length=512, null=True, description="API Key")
    api_secret = fields.CharField(max_length=512, null=True, description="API Secret")
    access_token = fields.CharField(max_length=512, null=True, description="Access Token")
    endpoint_url = fields.CharField(max_length=512, null=True, description="自定义端点URL")

    # ========== 旧字段（保留用于向后兼容，标记为deprecated） ==========
    # TODO: 数据迁移完成后删除这些字段
    app_key = fields.CharField(max_length=512, null=True, description="[Deprecated] App Key (LLM) - 请使用api_key")
    api_id_voice = fields.CharField(max_length=100, null=True, description="[Deprecated] API ID (语音服务) - 已被model_service_type替代")
    app_key_voice = fields.CharField(max_length=255, null=True, description="[Deprecated] App Key (语音服务) - 已被model_service_type替代")
    api_secret_voice = fields.CharField(max_length=255, null=True, description="[Deprecated] API密钥-语音服务 - 已被model_service_type替代")
    endpoint_url_voice = fields.CharField(max_length=255, null=True, description="[Deprecated] 自定义端点URL (语音服务) - 已被model_service_type替代")

    # ========== 配额管理 ==========
    max_quota = fields.IntField(default=100000, description="每日配额限制(tokens/天)")
    used_quota = fields.IntField(default=0, description="已使用配额")
    quota_reset_date = fields.DateField(default=datetime.now().date, description="配额重置日期")

    # ========== 状态管理 ==========
    status = fields.CharField(max_length=20, default="active", description="状态")
    last_used_at = fields.DatetimeField(null=True, description="最后使用时间")
    expires_at = fields.DatetimeField(null=True, description="过期时间")

    # ========== 备注 ==========
    description = fields.TextField(null=True, description="备注")

    class Meta:
        table = "llm_api_key"

    def __str__(self):
        return f"{self.provider.name} - {self.api_id or self.model_service_type}"

    async def save(self, *args, **kwargs):
        """保存前自动设置 quota_reset_date"""
        if not self.quota_reset_date:
            self.quota_reset_date = datetime.now().date()
        await super().save(*args, **kwargs)

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

    @property
    def is_voice_service(self) -> bool:
        """
        是否为语音服务类型

        根据model_service_type判断，替代旧的has_voice_credentials
        """
        return self.model_service_type in [t.value for t in ModelServiceType.voice_services()]

    @property
    def has_voice_credentials(self) -> bool:
        """
        [Deprecated] 是否有语音服务密钥

        保留用于向后兼容，新代码请使用is_voice_service
        """
        # 如果已设置model_service_type，使用新逻辑
        if self.model_service_type != ModelServiceType.LLM.value:
            return True
        # 否则使用旧逻辑（检查是否有语音字段）
        return bool(
            self.api_id_voice or
            self.app_key_voice or
            self.api_secret_voice or
            self.endpoint_url_voice
        )

    def get_credentials(self) -> dict:
        """
        获取服务凭据（根据服务类型返回对应的字段）

        统一的凭据获取方法，替代get_llm_credentials和get_voice_credentials
        """
        # 优先使用新字段，如果为空则回退到旧字段（向后兼容）
        return {
            "api_id": self.api_id or self.api_id_voice,
            "api_key": self.api_key or self.app_key or self.app_key_voice,
            "api_secret": self.api_secret or self.api_secret_voice,
            "access_token": self.access_token,
            "endpoint_url": self.endpoint_url or self.endpoint_url_voice
        }

    def get_llm_credentials(self) -> dict:
        """
        [Deprecated] 获取LLM服务凭据

        保留用于向后兼容，新代码请使用get_credentials
        """
        return {
            "api_id": self.api_id,
            "app_key": self.app_key,
            "api_secret": self.api_secret,
            "endpoint_url": self.endpoint_url
        }

    def get_voice_credentials(self) -> dict:
        """
        [Deprecated] 获取语音服务凭据（智能回退到LLM密钥）

        保留用于向后兼容，新代码请使用get_credentials
        """
        return {
            "api_id": self.api_id_voice or self.api_id,
            "app_key": self.app_key_voice or self.app_key,
            "api_secret": self.api_secret_voice or self.api_secret,
            "endpoint_url": self.endpoint_url_voice or self.endpoint_url
        }
