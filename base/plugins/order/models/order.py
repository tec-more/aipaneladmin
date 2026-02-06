"""
订单模型
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
    PENDING = "pending"          # 待支付
    PROCESSING = "processing"    # 处理中
    PAID = "paid"               # 已支付
    COMPLETED = "completed"      # 已完成
    CANCELLED = "cancelled"      # 已取消
    FAILED = "failed"            # 支付失败
    REFUNDED = "refunded"        # 已退款
    EXPIRED = "expired"          # 已过期

    @classmethod
    def get_status_color(cls, status: str) -> str:
        """获取状态对应的颜色"""
        colors = {
            cls.PENDING.value: "warning",      # 橙色
            cls.PROCESSING.value: "info",      # 蓝色
            cls.PAID.value: "success",         # 绿色
            cls.COMPLETED.value: "success",    # 绿色
            cls.CANCELLED.value: "default",    # 灰色
            cls.FAILED.value: "danger",        # 红色
            cls.REFUNDED.value: "secondary",   # 次要色
            cls.EXPIRED.value: "default",      # 灰色
        }
        return colors.get(status, "default")

    @classmethod
    def get_status_label(cls, status: str) -> str:
        """获取状态的中文标签"""
        labels = {
            cls.PENDING.value: "待支付",
            cls.PROCESSING.value: "处理中",
            cls.PAID.value: "已支付",
            cls.COMPLETED.value: "已完成",
            cls.CANCELLED.value: "已取消",
            cls.FAILED.value: "支付失败",
            cls.REFUNDED.value: "已退款",
            cls.EXPIRED.value: "已过期",
        }
        return labels.get(status, "未知")


def generate_order_no() -> str:
    """生成订单号"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.digits, k=6))
    return f"ORD{timestamp}{random_str}"


class CustomerOrder(BaseModel, TimestampMixin):
    """客户充值订单表"""

    order_no = fields.CharField(max_length=64, unique=True, description="订单号")
    customer = fields.ForeignKeyField(
        "models.Customer",
        related_name="recharge_orders",
        on_delete=fields.CASCADE
    )
    membership_level = fields.ForeignKeyField(
        "models.MembershipLevel",
        related_name="orders",
        on_delete=fields.RESTRICT
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
        table = "customer_order"
        ordering = ["-created_at"]

    @property
    def is_expired(self) -> bool:
        """订单是否已过期"""
        return datetime.now() > self.expire_time and self.payment_status == OrderStatus.PENDING

    @property
    def is_paid(self) -> bool:
        """订单是否已支付"""
        return self.payment_status == OrderStatus.PAID

    @property
    def status_color(self) -> str:
        """获取状态颜色"""
        return OrderStatus.get_status_color(self.payment_status.value)

    @property
    def status_label(self) -> str:
        """获取状态中文标签"""
        return OrderStatus.get_status_label(self.payment_status.value)

    @property
    def total_hours(self) -> int:
        """获取总小时数"""
        return self.hours + self.bonus_hours

    def __str__(self):
        return f"Order {self.order_no} - {self.payment_status}"
