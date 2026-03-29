"""
产品相关的Pydantic模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, computed_field
from decimal import Decimal


class ProductBase(BaseModel):
    """产品基础模型"""
    name: str = Field(..., min_length=1, max_length=255, description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    price: Decimal = Field(..., ge=Decimal("0.01"), max_digits=10, decimal_places=2, description="销售价格")
    original_price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), max_digits=10, decimal_places=2, description="原价")
    stock: int = Field(default=0, ge=0, description="库存数量")
    sort: int = Field(default=0, ge=0, description="排序")
    category: Optional[str] = Field(None, max_length=50, description="产品分类")
    tags: Optional[List[str]] = Field(None, description="产品标签")
    images: Optional[List[str]] = Field(None, description="产品图片")
    is_active: bool = Field(default=True, description="是否上架")
    is_hot: bool = Field(default=False, description="是否热门")
    is_new: bool = Field(default=False, description="是否新品")
    recharge_hours: Optional[int] = Field(None, ge=0, description="充值时长（小时）")
    bonus_hours: int = Field(default=0, ge=0, description="赠送时长（小时）")
    discount_description: Optional[str] = Field(None, max_length=255, description="优惠描述")

    @field_validator('original_price')
    @classmethod
    def validate_original_price(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """验证原价必须大于销售价格"""
        if v is not None and 'price' in info.data:
            price = info.data['price']
            if v <= price:
                raise ValueError('原价必须大于销售价格')
        return v


class ProductCreate(ProductBase):
    """创建产品模型"""
    pass


class ProductUpdate(BaseModel):
    """更新产品模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), max_digits=10, decimal_places=2, description="销售价格")
    original_price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), max_digits=10, decimal_places=2, description="原价")
    stock: Optional[int] = Field(None, ge=0, description="库存数量")
    sort: Optional[int] = Field(None, ge=0, description="排序")
    category: Optional[str] = Field(None, max_length=50, description="产品分类")
    tags: Optional[List[str]] = Field(None, description="产品标签")
    images: Optional[List[str]] = Field(None, description="产品图片")
    is_active: Optional[bool] = Field(None, description="是否上架")
    is_hot: Optional[bool] = Field(None, description="是否热门")
    is_new: Optional[bool] = Field(None, description="是否新品")
    recharge_hours: Optional[int] = Field(None, ge=0, description="充值时长（小时）")
    bonus_hours: Optional[int] = Field(None, ge=0, description="赠送时长（小时）")
    discount_description: Optional[str] = Field(None, max_length=255, description="优惠描述")
    membership_level_id: Optional[int] = Field(None, description="关联的会员等级ID")

    model_config = {"populate_by_name": True}


class ProductResponse(BaseModel):
    """产品响应模型"""
    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    original_price: Optional[Decimal] = None
    stock: int
    sort: int
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    images: Optional[List[str]] = None
    is_active: bool
    is_hot: bool
    is_new: bool
    view_count: int
    sales_count: int
    recharge_hours: Optional[int] = None
    bonus_hours: int
    discount_description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # 计算字段
    @computed_field
    @property
    def current_price(self) -> Decimal:
        """当前价格（返回销售价格）"""
        return self.price

    @computed_field
    @property
    def has_discount(self) -> bool:
        """是否有优惠（有原价且原价大于销售价格）"""
        return self.original_price is not None and self.original_price > self.price

    @computed_field
    @property
    def discount_percentage(self) -> int:
        """折扣百分比"""
        if not self.has_discount:
            return 0
        return int((self.original_price - self.price) / self.original_price * 100)

    @computed_field
    @property
    def total_hours(self) -> int:
        """总时长（充值时长 + 赠送时长）"""
        recharge = self.recharge_hours or 0
        bonus = self.bonus_hours or 0
        return recharge + bonus

    class Config:
        from_attributes = True


class ProductListQuery(BaseModel):
    """产品列表查询参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量")
    name: Optional[str] = Field(None, description="产品名称(模糊搜索)")
    category: Optional[str] = Field(None, description="产品分类")
    is_active: Optional[bool] = Field(None, description="是否上架")
    is_hot: Optional[bool] = Field(None, description="是否热门")
    is_new: Optional[bool] = Field(None, description="是否新品")


class ProductListResponse(BaseModel):
    """产品列表响应模型"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页数量")
    items: List[ProductResponse] = Field(..., description="产品列表")


class ProductStockUpdate(BaseModel):
    """产品库存更新模型"""
    quantity: int = Field(..., description="库存变更数量（正数增加，负数减少）")

    @field_validator('quantity')
    @classmethod
    def validate_quantity(cls, v: int) -> int:
        # 允许负数，但需要在服务层检查库存是否足够
        return v


class ProductSalesUpdate(BaseModel):
    """产品销售数量更新模型"""
    quantity: int = Field(..., ge=1, description="销售数量增加量")


class CategoryListResponse(BaseModel):
    """分类列表响应模型"""
    categories: List[str] = Field(..., description="分类列表")
