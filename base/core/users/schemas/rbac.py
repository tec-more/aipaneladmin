"""
角色权限相关的Pydantic模型
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# ==================== 角色相关 ==================== #

class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., min_length=1, max_length=50, description="角色名称")
    code: str = Field(..., min_length=1, max_length=50, description="角色编码")
    description: Optional[str] = Field(None, description="角色描述")
    sort: int = Field(default=0, description="排序")


class RoleCreate(RoleBase):
    """创建角色模型"""
    permission_ids: List[int] = Field(default=[], description="权限ID列表")


class RoleUpdate(BaseModel):
    """更新角色模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="角色名称")
    description: Optional[str] = Field(None, description="角色描述")
    is_active: Optional[bool] = Field(None, description="是否激活")
    sort: Optional[int] = Field(None, description="排序")


class RoleResponse(BaseModel):
    """角色响应模型"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    sort: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleWithPermissions(RoleResponse):
    """带权限的角色响应模型"""
    permissions: List["PermissionResponse"] = []


# ==================== 权限相关 ==================== #

class PermissionBase(BaseModel):
    """权限基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="权限名称")
    code: str = Field(..., min_length=1, max_length=100, description="权限编码")
    description: Optional[str] = Field(None, description="权限描述")
    module: Optional[str] = Field(None, max_length=50, description="所属模块")


class PermissionCreate(PermissionBase):
    """创建权限模型"""
    pass


class PermissionUpdate(BaseModel):
    """更新权限模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="权限名称")
    description: Optional[str] = Field(None, description="权限描述")
    module: Optional[str] = Field(None, max_length=50, description="所属模块")
    is_active: Optional[bool] = Field(None, description="是否激活")


class PermissionResponse(BaseModel):
    """权限响应模型"""
    id: int
    name: str
    code: str
    description: Optional[str] = None
    module: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== 菜单相关 ==================== #

class MenuBase(BaseModel):
    """菜单基础模型"""
    name: str = Field(..., min_length=1, max_length=50, description="菜单名称")
    path: str = Field(..., max_length=200, description="菜单路径")
    icon: Optional[str] = Field(None, max_length=50, description="菜单图标")
    component: Optional[str] = Field(None, max_length=200, description="组件路径")
    parent_id: Optional[int] = Field(None, description="父菜单ID")
    sort: int = Field(default=0, description="排序")
    is_hidden: bool = Field(default=False, description="是否隐藏")
    menu_type: str = Field(default="menu", description="菜单类型: menu/button")
    permission_code: Optional[str] = Field(None, max_length=100, description="权限编码")


class MenuCreate(MenuBase):
    """创建菜单模型"""
    pass


class MenuUpdate(BaseModel):
    """更新菜单模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="菜单名称")
    path: Optional[str] = Field(None, max_length=200, description="菜单路径")
    icon: Optional[str] = Field(None, max_length=50, description="菜单图标")
    component: Optional[str] = Field(None, max_length=200, description="组件路径")
    parent_id: Optional[int] = Field(None, description="父菜单ID")
    sort: Optional[int] = Field(None, description="排序")
    is_hidden: Optional[bool] = Field(None, description="是否隐藏")
    is_active: Optional[bool] = Field(None, description="是否激活")
    menu_type: Optional[str] = Field(None, description="菜单类型")
    permission_code: Optional[str] = Field(None, description="权限编码")


class MenuResponse(BaseModel):
    """菜单响应模型"""
    id: int
    name: str
    path: str
    icon: Optional[str] = None
    component: Optional[str] = None
    parent_id: Optional[int] = None
    sort: int
    is_hidden: bool
    is_active: bool
    menu_type: str
    permission_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MenuTree(MenuResponse):
    """菜单树形结构"""
    children: List["MenuTree"] = []


# ==================== 用户角色分配 ==================== #

class UserRoleAssign(BaseModel):
    """用户角色分配模型"""
    user_id: int = Field(..., description="用户ID")
    role_ids: List[int] = Field(..., description="角色ID列表")


class RolePermissionAssign(BaseModel):
    """角色权限分配模型"""
    role_id: int = Field(..., description="角色ID")
    permission_ids: List[int] = Field(..., description="权限ID列表")
