import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise
from base.common import database
from base.common.setting import settings
from base.common.database import init_data
from base.common.middleware import register_middlewares
from base.common.exceptions import register_exceptions
from base.common.router import register_routers
from base.common.json_encoder import DateTimeEncoder
from base.plugins import plugin_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    print("Application starting up...")
    try:
        await init_data()

        # 初始化插件系统
        plugin_manager.set_app(app)
        await plugin_manager.load_enabled_plugins()
        await plugin_manager.startup()
        print("插件系统初始化完成")

        yield

        # 关闭插件系统
        await plugin_manager.shutdown()
        await Tortoise.close_connections()
    finally:
        # 确保所有资源正确关闭
        print("Application shutting down...")

def init_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        json_dumps=lambda data, **kwargs: json.dumps(data, **kwargs, cls=DateTimeEncoder, ensure_ascii=False)
    )

    # 设置服务器 URL（用于文档页面的 "Try it out" 功能）
    app.state.servers = [
        {"url": "http://127.0.0.1:9998/api", "description": "本地开发服务器"},
    ]

    # 立即保存并替换 openapi 方法（在路由注册之前）
    _original_openapi = app.openapi

    def custom_openapi():
        import sys
        # 总是重新生成 schema（包含所有已注册的路由）
        openapi_schema = _original_openapi()

        # 设置服务器 URL
        if hasattr(app.state, 'servers'):
            openapi_schema["servers"] = app.state.servers

        paths = openapi_schema.get('paths', {})
        customer_auth_count = len([p for p in paths.keys() if 'customer/auth' in p])
        print(f"[custom_openapi] Generated schema with {customer_auth_count} customer/auth paths, total {len(paths)} paths", file=sys.stderr, flush=True)
        return openapi_schema

    app.openapi = custom_openapi

    # 注册中间件、路由和异常处理
    register_exceptions(app)
    register_middlewares(app)

    # 使用自动路由注册机制
    register_routers(app)

    return app
