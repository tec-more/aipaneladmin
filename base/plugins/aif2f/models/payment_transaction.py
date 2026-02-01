"""
支付交易记录模型
"""

from enum import Enum
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class TransactionStatus(str, Enum):
    """交易状态"""
    PENDING = "pending"      # 待处理
    SUCCESS = "success"      # 成功
    FAILED = "failed"        # 失败
    REFUNDED = "refunded"    # 已退款


class PaymentTransaction(BaseModel):
    """支付交易记录表"""

    order = fields.ForeignKeyField(
        "models.RechargeOrder",
        related_name="transactions",
        on_delete="CASCADE"
    )
    transaction_id = fields.CharField(max_length=128, unique=True, description="交易ID")
    transaction_type = fields.CharField(max_length=20, description="交易类型(wechat/alipay)")
    amount = fields.DecimalField(max_digits=10, decimal_places=2, description="交易金额")
    status = fields.CharEnumField(
        TransactionStatus,
        max_length=20,
        default=TransactionStatus.PENDING,
        description="交易状态"
    )
    notify_data = fields.JSONField(description="回调通知数据")
    processed_at = fields.DatetimeField(auto_now_add=True, description="处理时间")

    class Meta:
        table = "aif2f_payment_transaction"
        ordering = ["-processed_at"]

    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.status}"
