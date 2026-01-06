"""
客户数据模型
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
        def EmailField(**kwargs):
            return kwargs

class Customer(BaseModel, TimestampMixin):
    """注册用户模型"""
    username = fields.CharField(max_length=50, unique=True, description="用户名", index=True)
    email = fields.CharField(max_length=255, unique=True, description="邮箱", index=True)
    phone = fields.CharField(max_length=20, unique=True, null=True, description="手机号", index=True)
    password = fields.CharField(max_length=128, description="密码")
    
    # 用户信息字段
    nickname = fields.CharField(max_length=50, null=True, description="昵称", index=True)
    avatar = fields.CharField(max_length=255, null=True, description="头像URL")
    gender = fields.IntField(default=0, description="性别: 0-未知, 1-男, 2-女")
    birthday = fields.DatetimeField(null=True, description="生日")
    address = fields.CharField(max_length=255, null=True, description="地址")
    
    # 账户状态
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)
    is_verified = fields.BooleanField(default=False, description="是否已验证邮箱/手机号")
    
    # 账户信息
    points = fields.IntField(default=0, description="积分")
    balance = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00, description="余额")
    membership_expiry_date = fields.DatetimeField(null=True, description="会员到期日期", index=True)
    
    # 登录信息
    last_login = fields.DatetimeField(null=True, description="最后登录时间", index=True)
    login_count = fields.IntField(default=0, description="登录次数")

    class Meta:
        table = "customer"

    async def to_dict(self):
        """转换为字典"""
        data = {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "gender": self.gender,
            "birthday": self.birthday.strftime("%Y-%m-%d") if self.birthday else None,
            "address": self.address,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "points": self.points,
            "balance": float(self.balance) if hasattr(self.balance, "__float__") else self.balance,
            "membership_expiry_date": self.membership_expiry_date.strftime("%Y-%m-%d %H:%M:%S") if self.membership_expiry_date else None,
            "last_login": self.last_login.strftime("%Y-%m-%d %H:%M:%S") if self.last_login else None,
            "login_count": self.login_count,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
        return data