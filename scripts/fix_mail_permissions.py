"""
修复 mail 模块权限和菜单
将 mail 权限分配给所有角色
"""
import asyncio
from base.common.database import init_data
from base.core.users.models.rbac import Permission, Role
from base.core.users.models.users import User as UserModel


async def fix_mail_permissions():
    await init_data()
    
    mail_perms = await Permission.filter(module='mail').all()
    print(f"找到 {len(mail_perms)} 个 mail 权限")
    for p in mail_perms:
        print(f"  {p.code}")
    
    roles = await Role.filter(is_active=True).all()
    print(f"\n找到 {len(roles)} 个角色")
    
    for role in roles:
        existing_perm_ids = [rp.id for rp in await role.permissions.all()]
        mail_perm_ids = [p.id for p in mail_perms]
        missing = [p for p in mail_perms if p.id not in existing_perm_ids]
        
        print(f"\n角色 {role.name} ({role.code}):")
        print(f"  现有权限: {len(existing_perm_ids)} 个")
        print(f"  缺少 mail 权限: {len(missing)} 个")
        
        if missing:
            await role.permissions.add(*missing)
            print(f"  已添加 {len(missing)} 个 mail 权限")
        else:
            print(f"  已拥有所有 mail 权限")
    
    users = await UserModel.filter(is_active=True).limit(5).all()
    print(f"\n用户列表:")
    for u in users:
        print(f"  id={u.id}, username={u.username}, is_superuser={u.is_superuser}")
    
    print("\n修复完成！")


if __name__ == "__main__":
    asyncio.run(fix_mail_permissions())
