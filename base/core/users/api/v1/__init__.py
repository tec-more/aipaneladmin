"""
Core 用户模块 API 路由注册
确保所有路由被正确导入和注册
"""
from . import auth, users, menu, rbac, dashboard, operation_log, admin

# 导出所有路由，确保它们可以被自动发现
__all__ = [
    "auth",
    "users",
    "menu",
    "rbac",
    "dashboard",
    "operation_log",
    "admin"
]
