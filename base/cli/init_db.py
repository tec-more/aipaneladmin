"""
数据库初始化脚本 - 创建初始数据
"""
import asyncio
from base.core.users.models.users import User
from base.core.users.models.rbac import Role, Permission, Menu
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
        print("✅ 管理员用户已存在")
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
    print(f"✅ 创建管理员用户成功: {admin.username}")
    return admin


async def create_default_roles():
    """创建默认角色"""
    roles_data = [
        {"name": "超级管理员", "code": "super_admin", "description": "拥有所有权限", "sort": 1},
        {"name": "管理员", "code": "admin", "description": "系统管理员", "sort": 2},
        {"name": "普通用户", "code": "user", "description": "普通用户", "sort": 3},
    ]

    created_roles = []
    for role_info in roles_data:
        # 检查是否已存在
        existing_role = await Role.filter(code=role_info["code"]).first()
        if existing_role:
            print(f"✅ 角色已存在: {existing_role.name}")
            created_roles.append(existing_role)
            continue

        role = await Role.create(**role_info)
        created_roles.append(role)
        print(f"✅ 创建角色: {role.name}")

    return created_roles


async def create_default_permissions():
    """创建默认权限"""
    permissions_data = [
        # 用户管理
        {"name": "查看用户", "code": "user:view", "module": "用户管理"},
        {"name": "创建用户", "code": "user:create", "module": "用户管理"},
        {"name": "编辑用户", "code": "user:edit", "module": "用户管理"},
        {"name": "删除用户", "code": "user:delete", "module": "用户管理"},
        # 角色管理
        {"name": "查看角色", "code": "role:view", "module": "角色管理"},
        {"name": "创建角色", "code": "role:create", "module": "角色管理"},
        {"name": "编辑角色", "code": "role:edit", "module": "角色管理"},
        {"name": "删除角色", "code": "role:delete", "module": "角色管理"},
        # 权限管理
        {"name": "查看权限", "code": "permission:view", "module": "权限管理"},
        {"name": "创建权限", "code": "permission:create", "module": "权限管理"},
        {"name": "编辑权限", "code": "permission:edit", "module": "权限管理"},
        {"name": "删除权限", "code": "permission:delete", "module": "权限管理"},
        # 部门管理
        {"name": "查看部门", "code": "dept:view", "module": "部门管理"},
        {"name": "创建部门", "code": "dept:create", "module": "部门管理"},
        {"name": "编辑部门", "code": "dept:edit", "module": "部门管理"},
        {"name": "删除部门", "code": "dept:delete", "module": "部门管理"},
        # 菜单管理
        {"name": "查看菜单", "code": "menu:view", "module": "菜单管理"},
        {"name": "创建菜单", "code": "menu:create", "module": "菜单管理"},
        {"name": "编辑菜单", "code": "menu:edit", "module": "菜单管理"},
        {"name": "删除菜单", "code": "menu:delete", "module": "菜单管理"},
        # 日志管理
        {"name": "查看日志", "code": "log:view", "module": "日志管理"},
        {"name": "删除日志", "code": "log:delete", "module": "日志管理"},
    ]

    created_permissions = []
    for perm_info in permissions_data:
        # 检查是否已存在
        existing_perm = await Permission.filter(code=perm_info["code"]).first()
        if existing_perm:
            print(f"✅ 权限已存在: {existing_perm.name}")
            created_permissions.append(existing_perm)
            continue

        permission = await Permission.create(**perm_info)
        created_permissions.append(permission)
        print(f"✅ 创建权限: {permission.name}")

    return created_permissions


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
            print(f"✅ 部门已存在: {existing_dept.name}")
            created_departments.append(existing_dept)
            continue

        department = await Department.create(**dept_info)
        created_departments.append(department)
        print(f"✅ 创建部门: {department.name}")

    return created_departments


async def create_default_menus():
    """创建默认菜单"""
    menus_data = [
        # 一级菜单
        {
            "name": "系统管理",
            "path": "/system",
            "icon": "Setting",
            "component": None,
            "parent_id": None,
            "sort": 1,
            "menu_type": "menu",
        },
        {
            "name": "用户管理",
            "path": "/system/users",
            "icon": "User",
            "component": "/system/users/index",
            "parent_id": None,  # 后面会更新
            "sort": 1,
            "menu_type": "menu",
            "permission_code": "user:view",
        },
        {
            "name": "角色管理",
            "path": "/system/roles",
            "icon": "UserFilled",
            "component": "/system/roles/index",
            "parent_id": None,  # 后面会更新
            "sort": 2,
            "menu_type": "menu",
            "permission_code": "role:view",
        },
        {
            "name": "部门管理",
            "path": "/system/departments",
            "icon": "OfficeBuilding",
            "component": "/system/departments/index",
            "parent_id": None,  # 后面会更新
            "sort": 3,
            "menu_type": "menu",
            "permission_code": "dept:view",
        },
        {
            "name": "菜单管理",
            "path": "/system/menus",
            "icon": "Menu",
            "component": "/system/menus/index",
            "parent_id": None,  # 后面会更新
            "sort": 4,
            "menu_type": "menu",
            "permission_code": "menu:view",
        },
        {
            "name": "操作日志",
            "path": "/system/logs",
            "icon": "Document",
            "component": "/system/logs/index",
            "parent_id": None,  # 后面会更新
            "sort": 5,
            "menu_type": "menu",
            "permission_code": "log:view",
        },
    ]

    # 先创建系统管理菜单
    system_menu = await Menu.filter(name="系统管理").first()
    if not system_menu:
        system_menu = await Menu.create(**menus_data[0])
        print(f"✅ 创建菜单: {system_menu.name}")
    else:
        print(f"✅ 菜单已存在: {system_menu.name}")

    # 创建子菜单
    for menu_info in menus_data[1:]:
        existing_menu = await Menu.filter(name=menu_info["name"]).first()
        if existing_menu:
            print(f"✅ 菜单已存在: {existing_menu.name}")
            continue

        menu_info["parent_id"] = system_menu.id
        menu = await Menu.create(**menu_info)
        print(f"✅ 创建菜单: {menu.name}")


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

        # 为超级管理员角色分配所有权限
        super_admin_role = await Role.filter(code="super_admin").first()
        if super_admin_role:
            await super_admin_role.permissions.clear()
            await super_admin_role.permissions.add(*permissions)
            print(f"✅ 为角色 '{super_admin_role.name}' 分配了所有权限")

        # 为管理员用户分配超级管理员角色
        await admin_user.roles.clear()
        await admin_user.roles.add(super_admin_role)
        print(f"✅ 为用户 '{admin_user.username}' 分配了角色 '{super_admin_role.name}'")

        # 创建默认部门
        departments = await create_default_departments()

        # 创建默认菜单
        await create_default_menus()

        print("=" * 50)
        print("✅ 数据库初始化完成!")
        print("=" * 50)
        print("\n登录信息:")
        print(f"  用户名: admin")
        print(f"  密码: admin123")
        print(f"  邮箱: admin@example.com")
        print("\n访问地址:")
        print(f"  API文档: http://localhost:9999/docs")
        print("=" * 50)

    except Exception as e:
        print(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
