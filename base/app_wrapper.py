#!/usr/bin/env python3
"""
应用包装器 - 添加 /api 前缀
使用 ProxyFix 模式的 ASGI 中间件
"""
from base.start import init_app

# 创建实际应用
real_app = init_app()

class ASGIAppWithPrefix:
    """ASGI 应用包装器，自动添加路径前缀"""

    def __init__(self, app, prefix="/api"):
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # ========== 在这里打印 URL ==========
            original_path = scope.get("path", "")
            method = scope.get("method", "")
            client = scope.get("client", ["", ""])[0] if scope.get("client") else ""

            # 打印访问日志（使用 print 到 stdout）
            print(f'INFO:     {client} - "{method} {original_path} HTTP/1.1"', flush=True)

            # 如果路径以 prefix 开头，移除它
            if original_path.startswith(self.prefix):
                # 修改 scope
                new_path = original_path[len(self.prefix):] or "/"
                scope = dict(scope)  # 创建副本
                scope["path"] = new_path
                scope["root_path"] = self.prefix

        # 调用实际应用
        await self.app(scope, receive, send)

# 创建包装后的应用
app = ASGIAppWithPrefix(real_app, prefix="/api")
