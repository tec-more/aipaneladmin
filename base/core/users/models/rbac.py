"""
角色权限模型
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin


class Role(BaseModel, TimestampMixin):
    """角色模型"""
    name = fields.CharField(max_length=50, unique=True, description="角色名称", index=True)
    code = fields.CharField(max_length=50, unique=True, description="角色编码", index=True)
    description = fields.TextField(null=True, description="角色描述")
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)
    sort = fields.IntField(default=0, description="排序")

    # 多对多关系
    users = fields.ManyToManyField("models.User", related_name="roles", through="user_role")
    permissions = fields.ManyToManyField("models.Permission", related_name="roles", through="role_permission")

    class Meta:
        table = "role"
        ordering = ["sort", "-created_at"]

    async def to_dict(self, include_permissions: bool = False):
        """转换为字典"""
        data = {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "is_active": self.is_active,
            "sort": self.sort,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }

        if include_permissions:
            try:
                perms = await self.permissions.all()
                data["permissions"] = [await p.to_dict() for p in perms]
            except Exception:
                data["permissions"] = []

        return data


class Permission(BaseModel, TimestampMixin):
    """权限模型"""
    name = fields.CharField(max_length=100, unique=True, description="权限名称", index=True)
    code = fields.CharField(max_length=100, unique=True, description="权限编码", index=True)
    description = fields.TextField(null=True, description="权限描述")
    module = fields.CharField(max_length=50, null=True, description="所属模块", index=True)
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)

    class Meta:
        table = "permission"
        ordering = ["module", "name"]

    async def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "code": self.code,
            "description": self.description,
            "module": self.module,
            "is_active": self.is_active,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


class Menu(BaseModel, TimestampMixin):
    """菜单模型"""
    name = fields.CharField(max_length=50, description="菜单名称", index=True)
    path = fields.CharField(max_length=200, null=True, description="菜单路径")
    icon = fields.CharField(max_length=50, null=True, description="菜单图标")
    component = fields.CharField(max_length=200, null=True, description="组件路径")
    parent_id = fields.IntField(null=True, description="父菜单ID", index=True)
    sort = fields.IntField(default=0, description="排序")
    is_visible = fields.BooleanField(default=True, description="是否显示")
    is_cached = fields.BooleanField(default=True, description="是否缓存")
    is_active = fields.BooleanField(default=True, description="是否激活", index=True)
    menu_type = fields.CharField(max_length=20, default="menu", description="菜单类型: directory/menu/button")
    permission = fields.CharField(max_length=100, null=True, description="权限标识", index=True)

    class Meta:
        table = "menu"
        ordering = ["sort", "id"]

    async def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "icon": self.icon,
            "component": self.component,
            "parent_id": self.parent_id,
            "sort": self.sort,
            "is_visible": self.is_visible,
            "is_cached": self.is_cached,
            "is_active": self.is_active,
            "menu_type": self.menu_type,
            "permission": self.permission,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }
