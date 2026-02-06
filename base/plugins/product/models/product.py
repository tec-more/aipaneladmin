"""
产品数据模型
"""
try:
    from tortoise import fields
    from tortoise.models import Model
    from base.common.model import BaseModel, TimestampMixin
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
        def TextField(**kwargs):
            return kwargs

        @staticmethod
        def JSONField(**kwargs):
            return kwargs

        @staticmethod
        def FloatField(**kwargs):
            return kwargs


class Product(BaseModel, TimestampMixin):
    """产品模型"""
    name = fields.CharField(max_length=255, unique=True, description="产品名称", index=True)
    description = fields.TextField(null=True, description="产品描述")
    original_price = fields.DecimalField(max_digits=10, decimal_places=2, description="原价")
    sale_price = fields.DecimalField(max_digits=10, decimal_places=2, null=True, description="优惠价")
    stock = fields.IntField(default=0, description="库存数量")
    category = fields.CharField(max_length=50, null=True, description="产品分类", index=True)
    tags = fields.JSONField(null=True, description="产品标签")
    images = fields.JSONField(null=True, description="产品图片")
    is_active = fields.BooleanField(default=True, description="是否上架", index=True)
    is_hot = fields.BooleanField(default=False, description="是否热门", index=True)
    is_new = fields.BooleanField(default=False, description="是否新品", index=True)
    view_count = fields.IntField(default=0, description="浏览次数", index=True)
    sales_count = fields.IntField(default=0, description="销售数量", index=True)
    # 充值相关字段
    recharge_hours = fields.IntField(null=True, description="充值时长（小时）")
    bonus_hours = fields.IntField(default=0, description="赠送时长（小时）")
    discount_description = fields.CharField(max_length=255, null=True, description="优惠描述")

    class Meta:
        table = "product"

    @property
    def current_price(self):
        """获取当前价格（有优惠价返回优惠价，否则返回原价）"""
        return float(self.sale_price) if self.sale_price else float(self.original_price)

    @property
    def has_discount(self) -> bool:
        """判断是否有优惠"""
        return self.sale_price is not None and float(self.sale_price) < float(self.original_price)

    @property
    def discount_percentage(self) -> int:
        """计算折扣百分比"""
        if not self.has_discount:
            return 0
        original = float(self.original_price)
        sale = float(self.sale_price)
        return int((original - sale) / original * 100)

    @property
    def total_hours(self) -> int:
        """获取总时长（充值时长 + 赠送时长）"""
        recharge = self.recharge_hours or 0
        bonus = self.bonus_hours or 0
        return recharge + bonus

    async def to_dict(self):
        """转换为字典"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "original_price": float(self.original_price) if hasattr(self.original_price, "__float__") else self.original_price,
            "sale_price": float(self.sale_price) if self.sale_price and hasattr(self.sale_price, "__float__") else self.sale_price,
            "current_price": self.current_price,
            "has_discount": self.has_discount,
            "discount_percentage": self.discount_percentage,
            "stock": self.stock,
            "category": self.category,
            "tags": self.tags,
            "images": self.images,
            "is_active": self.is_active,
            "is_hot": self.is_hot,
            "is_new": self.is_new,
            "view_count": self.view_count,
            "sales_count": self.sales_count,
            "recharge_hours": self.recharge_hours,
            "bonus_hours": self.bonus_hours,
            "total_hours": self.total_hours,
            "discount_description": self.discount_description,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
        return data