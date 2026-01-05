"""
菜单服务层
"""
from typing import Optional, List, Tuple
from base.core.users.models.rbac import Menu
from base.core.users.schemas.rbac import MenuCreate, MenuUpdate


class MenuService:
    """菜单服务类"""

    @staticmethod
    async def get_by_id(menu_id: int) -> Optional[Menu]:
        """根据ID获取菜单"""
        return await Menu.filter(id=menu_id).first()

    @staticmethod
    async def create_menu(menu_data: MenuCreate) -> Menu:
        """创建菜单"""
        menu = await Menu.create(
            name=menu_data.name,
            path=menu_data.path,
            icon=menu_data.icon,
            component=menu_data.component,
            parent_id=menu_data.parent_id,
            sort=menu_data.sort,
            is_hidden=menu_data.is_hidden,
            menu_type=menu_data.menu_type,
            permission_code=menu_data.permission_code,
        )
        return menu

    @staticmethod
    async def update_menu(menu_id: int, menu_data: MenuUpdate) -> Optional[Menu]:
        """更新菜单"""
        menu = await Menu.filter(id=menu_id).first()
        if not menu:
            return None

        update_data = menu_data.model_dump(exclude_unset=True)
        await menu.update_from_dict(update_data).save()
        return menu

    @staticmethod
    async def delete_menu(menu_id: int) -> bool:
        """删除菜单"""
        # 检查是否有子菜单
        has_children = await Menu.filter(parent_id=menu_id).exists()
        if has_children:
            return False

        deleted_count = await Menu.filter(id=menu_id).delete()
        return deleted_count > 0

    @staticmethod
    async def get_all_menus() -> List[Menu]:
        """获取所有菜单"""
        return await Menu.filter(is_active=True).order_by('sort', 'id')

    @staticmethod
    async def build_menu_tree(menus: List[Menu] = None) -> List[dict]:
        """构建菜单树形结构"""
        if menus is None:
            menus = await MenuService.get_all_menus()

        # 转换为字典
        menu_list = []
        for menu in menus:
            menu_dict = await menu.to_dict()
            menu_dict['children'] = []
            menu_list.append(menu_dict)

        # 构建树形结构
        menu_map = {menu['id']: menu for menu in menu_list}
        tree = []

        for menu in menu_list:
            parent_id = menu.get('parent_id')
            if parent_id and parent_id in menu_map:
                menu_map[parent_id]['children'].append(menu)
            else:
                tree.append(menu)

        return tree

    @staticmethod
    async def get_user_menus(user_id: int, is_superuser: bool) -> List[dict]:
        """获取用户可访问的菜单树"""
        if is_superuser:
            # 超级管理员返回所有菜单
            menus = await MenuService.get_all_menus()
            return await MenuService.build_menu_tree(menus)

        # 普通用户根据权限获取菜单
        # TODO: 实现根据用户权限过滤菜单
        menus = await MenuService.get_all_menus()
        return await MenuService.build_menu_tree(menus)
