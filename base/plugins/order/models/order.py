"""
订单数据模型
"""
try:
    from tortoise import fields
    from tortoise.models import Model
    from base.common.model import BaseModel, TimestampMixin
    from base.plugins.customer.models.customer import Customer
    from base.plugins.product.models.product import Product
except ImportError:
    # 定义临时依赖，以便在没有base模块的情况下也能工作
    from typing import Optional, Any
    from datetime import datetime

    class BaseModel:
        id = None

    class TimestampMixin:
        created_at = None
        updated_at = None

    class fields:
        @staticmethod
        def CharField(**kwargs):
            return kwargs

        @staticmethod
        def BooleanField(**kwargs):
            return kwargs

        @staticmethod
        def IntField(**kwargs):
            return kwargs

        @staticmethod
        def DatetimeField(**kwargs):
            return kwargs

        @staticmethod
        def DecimalField(**kwargs):
            return kwargs

        @staticmethod
        def ForeignKeyField(**kwargs):
            return kwargs

        @staticmethod
        def TextField(**kwargs):
            return kwargs

        @staticmethod
        def JSONField(**kwargs):
            return kwargs


class Order(BaseModel, TimestampMixin):
    """订单模型"""
    # 订单基本信息
    order_no = fields.CharField(max_length=32, unique=True, description="订单编号", index=True)
    customer_id = fields.ForeignKeyField('models.Customer', related_name='orders', description="客户ID")
    total_amount = fields.DecimalField(max_digits=10, decimal_places=2, description="订单总金额")
    
    # 支付信息
    payment_status = fields.IntField(default=0, description="支付状态: 0-待支付, 1-已支付, 2-支付失败, 3-已退款")
    payment_method = fields.CharField(max_length=20, null=True, description="支付方式")
    payment_time = fields.DatetimeField(null=True, description="支付时间")
    transaction_id = fields.CharField(max_length=100, null=True, description="支付平台交易ID")
    
    # 订单状态
    order_status = fields.IntField(default=0, description="订单状态: 0-待支付, 1-已支付, 2-已完成, 3-已取消")
    
    # 订单商品信息
    product_id = fields.ForeignKeyField('models.Product', related_name='orders', description="产品ID")
    quantity = fields.IntField(default=1, description="购买数量")
    unit_price = fields.DecimalField(max_digits=10, decimal_places=2, description="商品单价")
    
    # 虚拟产品相关信息
    product_type = fields.CharField(max_length=20, description="产品类型: point-点卷, membership-会员")
    product_value = fields.IntField(null=True, description="产品值(如点卷数量)")
    membership_duration = fields.IntField(null=True, description="会员时长(天)")
    
    # 其他信息
    remark = fields.TextField(null=True, description="订单备注")

    class Meta:
        table = "order"

    async def to_dict(self):
        """转换为字典"""
        data = {
            "id": self.id,
            "order_no": self.order_no,
            "customer_id": self.customer_id,
            "total_amount": float(self.total_amount) if hasattr(self.total_amount, "__float__") else self.total_amount,
            "payment_status": self.payment_status,
            "payment_method": self.payment_method,
            "payment_time": self.payment_time.strftime("%Y-%m-%d %H:%M:%S") if self.payment_time else None,
            "transaction_id": self.transaction_id,
            "order_status": self.order_status,
            "product_id": self.product_id,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price) if hasattr(self.unit_price, "__float__") else self.unit_price,
            "product_type": self.product_type,
            "product_value": self.product_value,
            "membership_duration": self.membership_duration,
            "remark": self.remark,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
        return data