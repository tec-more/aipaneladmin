"""
产品相关的Pydantic模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal


class ProductBase(BaseModel):
    """产品基础模型"""
    name: str = Field(..., min_length=1, max_length=255, description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    price: Decimal = Field(..., ge=Decimal("0.01"), max_digits=10, decimal_places=2, description="产品价格")
    stock: int = Field(default=0, ge=0, description="库存数量")
    category: Optional[str] = Field(None, max_length=50, description="产品分类")
    tags: Optional[List[str]] = Field(None, description="产品标签")
    images: Optional[List[str]] = Field(None, description="产品图片")
    is_active: bool = Field(default=True, description="是否上架")
    is_hot: bool = Field(default=False, description="是否热门")
    is_new: bool = Field(default=False, description="是否新品")


class ProductCreate(ProductBase):
    """创建产品模型"""
    pass


class ProductUpdate(BaseModel):
    """更新产品模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="产品名称")
    description: Optional[str] = Field(None, description="产品描述")
    price: Optional[Decimal] = Field(None, ge=Decimal("0.01"), max_digits=10, decimal_places=2, description="产品价格")
    stock: Optional[int] = Field(None, ge=0, description="库存数量")
    category: Optional[str] = Field(None, max_length=50, description="产品分类")
    tags: Optional[List[str]] = Field(None, description="产品标签")
    images: Optional[List[str]] = Field(None, description="产品图片")
    is_active: Optional[bool] = Field(None, description="是否上架")
    is_hot: Optional[bool] = Field(None, description="是否热门")
    is_new: Optional[bool] = Field(None, description="是否新品")


class ProductResponse(BaseModel):
    """产品响应模型"""
    id: int
    name: str
    description: Optional[str] = None
    price: Decimal
    stock: int
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    images: Optional[List[str]] = None
    is_active: bool
    is_hot: bool
    is_new: bool
    view_count: int
    sales_count: int
    created_at: datetime
    updated_at: datetime

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
