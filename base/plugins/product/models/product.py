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
    price = fields.DecimalField(max_digits=10, decimal_places=2, description="产品价格")
    stock = fields.IntField(default=0, description="库存数量")
    category = fields.CharField(max_length=50, null=True, description="产品分类", index=True)
    tags = fields.JSONField(null=True, description="产品标签")
    images = fields.JSONField(null=True, description="产品图片")
    is_active = fields.BooleanField(default=True, description="是否上架", index=True)
    is_hot = fields.BooleanField(default=False, description="是否热门", index=True)
    is_new = fields.BooleanField(default=False, description="是否新品", index=True)
    view_count = fields.IntField(default=0, description="浏览次数", index=True)
    sales_count = fields.IntField(default=0, description="销售数量", index=True)

    class Meta:
        table = "product"

    async def to_dict(self):
        """转换为字典"""
        data = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": float(self.price) if hasattr(self.price, "__float__") else self.price,
            "stock": self.stock,
            "category": self.category,
            "tags": self.tags,
            "images": self.images,
            "is_active": self.is_active,
            "is_hot": self.is_hot,
            "is_new": self.is_new,
            "view_count": self.view_count,
            "sales_count": self.sales_count,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
        return data