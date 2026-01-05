"""
数据库初始化脚本 - 创建初始数据
"""
import asyncio
from base.core.users.models.users import User
from base.core.users.models.rbac import Role, Permission, Menu, PermissionGroup
from base.core.dept.models.department import Department
from base.common.security import get_password_hash
from tortoise import Tortoise
from base.common.setting import settings


async def init_database():
    """初始化数据库连接"""
    await Tortoise.init(config=settings.TORTOISE_ORM)
    await Tortoise.generate_schemas()


async def create_admin_user():
    """创建管理员用户"""
    # 检查是否已存在admin用户
    existing_user = await User.filter(username="admin").first()
    if existing_user:
        print("[OK] 管理员用户已存在")
        return existing_user

    # 创建admin用户
    admin = await User.create(
        username="admin",
        email="admin@example.com",
        password=get_password_hash("admin123"),
        alias="系统管理员",
        is_superuser=True,
        is_active=True,
    )
    print(f"[OK] 创建管理员用户成功: {admin.username}")
    return admin


async def create_default_roles():
    """创建默认角色"""
    roles_data = [
        {"name": "超级管理员", "code": "super_admin", "description": "拥有所有权限", "sort": 1, "data_scope": "all"},
        {"name": "管理员", "code": "admin", "description": "系统管理员", "sort": 2, "data_scope": "all", "parent_id": None},
        {"name": "部门经理", "code": "dept_manager", "description": "部门经理，可管理本部门数据", "sort": 3, "data_scope": "dept_tree"},
        {"name": "普通用户", "code": "user", "description": "普通用户，只能查看自己的数据", "sort": 4, "data_scope": "self"},
    ]

    created_roles = []
    for role_info in roles_data:
        # 检查是否已存在
        existing_role = await Role.filter(code=role_info["code"]).first()
        if existing_role:
            print(f"[OK] 角色已存在: {existing_role.name}")
            created_roles.append(existing_role)
            continue

        role = await Role.create(**role_info)
        created_roles.append(role)
        print(f"[OK] 创建角色: {role.name}")

    # 设置角色继承关系
    admin_role = await Role.filter(code="admin").first()
    super_admin_role = await Role.filter(code="super_admin").first()
    if admin_role and super_admin_role and admin_role.parent_id is None:
        admin_role.parent_id = super_admin_role.id
        await admin_role.save()
        print(f"[OK] 设置角色继承: {admin_role.name} -> {super_admin_role.name}")

    return created_roles


async def create_default_permissions():
    """创建默认权限"""
    permissions_data = [
        # 用户管理
        {"name": "查看用户列表", "code": "user:list", "module": "用户管理", "description": "查看用户列表"},
        {"name": "创建用户", "code": "user:create", "module": "用户管理", "description": "创建新用户"},
        {"name": "更新用户", "code": "user:update", "module": "用户管理", "description": "更新用户信息"},
        {"name": "删除用户", "code": "user:delete", "module": "用户管理", "description": "删除用户"},
        # 角色管理
        {"name": "查看角色列表", "code": "role:list", "module": "角色管理", "description": "查看角色列表"},
        {"name": "创建角色", "code": "role:create", "module": "角色管理", "description": "创建新角色"},
        {"name": "更新角色", "code": "role:update", "module": "角色管理", "description": "更新角色信息"},
        {"name": "删除角色", "code": "role:delete", "module": "角色管理", "description": "删除角色"},
        # 权限管理
        {"name": "查看权限列表", "code": "permission:list", "module": "权限管理", "description": "查看权限列表"},
        {"name": "创建权限", "code": "permission:create", "module": "权限管理", "description": "创建新权限"},
        {"name": "更新权限", "code": "permission:update", "module": "权限管理", "description": "更新权限信息"},
        {"name": "删除权限", "code": "permission:delete", "module": "权限管理", "description": "删除权限"},
        # 权限组管理
        {"name": "查看权限组列表", "code": "permission_group:list", "module": "权限组管理", "description": "查看权限组列表"},
        {"name": "创建权限组", "code": "permission_group:create", "module": "权限组管理", "description": "创建新权限组"},
        {"name": "更新权限组", "code": "permission_group:update", "module": "权限组管理", "description": "更新权限组信息"},
        {"name": "删除权限组", "code": "permission_group:delete", "module": "权限组管理", "description": "删除权限组"},
        # 部门管理
        {"name": "查看部门列表", "code": "dept:list", "module": "部门管理", "description": "查看部门列表"},
        {"name": "创建部门", "code": "dept:create", "module": "部门管理", "description": "创建新部门"},
        {"name": "更新部门", "code": "dept:update", "module": "部门管理", "description": "更新部门信息"},
        {"name": "删除部门", "code": "dept:delete", "module": "部门管理", "description": "删除部门"},
        # 菜单管理
        {"name": "查看菜单列表", "code": "menu:list", "module": "菜单管理", "description": "查看菜单列表"},
        {"name": "创建菜单", "code": "menu:create", "module": "菜单管理", "description": "创建新菜单"},
        {"name": "更新菜单", "code": "menu:update", "module": "菜单管理", "description": "更新菜单信息"},
        {"name": "删除菜单", "code": "menu:delete", "module": "菜单管理", "description": "删除菜单"},
        # 日志管理
        {"name": "查看日志", "code": "log:list", "module": "日志管理", "description": "查看操作日志"},
        {"name": "删除日志", "code": "log:delete", "module": "日志管理", "description": "删除操作日志"},
    ]

    created_permissions = []
    for perm_info in permissions_data:
        # 检查是否已存在
        existing_perm = await Permission.filter(code=perm_info["code"]).first()
        if existing_perm:
            print(f"[OK] 权限已存在: {existing_perm.name}")
            created_permissions.append(existing_perm)
            continue

        permission = await Permission.create(**perm_info)
        created_permissions.append(permission)
        print(f"[OK] 创建权限: {permission.name}")

    return created_permissions


async def create_default_permission_groups():
    """创建默认权限组"""
    groups_data = [
        {
            "name": "用户管理全部权限",
            "code": "user_all",
            "description": "用户管理模块的全部权限",
            "permission_codes": ["user:list", "user:create", "user:update", "user:delete"]
        },
        {
            "name": "角色管理全部权限",
            "code": "role_all",
            "description": "角色管理模块的全部权限",
            "permission_codes": ["role:list", "role:create", "role:update", "role:delete"]
        },
        {
            "name": "权限管理全部权限",
            "code": "permission_all",
            "description": "权限管理模块的全部权限",
            "permission_codes": ["permission:list", "permission:create", "permission:update", "permission:delete"]
        },
        {
            "name": "部门管理全部权限",
            "code": "dept_all",
            "description": "部门管理模块的全部权限",
            "permission_codes": ["dept:list", "dept:create", "dept:update", "dept:delete"]
        },
        {
            "name": "只读权限",
            "code": "readonly",
            "description": "所有模块的查看权限",
            "permission_codes": ["user:list", "role:list", "permission:list", "permission_group:list", "dept:list", "menu:list", "log:list"]
        },
    ]

    created_groups = []
    for group_info in groups_data:
        # 检查是否已存在
        existing_group = await PermissionGroup.filter(code=group_info["code"]).first()
        if existing_group:
            print(f"[OK] 权限组已存在: {existing_group.name}")
            created_groups.append(existing_group)
            continue

        # 获取权限列表
        permission_codes = group_info.pop("permission_codes", [])
        group = await PermissionGroup.create(**group_info)

        # 关联权限
        if permission_codes:
            permissions = await Permission.filter(code__in=permission_codes).all()
            await group.permissions.add(*permissions)

        created_groups.append(group)
        print(f"[OK] 创建权限组: {group.name} (包含 {len(permission_codes)} 个权限)")

    return created_groups


async def create_default_departments():
    """创建默认部门"""
    departments_data = [
        {"name": "总公司", "code": "root", "parent_id": None, "sort": 1},
        {"name": "技术部", "code": "tech", "parent_id": None, "sort": 2},
        {"name": "市场部", "code": "market", "parent_id": None, "sort": 3},
        {"name": "人事部", "code": "hr", "parent_id": None, "sort": 4},
    ]

    created_departments = []
    for dept_info in departments_data:
        # 检查是否已存在
        existing_dept = await Department.filter(code=dept_info["code"]).first()
        if existing_dept:
            print(f"[OK] 部门已存在: {existing_dept.name}")
            created_departments.append(existing_dept)
            continue

        department = await Department.create(**dept_info)
        created_departments.append(department)
        print(f"[OK] 创建部门: {department.name}")

    return created_departments


async def create_default_menus(force: bool = False):
    """创建默认菜单

    Args:
        force: 是否强制重建菜单（会删除现有菜单）
    """
    # 检查是否已有菜单数据
    menu_count = await Menu.all().count()
    if menu_count > 0:
        if not force:
            print(f"[OK] 菜单数据已存在 ({menu_count} 条)")
            return
        else:
            # 强制模式：删除所有现有菜单
            await Menu.all().delete()
            print(f"[!] 已删除 {menu_count} 条现有菜单数据")

    # 仪表盘菜单（一级菜单）
    dashboard_menu = await Menu.create(
        name="仪表盘",
        path="/dashboard",
        icon="Odometer",
        component="dashboard/Index",
        parent_id=None,
        sort=0,
        menu_type="menu",
        permission=None,
        is_visible=True,
        is_active=True,
    )
    print(f"[OK] 创建菜单: {dashboard_menu.name}")

    # 系统管理目录（一级菜单）
    system_menu = await Menu.create(
        name="系统管理",
        path="/system",
        icon="Setting",
        component=None,
        parent_id=None,
        sort=1,
        menu_type="directory",
        permission=None,
        is_visible=True,
        is_active=True,
    )
    print(f"[OK] 创建菜单: {system_menu.name}")

    # 系统管理子菜单
    sub_menus = [
        {
            "name": "用户管理",
            "path": "/users",
            "icon": "User",
            "component": "user/Index",
            "sort": 1,
            "permission": "user:list",
        },
        {
            "name": "部门管理",
            "path": "/departments",
            "icon": "OfficeBuilding",
            "component": "department/Index",
            "sort": 2,
            "permission": "dept:list",
        },
        {
            "name": "角色管理",
            "path": "/roles",
            "icon": "UserFilled",
            "component": "role/Index",
            "sort": 3,
            "permission": "role:list",
        },
        {
            "name": "权限管理",
            "path": "/permissions",
            "icon": "Key",
            "component": "permission/Index",
            "sort": 4,
            "permission": "permission:list",
        },
        {
            "name": "菜单管理",
            "path": "/menus",
            "icon": "Menu",
            "component": "menu/Index",
            "sort": 5,
            "permission": "menu:list",
        },
        {
            "name": "插件管理",
            "path": "/plugins",
            "icon": "Connection",
            "component": "plugin/Index",
            "sort": 6,
            "permission": None,
        },
    ]

    for menu_info in sub_menus:
        menu = await Menu.create(
            name=menu_info["name"],
            path=menu_info["path"],
            icon=menu_info["icon"],
            component=menu_info["component"],
            parent_id=system_menu.id,
            sort=menu_info["sort"],
            menu_type="menu",
            permission=menu_info["permission"],
            is_visible=True,
            is_active=True,
        )
        print(f"[OK] 创建菜单: {menu.name}")


async def main():
    """主函数"""
    print("=" * 50)
    print("开始初始化数据库...")
    print("=" * 50)

    try:
        # 初始化数据库连接
        await init_database()

        # 创建管理员用户
        admin_user = await create_admin_user()

        # 创建默认角色
        roles = await create_default_roles()

        # 创建默认权限
        permissions = await create_default_permissions()

        # 创建默认权限组
        permission_groups = await create_default_permission_groups()

        # 为超级管理员角色分配所有权限
        super_admin_role = await Role.filter(code="super_admin").first()
        if super_admin_role:
            await super_admin_role.permissions.clear()
            await super_admin_role.permissions.add(*permissions)
            print(f"[OK] 为角色 '{super_admin_role.name}' 分配了所有权限")

        # 为管理员角色分配权限组
        admin_role = await Role.filter(code="admin").first()
        if admin_role:
            user_all_group = await PermissionGroup.filter(code="user_all").first()
            dept_all_group = await PermissionGroup.filter(code="dept_all").first()
            if user_all_group and dept_all_group:
                await admin_role.permission_groups.clear()
                await admin_role.permission_groups.add(user_all_group, dept_all_group)
                print(f"[OK] 为角色 '{admin_role.name}' 分配了权限组")

        # 为普通用户角色分配只读权限组
        user_role = await Role.filter(code="user").first()
        if user_role:
            readonly_group = await PermissionGroup.filter(code="readonly").first()
            if readonly_group:
                await user_role.permission_groups.clear()
                await user_role.permission_groups.add(readonly_group)
                print(f"[OK] 为角色 '{user_role.name}' 分配了只读权限组")

        # 为管理员用户分配超级管理员角色
        await admin_user.roles.clear()
        await admin_user.roles.add(super_admin_role)
        print(f"[OK] 为用户 '{admin_user.username}' 分配了角色 '{super_admin_role.name}'")

        # 创建默认部门
        departments = await create_default_departments()

        # 创建默认菜单
        await create_default_menus()

        print("=" * 50)
        print("[OK] 数据库初始化完成!")
        print("=" * 50)
        print("\n登录信息:")
        print(f"  用户名: admin")
        print(f"  密码: admin123")
        print(f"  邮箱: admin@example.com")
        print("\n访问地址:")
        print(f"  API文档: http://localhost:9999/docs")
        print("=" * 50)

    except Exception as e:
        print(f"[ERR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()


async def init_menus_only(force: bool = False):
    """仅初始化菜单数据"""
    print("=" * 50)
    print("开始初始化菜单...")
    print("=" * 50)

    try:
        await init_database()
        await create_default_menus(force=force)
        print("=" * 50)
        print("[OK] 菜单初始化完成!")
        print("=" * 50)
    except Exception as e:
        print(f"[ERR] 菜单初始化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    import sys

    # 支持命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "menus":
            # 仅初始化菜单: python -m base.cli.init_db menus
            force = "--force" in sys.argv
            asyncio.run(init_menus_only(force=force))
        elif sys.argv[1] == "--help":
            print("用法:")
            print("  python -m base.cli.init_db         # 完整初始化")
            print("  python -m base.cli.init_db menus   # 仅初始化菜单")
            print("  python -m base.cli.init_db menus --force  # 强制重建菜单")
        else:
            asyncio.run(main())
    else:
        asyncio.run(main())
