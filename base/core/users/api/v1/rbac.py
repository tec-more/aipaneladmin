"""
角色权限管理API
"""
from fastapi import APIRouter, Depends, status, Query
from typing import Optional, List

from base.core.users.schemas.rbac import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    PermissionCreate,
    PermissionUpdate,
    PermissionResponse,
    UserRoleAssign,
    RolePermissionAssign,
)
from base.core.users.services.rbac_service import RoleService, PermissionService
from base.core.users.services.user_service import UserService
from base.common.security import get_current_user_id
from base.common.response import SuccessResponse, ErrorResponse

router = APIRouter(prefix="/api/v1/rbac", tags=["角色权限管理"])


# ==================== 角色管理 ==================== #

@router.get("/roles/list", summary="获取角色列表")
async def get_role_list(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        name: Optional[str] = Query(None, description="角色名称(模糊搜索)"),
        is_active: Optional[bool] = Query(None, description="是否激活"),
        current_user_id: int = Depends(get_current_user_id)
):
    """获取角色列表"""
    roles, total = await RoleService.get_role_list(
        page=page,
        page_size=page_size,
        name=name,
        is_active=is_active,
    )

    role_list = []
    for role in roles:
        role_dict = await role.to_dict()
        role_list.append(role_dict)

    response_data = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": role_list
    }

    return SuccessResponse(data=response_data)


@router.get("/roles/{role_id}", summary="获取角色详情")
async def get_role_detail(
        role_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """获取角色详情(包含权限列表)"""
    role = await RoleService.get_by_id(role_id)
    if not role:
        return ErrorResponse(msg="角色不存在", status_code=status.HTTP_404_NOT_FOUND)

    role_dict = await role.to_dict()

    # 获取角色权限
    permissions = await RoleService.get_role_permissions(role_id)
    permission_list = [await perm.to_dict() for perm in permissions]
    role_dict['permissions'] = permission_list

    return SuccessResponse(data=role_dict)


@router.post("/roles", summary="创建角色")
async def create_role(
        role_data: RoleCreate,
        current_user_id: int = Depends(get_current_user_id)
):
    """创建角色(管理员功能)"""
    # 检查权限
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    # 检查角色编码是否存在
    if await RoleService.check_code_exists(role_data.code):
        return ErrorResponse(msg="角色编码已存在", status_code=status.HTTP_400_BAD_REQUEST)

    # 创建角色
    role = await RoleService.create_role(role_data)
    role_dict = await role.to_dict()

    return SuccessResponse(data=role_dict, msg="创建成功")


@router.put("/roles/{role_id}", summary="更新角色")
async def update_role(
        role_id: int,
        role_data: RoleUpdate,
        current_user_id: int = Depends(get_current_user_id)
):
    """更新角色(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    role = await RoleService.update_role(role_id, role_data)
    if not role:
        return ErrorResponse(msg="角色不存在", status_code=status.HTTP_404_NOT_FOUND)

    role_dict = await role.to_dict()
    return SuccessResponse(data=role_dict, msg="更新成功")


@router.delete("/roles/{role_id}", summary="删除角色")
async def delete_role(
        role_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """删除角色(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    success = await RoleService.delete_role(role_id)
    if not success:
        return ErrorResponse(msg="角色不存在", status_code=status.HTTP_404_NOT_FOUND)

    return SuccessResponse(msg="删除成功")


@router.post("/roles/{role_id}/permissions", summary="为角色分配权限")
async def assign_permissions(
        role_id: int,
        assign_data: RolePermissionAssign,
        current_user_id: int = Depends(get_current_user_id)
):
    """为角色分配权限(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    success = await RoleService.assign_permissions_to_role(role_id, assign_data.permission_ids)
    if not success:
        return ErrorResponse(msg="角色不存在", status_code=status.HTTP_404_NOT_FOUND)

    return SuccessResponse(msg="权限分配成功")


# ==================== 权限管理 ==================== #

@router.get("/permissions/list", summary="获取权限列表")
async def get_permission_list(
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(10, ge=1, le=100, description="每页数量"),
        module: Optional[str] = Query(None, description="所属模块"),
        is_active: Optional[bool] = Query(None, description="是否激活"),
        current_user_id: int = Depends(get_current_user_id)
):
    """获取权限列表"""
    permissions, total = await PermissionService.get_permission_list(
        page=page,
        page_size=page_size,
        module=module,
        is_active=is_active,
    )

    permission_list = []
    for perm in permissions:
        perm_dict = await perm.to_dict()
        permission_list.append(perm_dict)

    response_data = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": permission_list
    }

    return SuccessResponse(data=response_data)


@router.get("/permissions/all", summary="获取所有权限")
async def get_all_permissions(current_user_id: int = Depends(get_current_user_id)):
    """获取所有激活的权限"""
    permissions = await PermissionService.get_all_permissions()
    permission_list = [await perm.to_dict() for perm in permissions]
    return SuccessResponse(data=permission_list)


@router.post("/permissions", summary="创建权限")
async def create_permission(
        permission_data: PermissionCreate,
        current_user_id: int = Depends(get_current_user_id)
):
    """创建权限(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    # 检查权限编码是否存在
    if await PermissionService.check_code_exists(permission_data.code):
        return ErrorResponse(msg="权限编码已存在", status_code=status.HTTP_400_BAD_REQUEST)

    permission = await PermissionService.create_permission(permission_data)
    perm_dict = await permission.to_dict()

    return SuccessResponse(data=perm_dict, msg="创建成功")


@router.put("/permissions/{permission_id}", summary="更新权限")
async def update_permission(
        permission_id: int,
        permission_data: PermissionUpdate,
        current_user_id: int = Depends(get_current_user_id)
):
    """更新权限(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    permission = await PermissionService.update_permission(permission_id, permission_data)
    if not permission:
        return ErrorResponse(msg="权限不存在", status_code=status.HTTP_404_NOT_FOUND)

    perm_dict = await permission.to_dict()
    return SuccessResponse(data=perm_dict, msg="更新成功")


@router.delete("/permissions/{permission_id}", summary="删除权限")
async def delete_permission(
        permission_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """删除权限(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    success = await PermissionService.delete_permission(permission_id)
    if not success:
        return ErrorResponse(msg="权限不存在", status_code=status.HTTP_404_NOT_FOUND)

    return SuccessResponse(msg="删除成功")


# ==================== 用户角色管理 ==================== #

@router.post("/users/{user_id}/roles", summary="为用户分配角色")
async def assign_roles_to_user(
        user_id: int,
        assign_data: UserRoleAssign,
        current_user_id: int = Depends(get_current_user_id)
):
    """为用户分配角色(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    user = await UserService.get_by_id(user_id)
    if not user:
        return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)

    # 清除原有角色
    await user.roles.clear()

    # 添加新角色
    if assign_data.role_ids:
        from base.core.users.models.rbac import Role
        roles = await Role.filter(id__in=assign_data.role_ids)
        await user.roles.add(*roles)

    return SuccessResponse(msg="角色分配成功")


@router.get("/users/{user_id}/roles", summary="获取用户的角色")
async def get_user_roles(
        user_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """获取用户的角色列表"""
    user = await UserService.get_by_id(user_id)
    if not user:
        return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)

    roles = await user.roles.all()
    role_list = [await role.to_dict() for role in roles]

    return SuccessResponse(data=role_list)


@router.get("/users/{user_id}/permissions", summary="获取用户的所有权限")
async def get_user_permissions(
        user_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """获取用户的所有权限编码"""
    permission_codes = await PermissionService.get_user_permissions(user_id)
    return SuccessResponse(data=permission_codes)
