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
        # 处理 WebSocket 连接
        if scope["type"] == "websocket":
            client = scope.get("client", ["", ""])[0] if scope.get("client") else ""
            original_path = scope.get("path", "")

            # 处理 /api 前缀（与HTTP请求保持一致）
            path = original_path
            if path.startswith(self.prefix):
                # 移除 /api 前缀
                new_path = path[len(self.prefix):] or "/"
                scope = dict(scope)  # 创建副本
                scope["path"] = new_path
                scope["root_path"] = self.prefix

            # 打印日志
            # print(f'INFO:     ({client}, -) "WebSocket {original_path}"', flush=True)

            await self.app(scope, receive, send)
            return

        # 处理 HTTP 请求
        if scope["type"] == "http":
            original_path = scope.get("path", "")
            method = scope.get("method", "")
            client = scope.get("client", ["", ""])[0] if scope.get("client") else ""

            # 打印访问日志
            # print(f'INFO:     {client} - "{method} {original_path} HTTP/1.1"', flush=True)

            # OPTIONS 请求（CORS 预检）直接透传
            if method == "OPTIONS":
                await self.app(scope, receive, send)
                return

            # 静态资源路径也直接透传
            if (original_path.startswith("/docs") or
                original_path.startswith("/openapi") or
                original_path.startswith("/redoc") or
                original_path.startswith("/static") or
                original_path.startswith("/metrics") or
                original_path.startswith("/health")):
                # 直接传给 FastAPI，不处理
                await self.app(scope, receive, send)
                return

            # 如果路径以 prefix 开头，移除它
            if original_path.startswith(self.prefix):
                # 修改 scope
                new_path = original_path[len(self.prefix):] or "/"
                scope = dict(scope)  # 创建副本
                scope["path"] = new_path
                scope["root_path"] = self.prefix

            # 如果路径不以 prefix 开头，但是是API路径（/v1/开头），自动添加前缀
            elif original_path.startswith("/v1/"):
                # 自动为API路径添加 /api 前缀（兼容前端）
                new_path = original_path
                scope = dict(scope)
                scope["path"] = new_path
                scope["root_path"] = self.prefix

            else:
                import os
                from starlette.responses import FileResponse, HTMLResponse

                static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web", "dist")
                
                if original_path.startswith("/assets/"):
                    file_path = os.path.join(static_dir, original_path.lstrip("/"))
                    if os.path.exists(file_path):
                        await FileResponse(file_path)(scope, receive, send)
                    else:
                        await HTMLResponse(status_code=404, content="Not Found")(scope, receive, send)
                    return
                
                index_path = os.path.join(static_dir, "index.html")
                if os.path.exists(index_path):
                    await FileResponse(index_path)(scope, receive, send)
                else:
                    await HTMLResponse(status_code=500, content="Frontend index.html not found")(scope, receive, send)
                return

        # 调用实际应用
        await self.app(scope, receive, send)

# 创建包装后的应用
app = ASGIAppWithPrefix(real_app, prefix="/api")
