"""
订单相关 Schema
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal


class CreateOrderIn(BaseModel):
    """创建订单输入"""
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
    total_hours: int
    payment_method: str
    payment_status: str
    trade_no: Optional[str]
    pay_time: Optional[datetime]
    expire_time: datetime
    is_paid: bool
    is_expired: bool

    # 会员等级信息
    membership_level: Optional[Dict[str, Any]] = None


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
