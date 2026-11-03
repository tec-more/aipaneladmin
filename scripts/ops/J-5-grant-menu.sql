-- 资源授权管理 · 菜单注册（FR-01 入口）
-- 溯源：docs/arch/resource-grant-admin-tech.md §4.1（菜单后端驱动，component 映射 @/views/**）
-- 说明：superuser 自动获得全部菜单（menu.py get_user_menus），不授权给任何角色即仅 superuser 可见。
-- 兼容：MySQL / openGauss(PG) 均可执行（同表子查询用派生表包裹）。
-- D9 修复：父分组按「系统管理」directory 解析（实测环境结构）；不存在则落顶级（parent_id=NULL）。

INSERT INTO menu (name, path, icon, component, parent_id, sort, is_visible, is_cached, is_active, menu_type, permission, created_at, updated_at)
SELECT '资源授权', '/panel/grant', 'Key', 'grant/Index',
       (SELECT t.id FROM (SELECT id FROM menu WHERE name = '系统管理' AND menu_type = 'directory' ORDER BY id LIMIT 1) t),
       99, 1, 1, 1, 'menu', 'grant:manage', NOW(), NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM menu WHERE path = '/panel/grant'
);
