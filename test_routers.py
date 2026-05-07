
#!/usr/bin/env python3
"""测试路由发现功能"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from base.common.router import auto_discover_routers

# 创建测试应用
app = FastAPI(title="Router Test")

print("=" * 80)
print("开始测试路由发现...")
print("=" * 80)

# 测试发现 core.users 路由
print("\n[1] 扫描 base.core.users.api.v1")
auto_discover_routers(app, "base.core.users.api.v1")

print("\n" + "=" * 80)
print("已注册的路由:")
print("=" * 80)

for route in app.routes:
    if hasattr(route, 'path'):
        methods = ", ".join(route.methods) if hasattr(route, 'methods') else "N/A"
        print(f"  {methods:10} {route.path}")

print(f"\n总共发现 {len(app.routes)} 个路由")

# 检查是否有 /users/list 路由
found = False
for route in app.routes:
    if hasattr(route, 'path') and '/users/list' in route.path:
        found = True
        print(f"\n✅ 找到 /users/list 路由: {route.path}")
        break

if not found:
    print(f"\n❌ 没有找到 /users/list 路由！")

