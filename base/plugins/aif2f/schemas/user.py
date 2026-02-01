"""
用户相关 Schema
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime


class UserProfileOut(BaseModel):
    """用户资料输出"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: Optional[str]
    nickname: Optional[str]
    avatar: Optional[str]
    is_active: bool
    created_at: datetime

    # 会员信息
    membership: Optional[dict] = None


class UserProfileUpdate(BaseModel):
    """更新用户资料"""
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    email: Optional[EmailStr] = None
