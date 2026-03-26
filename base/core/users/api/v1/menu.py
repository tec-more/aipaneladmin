"""
菜单管理API
"""
from fastapi import APIRouter, Depends, status

from base.core.users.schemas.rbac import MenuCreate, MenuUpdate, MenuResponse, MenuTree
from base.core.users.services.menu_service import MenuService
from base.core.users.services.user_service import UserService
from base.common.security import get_current_user_id
from base.common.response import SuccessResponse, ErrorResponse

router = APIRouter(prefix="/v1/menus", tags=["菜单管理"])


@router.get("/tree", summary="获取菜单树")
async def get_menu_tree(current_user_id: int = Depends(get_current_user_id)):
    """获取菜单树形结构"""
    tree = await MenuService.build_menu_tree()
    return SuccessResponse(data=tree)


@router.get("/user-menus", summary="获取当前用户菜单")
async def get_user_menus(current_user_id: int = Depends(get_current_user_id)):
    """获取当前用户可访问的菜单树"""
    user = await UserService.get_by_id(current_user_id)
    if not user:
        return ErrorResponse(msg="用户不存在", status_code=status.HTTP_404_NOT_FOUND)

    menus = await MenuService.get_user_menus(current_user_id, user.is_superuser)
    return SuccessResponse(data=menus)


@router.get("/{menu_id}", summary="获取菜单详情")
async def get_menu_detail(
        menu_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """获取菜单详情"""
    menu = await MenuService.get_by_id(menu_id)
    if not menu:
        return ErrorResponse(msg="菜单不存在", status_code=status.HTTP_404_NOT_FOUND)

    menu_dict = await menu.to_dict()
    return SuccessResponse(data=menu_dict)


@router.post("", summary="创建菜单")
async def create_menu(
        menu_data: MenuCreate,
        current_user_id: int = Depends(get_current_user_id)
):
    """创建菜单(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    menu = await MenuService.create_menu(menu_data)
    menu_dict = await menu.to_dict()

    return SuccessResponse(data=menu_dict, msg="创建成功")


@router.put("/{menu_id}", summary="更新菜单")
async def update_menu(
        menu_id: int,
        menu_data: MenuUpdate,
        current_user_id: int = Depends(get_current_user_id)
):
    """更新菜单(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    menu = await MenuService.update_menu(menu_id, menu_data)
    if not menu:
        return ErrorResponse(msg="菜单不存在", status_code=status.HTTP_404_NOT_FOUND)

    menu_dict = await menu.to_dict()
    return SuccessResponse(data=menu_dict, msg="更新成功")


@router.delete("/{menu_id}", summary="删除菜单")
async def delete_menu(
        menu_id: int,
        current_user_id: int = Depends(get_current_user_id)
):
    """删除菜单(管理员功能)"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    success = await MenuService.delete_menu(menu_id)
    if not success:
        return ErrorResponse(
            msg="菜单不存在或存在子菜单,无法删除",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    return SuccessResponse(msg="删除成功")
