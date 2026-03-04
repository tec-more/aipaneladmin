"""
订单相关 Schema
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, computed_field
from decimal import Decimal


class CreateOrderIn(BaseModel):
    """创建订单输入"""
    customer_id: int = Field(..., description="客户ID")
    membership_level_id: int = Field(..., description="会员等级ID")
    payment_method: str = Field(..., description="支付方式(wechat/alipay)")
    client_ip: Optional[str] = None
    device_info: Optional[Dict[str, Any]] = None


class OrderOut(BaseModel):
    """订单输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    customer_id: int
    membership_level_id: int
    amount: Decimal
    hours: int
    bonus_hours: int
    payment_method: str
    payment_status: str
    trade_no: Optional[str]
    pay_time: Optional[datetime]
    expire_time: datetime
    created_at: datetime
    updated_at: datetime

    # 会员等级信息
    membership_level: Optional[Dict[str, Any]] = None

    # 计算字段
    @computed_field
    @property
    def total_hours(self) -> int:
        """总小时数"""
        return self.hours + self.bonus_hours

    @computed_field
    @property
    def is_paid(self) -> bool:
        """是否已支付"""
        return self.payment_status == "paid"

    @computed_field
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        if self.pay_time:
            return False
        return datetime.now() > self.expire_time if self.expire_time else False

    @computed_field
    @property
    def status_color(self) -> str:
        """状态颜色"""
        colors = {
            "pending": "warning",
            "processing": "info",
            "paid": "success",
            "completed": "success",
            "cancelled": "default",
            "failed": "danger",
            "refunded": "secondary",
            "expired": "default",
        }
        return colors.get(self.payment_status, "default")

    @computed_field
    @property
    def status_label(self) -> str:
        """状态中文标签"""
        labels = {
            "pending": "待支付",
            "processing": "处理中",
            "paid": "已支付",
            "completed": "已完成",
            "cancelled": "已取消",
            "failed": "支付失败",
            "refunded": "已退款",
            "expired": "已过期",
        }
        return labels.get(self.payment_status, "未知")


class PaymentWebhookIn(BaseModel):
    """支付回调输入"""
    """基类，具体字段由微信/支付宝决定"""
    pass


class WechatPayNotifyIn(BaseModel):
    """微信支付回调"""
    # 具体字段根据微信支付文档定义
    pass


class AlipayNotifyIn(BaseModel):
    """支付宝回调"""
    # 具体字段根据支付宝文档定义
    pass


class UsageLogOut(BaseModel):
    """使用记录输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    session_id: str
    duration_seconds: int
    service_type: str
    details: Dict[str, Any]
    characters_count: int
    api_cost: Decimal
    created_at: datetime


# 保留原有的旧Schema以便兼容
class OrderBase(BaseModel):
    """订单基础模型（保留以兼容旧代码）"""
    customer_id: int = Field(..., description="客户ID")
    product_id: int = Field(..., description="产品ID")
    quantity: int = Field(default=1, ge=1, description="购买数量")
    remark: Optional[str] = Field(None, description="订单备注")


class OrderCreateRequest(OrderBase):
    """创建订单请求模型（保留以兼容旧代码）"""
    pass


class OrderUpdateRequest(BaseModel):
    """更新订单请求模型"""
    payment_status: Optional[str] = Field(None, description="支付状态(pending/processing/paid/completed/cancelled/failed/refunded/expired)")
    remark: Optional[str] = Field(None, description="订单备注")


class PaymentUpdateRequest(BaseModel):
    """更新支付状态请求模型（保留以兼容旧代码）"""
    order_id: int = Field(..., description="订单ID")
    payment_status: int = Field(..., description="支付状态: 0-待支付, 1-已支付, 2-支付失败, 3-已退款")
    payment_method: Optional[str] = Field(None, description="支付方式")
    transaction_id: Optional[str] = Field(None, description="支付平台交易ID")


class OrderItemResponse(BaseModel):
    """订单项响应模型（保留以兼容旧代码）"""
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


class OrderDetailResponse(OrderItemResponse):
    """订单详情响应模型（保留以兼容旧代码）"""
    payment_method: Optional[str] = None
    payment_time: Optional[datetime] = None
    transaction_id: Optional[str] = None
    remark: Optional[str] = None
    updated_at: datetime


class OrderListResponse(BaseModel):
    """订单列表响应模型"""
    total: int
    items: list


class OrderCreateResponse(BaseModel):
    """创建订单响应模型"""
    order_id: int
    order_no: str
    message: str = "订单创建成功"
