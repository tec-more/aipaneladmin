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

        import sys
        print("[DEBUG] Plugin startup complete, triggering schema generation...", file=sys.stderr, flush=True)

        # 触发一次 schema 生成以验证
        schema = app.openapi()

        print(f"[DEBUG] Initial schema generated, total paths: {len(schema.get('paths', {}))}", file=sys.stderr, flush=True)

        # Debug: 打印所有包含 customer/auth 的路径
        paths = schema.get('paths', {})
        customer_auth_paths = [p for p in paths.keys() if 'customer/auth' in p]
        print(f"[DEBUG] Found {len(customer_auth_paths)} customer/auth paths in initial schema", file=sys.stderr, flush=True)
        if customer_auth_paths:
            print(f"[DEBUG] Customer auth paths: {customer_auth_paths[:5]}...", file=sys.stderr, flush=True)

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
        lifespan=lifespan,
        json_dumps=lambda data, **kwargs: json.dumps(data, **kwargs, cls=DateTimeEncoder, ensure_ascii=False)
    )

    # 立即保存并替换 openapi 方法（在路由注册之前）
    _original_openapi = app.openapi

    def custom_openapi():
        import sys
        # 总是重新生成 schema（包含所有已注册的路由）
        openapi_schema = _original_openapi()
        paths = openapi_schema.get('paths', {})
        customer_auth_count = len([p for p in paths.keys() if 'customer/auth' in p])
        print(f"[custom_openapi] Generated schema with {customer_auth_count} customer/auth paths, total {len(paths)} paths", file=sys.stderr, flush=True)
        return openapi_schema

    app.openapi = custom_openapi

    # 注册中间件、路由和异常处理
    register_exceptions(app)
    register_middlewares(app)
    register_routers(app)

    return app
