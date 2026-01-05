import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from tortoise import Tortoise
from base.common import database
from base.common.setting import settings
from base.common.database import init_data
from base.common.middleware import register_middlewares
from base.common.exceptions import register_exceptions
from base.common.router import register_routers
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
        factory=True,
        lifespan=lifespan
    )

    # 注册中间件、路由和异常处理
    register_exceptions(app)
    register_middlewares(app)
    register_routers(app)

    return app
