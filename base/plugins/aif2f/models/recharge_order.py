"""
充值订单模型
"""

from enum import Enum
from datetime import datetime, timedelta
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin
import random
import string


class PaymentMethod(str, Enum):
    """支付方式"""
    WECHAT = "wechat"    # 微信支付
    ALIPAY = "alipay"    # 支付宝
    BALANCE = "balance"  # 余额支付


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"      # 待支付
    PAID = "paid"           # 已支付
    CANCELLED = "cancelled"  # 已取消
    REFUNDED = "refunded"    # 已退款
    EXPIRED = "expired"      # 已过期


def generate_order_no() -> str:
    """生成订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"ORD{timestamp}{random_str}"


class RechargeOrder(BaseModel):
    """充值订单表"""

    order_no = fields.CharField(max_length=64, unique=True, description="订单号")
    user = fields.ForeignKeyField(
        "models.User",
        related_name="recharge_orders",
        on_delete="CASCADE"
    )
    membership_level = fields.ForeignKeyField(
        "models.MembershipLevel",
        related_name="orders",
        on_delete="RESTRICT"
    )
    amount = fields.DecimalField(max_digits=10, decimal_places=2, description="支付金额")
    hours = fields.IntField(description="购买小时数")
    bonus_hours = fields.IntField(default=0, description="赠送小时数")
    total_hours = fields.IntField(description="总小时数(购买+赠送)")
    payment_method = fields.CharEnumField(
        PaymentMethod,
        max_length=20,
        description="支付方式"
    )
    payment_status = fields.CharEnumField(
        OrderStatus,
        max_length=20,
        default=OrderStatus.PENDING,
        description="支付状态"
    )
    trade_no = fields.CharField(max_length=128, null=True, description="第三方交易号")
    pay_time = fields.DatetimeField(null=True, description="支付时间")
    expire_time = fields.DatetimeField(description="订单过期时间")
    client_ip = fields.CharField(max_length=50, null=True, description="客户端IP")
    device_info = fields.JSONField(null=True, description="设备信息")
    remark = fields.TextField(null=True, description="备注")

    class Meta:
        table = "aif2f_recharge_order"
        ordering = ["-created_at"]

    @classmethod
    def create_order(cls, user_id: int, membership_level_id: int,
                     payment_method: str, client_ip: str = None):
        """创建订单"""
        from .membership import MembershipLevel

        # 获取会员等级信息
        level = MembershipLevel.get(id=membership_level_id)

        # 计算总小时数
        total_hours = level.duration_hours + level.bonus_hours

        # 订单过期时间(15分钟)
        expire_time = datetime.now() + timedelta(minutes=15)

        return cls(
            order_no=generate_order_no(),
            user_id=user_id,
            membership_level_id=membership_level_id,
            amount=level.price,
            hours=level.duration_hours,
            bonus_hours=level.bonus_hours,
            total_hours=total_hours,
            payment_method=payment_method,
            expire_time=expire_time,
            client_ip=client_ip
        )

    @property
    def is_expired(self) -> bool:
        """订单是否已过期"""
        return datetime.now() > self.expire_time and self.payment_status == OrderStatus.PENDING

    @property
    def is_paid(self) -> bool:
        """订单是否已支付"""
        return self.payment_status == OrderStatus.PAID

    def __str__(self):
        return f"Order {self.order_no} - {self.payment_status}"
