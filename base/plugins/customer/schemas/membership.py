"""
会员相关 Schema
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from decimal import Decimal


class MembershipLevelIn(BaseModel):
    """创建/更新会员等级"""
    level_type: str
    level: int
    name: str
    description: Optional[str] = None
    duration_days: int
    duration_hours: int = 0
    price: Decimal
    original_price: Optional[Decimal] = None
    bonus_hours: int = 0
    features: List[str] = []
    sort_order: int = 0
    is_active: bool = True


class MembershipLevelOut(BaseModel):
    """会员等级输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    level_type: str
    level: int
    name: str
    description: Optional[str]
    duration_days: int
    duration_hours: int
    price: Decimal
    original_price: Optional[Decimal]
    bonus_hours: int
    features: List[str]
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CustomerMembershipOut(BaseModel):
    """客户会员信息输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    membership_level_id: Optional[int]
    start_time: datetime
    expire_time: datetime
    total_hours: int
    used_hours: Decimal
    remaining_hours: Decimal
    level: int
    is_active: bool
    is_vip: bool
    is_expired: bool

    # 包含的会员等级信息
    membership_level: Optional[MembershipLevelOut] = None


class FibonacciLevelOut(BaseModel):
    """Fibonacci等级输出"""
    level: int
    total_hours: int
    next_level_hours: Optional[int]
    remaining_to_next: Optional[int]
    privileges: List[str]


class CalculateFibonacciLevelIn(BaseModel):
    """计算Fibonacci等级输入"""
    hours: int
