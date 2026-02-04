"""
客户会员关系模型
"""

from datetime import datetime
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class CustomerMembership(BaseModel, TimestampMixin):
    """客户会员信息表"""

    customer = fields.ForeignKeyField(
        "models.Customer",
        related_name="memberships",
        on_delete=fields.CASCADE
    )
    membership_level = fields.ForeignKeyField(
        "models.MembershipLevel",
        related_name="customers",
        on_delete=fields.RESTRICT,
        null=True
    )
    start_time = fields.DatetimeField(description="开始时间")
    expire_time = fields.DatetimeField(description="过期时间")
    total_hours = fields.IntField(default=0, description="总小时数")
    used_hours = fields.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        description="已使用小时数"
    )
    remaining_hours = fields.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        description="剩余小时数"
    )
    level = fields.IntField(default=0, description="Fibonacci等级")
    is_active = fields.BooleanField(default=True, description="是否激活")
    auto_renew = fields.BooleanField(default=False, description="是否自动续费")

    class Meta:
        table = "customer_membership"
        unique_together = (("customer", "is_active"),)

    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        return datetime.now() > self.expire_time if self.expire_time else True

    @property
    def is_vip(self) -> bool:
        """是否是VIP会员"""
        return self.is_active and not self.is_expired and self.remaining_hours > 0

    def __str__(self):
        return f"Customer {self.customer_id} - Level {self.level} - {self.remaining_hours}h remaining"
