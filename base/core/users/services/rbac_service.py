"""
角色权限服务层
"""
from typing import Optional, List, Tuple
from tortoise.expressions import Q

from base.core.users.models.rbac import Role, Permission, Menu
from base.core.users.models.users import User
from base.core.users.schemas.rbac import RoleCreate, RoleUpdate, PermissionCreate, PermissionUpdate


class RoleService:
    """角色服务类"""

    @staticmethod
    async def get_by_id(role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        return await Role.filter(id=role_id).first()

    @staticmethod
    async def get_by_code(code: str) -> Optional[Role]:
        """根据编码获取角色"""
        return await Role.filter(code=code).first()

    @staticmethod
    async def create_role(role_data: RoleCreate) -> Role:
        """创建角色"""
        role = await Role.create(
            name=role_data.name,
            code=role_data.code,
            description=role_data.description,
            sort=role_data.sort,
        )

        # 关联权限
        if role_data.permission_ids:
            permissions = await Permission.filter(id__in=role_data.permission_ids)
            await role.permissions.add(*permissions)

        return role

    @staticmethod
    async def update_role(role_id: int, role_data: RoleUpdate) -> Optional[Role]:
        """更新角色"""
        role = await Role.filter(id=role_id).first()
        if not role:
            return None

        update_data = role_data.model_dump(exclude_unset=True)
        await role.update_from_dict(update_data).save()
        return role

    @staticmethod
    async def delete_role(role_id: int) -> bool:
        """删除角色"""
        deleted_count = await Role.filter(id=role_id).delete()
        return deleted_count > 0

    @staticmethod
    async def get_role_list(
            page: int = 1,
            page_size: int = 10,
            name: Optional[str] = None,
            is_active: Optional[bool] = None,
    ) -> Tuple[List[Role], int]:
        """获取角色列表"""
        query = Role.all()

        if name:
            query = query.filter(name__icontains=name)
        if is_active is not None:
            query = query.filter(is_active=is_active)

        total = await query.count()

        offset = (page - 1) * page_size
        roles = await query.offset(offset).limit(page_size).order_by('sort', '-created_at')

        return roles, total

    @staticmethod
    async def assign_permissions_to_role(role_id: int, permission_ids: List[int]) -> bool:
        """为角色分配权限"""
        role = await Role.filter(id=role_id).first()
        if not role:
            return False

        # 清除原有权限
        await role.permissions.clear()

        # 添加新权限
        if permission_ids:
            permissions = await Permission.filter(id__in=permission_ids)
            await role.permissions.add(*permissions)

        return True

    @staticmethod
    async def get_role_permissions(role_id: int) -> List[Permission]:
        """获取角色的所有权限"""
        role = await Role.filter(id=role_id).prefetch_related('permissions').first()
        if not role:
            return []
        return await role.permissions.all()

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        """检查角色编码是否存在"""
        query = Role.filter(code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()


class PermissionService:
    """权限服务类"""

    @staticmethod
    async def get_by_id(permission_id: int) -> Optional[Permission]:
        """根据ID获取权限"""
        return await Permission.filter(id=permission_id).first()

    @staticmethod
    async def get_by_code(code: str) -> Optional[Permission]:
        """根据编码获取权限"""
        return await Permission.filter(code=code).first()

    @staticmethod
    async def create_permission(permission_data: PermissionCreate) -> Permission:
        """创建权限"""
        permission = await Permission.create(
            name=permission_data.name,
            code=permission_data.code,
            description=permission_data.description,
            module=permission_data.module,
        )
        return permission

    @staticmethod
    async def update_permission(permission_id: int, permission_data: PermissionUpdate) -> Optional[Permission]:
        """更新权限"""
        permission = await Permission.filter(id=permission_id).first()
        if not permission:
            return None

        update_data = permission_data.model_dump(exclude_unset=True)
        await permission.update_from_dict(update_data).save()
        return permission

    @staticmethod
    async def delete_permission(permission_id: int) -> bool:
        """删除权限"""
        deleted_count = await Permission.filter(id=permission_id).delete()
        return deleted_count > 0

    @staticmethod
    async def get_permission_list(
            page: int = 1,
            page_size: int = 10,
            module: Optional[str] = None,
            is_active: Optional[bool] = None,
    ) -> Tuple[List[Permission], int]:
        """获取权限列表"""
        query = Permission.all()

        if module:
            query = query.filter(module=module)
        if is_active is not None:
            query = query.filter(is_active=is_active)

        total = await query.count()

        offset = (page - 1) * page_size
        permissions = await query.offset(offset).limit(page_size).order_by('module', 'name')

        return permissions, total

    @staticmethod
    async def get_all_permissions() -> List[Permission]:
        """获取所有权限"""
        return await Permission.filter(is_active=True).all()

    @staticmethod
    async def check_code_exists(code: str, exclude_id: Optional[int] = None) -> bool:
        """检查权限编码是否存在"""
        query = Permission.filter(code=code)
        if exclude_id:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    @staticmethod
    async def get_user_permissions(user_id: int) -> List[str]:
        """获取用户的所有权限编码"""
        user = await User.filter(id=user_id).prefetch_related('roles__permissions').first()
        if not user:
            return []

        # 如果是超级管理员,返回所有权限
        if user.is_superuser:
            all_permissions = await Permission.filter(is_active=True).all()
            return [perm.code for perm in all_permissions]

        # 获取用户所有角色的权限
        permission_codes = set()
        roles = await user.roles.filter(is_active=True).prefetch_related('permissions')
        for role in roles:
            permissions = await role.permissions.filter(is_active=True)
            permission_codes.update([perm.code for perm in permissions])

        return list(permission_codes)
