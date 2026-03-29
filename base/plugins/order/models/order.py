"""
订单模型 - 订单主表 + 订单明细表设计
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
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
    """
    订单主表
    存储订单的基本信息和支付状态
    """

    # ========== 基础信息 ==========
    order_no = fields.CharField(max_length=64, unique=True, description="订单号")
    customer = fields.ForeignKeyField(
        "models.Customer",
        related_name="orders",
        on_delete=fields.CASCADE,
        description="客户"
    )

    # ========== 金额信息 ==========
    total_amount = fields.DecimalField(max_digits=10, decimal_places=2, description="订单总金额")
    discount_amount = fields.DecimalField(max_digits=10, decimal_places=2, default=0, description="优惠金额")
    final_amount = fields.DecimalField(max_digits=10, decimal_places=2, description="实际支付金额")

    # ========== 支付信息 ==========
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

    # ========== 时间信息 ==========
    expire_time = fields.DatetimeField(description="订单过期时间")

    # ========== 旧字段（保留用于向后兼容，设为可选） ==========
    # 这些字段是旧的 customer_order 表的遗留字段
    # 新架构中，会员信息存储在 order_items.extra_info 中
    membership_level_id = fields.BigIntField(null=True, description="会员等级ID（旧字段，已弃用）")
    hours = fields.IntField(null=True, description="购买小时数（旧字段，已弃用）")
    bonus_hours = fields.IntField(null=True, description="赠送小时数（旧字段，已弃用）")
    total_hours = fields.IntField(null=True, description="总小时数（旧字段，已弃用）")
    amount = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="原金额字段（旧字段，已弃用）")

    # ========== 其他信息 ==========
    client_ip = fields.CharField(max_length=50, null=True, description="客户端IP")
    device_info = fields.JSONField(null=True, description="设备信息")
    remark = fields.TextField(null=True, description="备注")

    class Meta:
        table = "orders"
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

    async def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        # 预加载关联数据
        await self.fetch_related('customer')

        # 获取订单明细
        items = await self.items.all()
        items_list = [await item.to_dict() for item in items]

        # 构建产品摘要信息
        product_summary = []
        for item in items_list:
            product_summary.append(f"{item['product_name']} x{item['quantity']}")

        # 查询实际的产品信息（如果有 product_id）
        product_details = []
        for item in items_list:
            product_detail = {
                "product_name": item['product_name'],
                "product_type": item['product_type'],
                "quantity": item['quantity'],
                "unit_price": item['unit_price'],
                "total_price": item['total_price']
            }
            # 如果有 product_id，尝试获取产品详细信息
            if item.get('product_id'):
                from base.plugins.product.models.product import Product
                product = await Product.get_or_none(id=item['product_id'])
                if product:
                    product_detail['product_description'] = product.description
                    # images 是 JSON 数组，取第一个图片或返回整个数组
                    if product.images and isinstance(product.images, list) and len(product.images) > 0:
                        product_detail['product_image'] = product.images[0]
                        product_detail['product_images'] = product.images
                    else:
                        product_detail['product_image'] = None
                        product_detail['product_images'] = []
            product_details.append(product_detail)

        data = {
            "id": self.id,
            "order_no": self.order_no,
            "customer_id": self.customer_id,
            "customer_name": str(self.customer) if self.customer else None,
            "total_amount": float(self.total_amount),
            "discount_amount": float(self.discount_amount),
            "final_amount": float(self.final_amount),
            "payment_method": self.payment_method.value if isinstance(self.payment_method, Enum) else self.payment_method,
            "payment_status": self.payment_status.value if isinstance(self.payment_status, Enum) else self.payment_status,
            "status": self.payment_status.value if isinstance(self.payment_status, Enum) else self.payment_status,
            "trade_no": self.trade_no,
            "pay_time": self.pay_time.strftime("%Y-%m-%d %H:%M:%S") if self.pay_time else None,
            "expire_time": self.expire_time.strftime("%Y-%m-%d %H:%M:%S") if self.expire_time else None,
            "client_ip": self.client_ip,
            "device_info": self.device_info,
            "remark": self.remark,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
            "items": items_list,  # 订单明细列表
            # 新增：产品摘要和详细信息
            "product_summary": product_summary,  # 产品摘要：["SVIP会员 x1", "积分充值 x2"]
            "product_details": product_details,  # 产品详细信息列表
            "item_count": len(items_list),  # 商品数量
            "first_product_name": items_list[0]['product_name'] if items_list else None,  # 第一个产品名称
            "first_product_image": items_list[0].get('product_image') if items_list else None,  # 第一个产品图片
        }
        return data

    def __str__(self):
        return f"Order {self.order_no} - {self.payment_status}"


class OrderItem(BaseModel, TimestampMixin):
    """
    订单明细表
    存储订单中的每个商品信息
    """

    # ========== 关联信息 ==========
    order = fields.ForeignKeyField(
        "models.CustomerOrder",
        related_name="items",
        on_delete=fields.CASCADE,
        description="订单"
    )
    product = fields.ForeignKeyField(
        "models.Product",
        related_name="order_items",
        on_delete=fields.SET_NULL,
        null=True,
        description="产品"
    )

    # ========== 产品信息（冗余字段，避免关联查询） ==========
    product_name = fields.CharField(max_length=255, description="产品名称")
    product_type = fields.CharField(max_length=50, description="产品类型：membership/points/item")
    product_image = fields.CharField(max_length=500, null=True, description="产品图片")

    # ========== 购买信息 ==========
    quantity = fields.IntField(default=1, description="购买数量")
    unit_price = fields.DecimalField(max_digits=10, decimal_places=2, description="单价")
    total_price = fields.DecimalField(max_digits=10, decimal_places=2, description="小计金额")

    # ========== 扩展信息（JSON格式，存储特定业务数据） ==========
    extra_info = fields.JSONField(null=True, description="扩展信息")
    """
    扩展信息示例：
    {
        "membership_level_id": 1,          # 会员等级ID
        "membership_level_name": "SVIP",   # 会员等级名称
        "hours": 100,                      # 购买小时数
        "bonus_hours": 20,                 # 赠送小时数
        "total_hours": 120,                # 总小时数
        "recharge_type": "monthly"         # 充值类型：monthly/yearly
    }
    """

    class Meta:
        table = "order_items"
        ordering = ["-created_at"]

    async def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "product_type": self.product_type,
            "product_image": self.product_image,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total_price": float(self.total_price),
            "extra_info": self.extra_info,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
        return data

    def __str__(self):
        return f"OrderItem {self.product_name} x {self.quantity}"

# ========== 向后兼容 ==========
# 注意：customer_order 表已重命名为 orders
# 如果需要访问旧表，请使用 orders 表
