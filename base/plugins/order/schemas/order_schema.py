"""
订单数据验证模型
"""
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

from pydantic import BaseModel, Field


# ====== 基础模型 ======
class OrderBase(BaseModel):
    """订单基础模型"""
    customer_id: int = Field(..., description="客户ID")
    product_id: int = Field(..., description="产品ID")
    quantity: int = Field(default=1, ge=1, description="购买数量")
    remark: Optional[str] = Field(None, description="订单备注")


# ====== 请求模型 ======
class OrderCreate(OrderBase):
    """创建订单请求模型"""
    pass


class OrderUpdate(BaseModel):
    """更新订单请求模型"""
    payment_status: Optional[int] = Field(None, description="支付状态: 0-待支付, 1-已支付, 2-支付失败, 3-已退款")
    order_status: Optional[int] = Field(None, description="订单状态: 0-待支付, 1-已支付, 2-已完成, 3-已取消")
    remark: Optional[str] = Field(None, description="订单备注")


class PaymentUpdate(BaseModel):
    """更新支付状态请求模型"""
    order_id: int = Field(..., description="订单ID")
    payment_status: int = Field(..., description="支付状态: 0-待支付, 1-已支付, 2-支付失败, 3-已退款")
    payment_method: Optional[str] = Field(None, description="支付方式")
    transaction_id: Optional[str] = Field(None, description="支付平台交易ID")


# ====== 响应模型 ======
class OrderItem(BaseModel):
    """订单项响应模型"""
    id: int
    order_no: str
    customer_id: int
    product_id: int
    product_name: Optional[str] = None
    product_type: str
    product_value: Optional[int] = None
    membership_duration: Optional[int] = None
    quantity: int
    unit_price: Decimal
    total_amount: Decimal
    payment_status: int
    order_status: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: float
        }


class OrderResponse(OrderItem):
    """订单详情响应模型"""
    payment_method: Optional[str] = None
    payment_time: Optional[datetime] = None
    transaction_id: Optional[str] = None
    remark: Optional[str] = None
    updated_at: datetime


class OrderListResponse(BaseModel):
    """订单列表响应模型"""
    total: int
    items: List[OrderItem]


class OrderCreateResponse(BaseModel):
    """创建订单响应模型"""
    order_id: int
    order_no: str
    message: str = "订单创建成功"