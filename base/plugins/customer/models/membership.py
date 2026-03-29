"""
会员等级模型
"""

from enum import Enum
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class LevelType(str, Enum):
    """会员等级类型"""
    TRIAL = "trial"              # 体验会员
    MONTHLY = "monthly"          # 月度会员
    QUARTERLY = "quarterly"      # 季度会员
    HALF_YEARLY = "half_yearly"  # 半年会员
    YEARLY = "yearly"            # 年度会员
    LIFETIME = "lifetime"        # 终身会员
    FIBONACCI = "fibonacci"      # Fibonacci动态等级


class MembershipLevel(BaseModel, TimestampMixin):
    """会员等级配置表"""

    level_type = fields.CharEnumField(
        LevelType,
        max_length=20,
        description="等级类型"
    )
    level = fields.IntField(description="等级数字(用于Fibonacci系统)")
    name = fields.CharField(max_length=50, description="等级名称")
    description = fields.TextField(null=True, description="等级描述")
    duration_days = fields.IntField(description="有效期天数")
    duration_hours = fields.IntField(default=0, description="有效期小时数")
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="价格")
    original_price = fields.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        description="原价"
    )
    bonus_hours = fields.IntField(default=0, description="赠送小时数")
    discount_percentage = fields.IntField(default=0, description="折扣百分比(0-100)")
    features = fields.JSONField(default=list, description="特权列表")
    sort_order = fields.IntField(default=0, description="排序")
    is_active = fields.BooleanField(default=True, description="是否启用")

    class Meta:
        table = "customer_membership_level"
        ordering = ["sort_order", "level"]

    def __str__(self):
        return f"{self.name} (Level {self.level})"
