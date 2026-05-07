-- 添加系统设置菜单和初始化默认设置

-- 1. 插入系统设置菜单
INSERT INTO menu (
    name, path, icon, component, parent_id, sort,
    is_visible, is_cached, is_active, menu_type, permission,
    created_at, updated_at
) VALUES (
    '系统设置', '/system-setting', 'Setting', 'systemSetting/index', NULL, 99,
    TRUE, TRUE, TRUE, 'menu', 'system:setting',
    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
)
ON CONFLICT (name, path) DO NOTHING;

-- 2. 初始化默认系统设置
INSERT INTO system_setting (
    key, value, name, description, setting_type, is_active, sort,
    created_at, updated_at
) VALUES
    ('system_name', 'AI智能管理系统', '系统名称', '网站或系统的名称', 'string', TRUE, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('system_logo', '', '系统Logo', '网站或系统的Logo图片URL', 'image', TRUE, 2, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('system_icp', '', '备案号', '网站ICP备案号', 'string', TRUE, 3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('system_copyright', '© 2024 AI智能管理系统 版权所有', '版权信息', '网站底部版权声明', 'string', TRUE, 4, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('system_description', '一个强大的AI智能管理平台', '系统描述', '网站或系统的简要描述', 'string', TRUE, 5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (key) DO NOTHING;

-- 完成
