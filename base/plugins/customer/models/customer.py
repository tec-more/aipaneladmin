from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class Customer(BaseModel, TimestampMixin):
    """Customer model"""

    # 系统关联
    system_user_id = fields.BigIntField(unique=True, null=True, description="关联的系统用户ID")

    # 基本信息
    openid = fields.CharField(max_length=100, unique=True, description="OpenID for WeChat", null=True)
    unionid = fields.CharField(max_length=100, unique=True, description="UnionID for WeChat", null=True)
    phone = fields.CharField(max_length=20, unique=True, description="Phone number", null=True)
    email = fields.CharField(max_length=100, unique=True, description="Email", null=True)
    nickname = fields.CharField(max_length=100, description="Nickname", null=True)
    avatar = fields.CharField(max_length=500, description="Avatar URL", null=True)

    # 认证信息
    username = fields.CharField(max_length=50, unique=True, null=True, description="用户名")
    password = fields.CharField(max_length=128, null=True, description="密码(加密)")

    # 状态
    is_active = fields.BooleanField(default=True, description="是否激活")
    is_verified = fields.BooleanField(default=False, description="是否已验证")

    # 统计信息
    last_login = fields.DatetimeField(null=True, description="最后登录时间")
    login_count = fields.IntField(default=0, description="登录次数")

    class Meta:
        table = "customer"
        table_description = "Customer table"

    def __str__(self):
        return self.nickname or self.username or self.phone or self.email or str(self.id)

    async def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
