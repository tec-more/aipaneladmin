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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    print("Application starting up...")
    try:
        await init_data()
        yield
        await Tortoise.close_connections()
    finally:
        # 确保所有资源正确关闭
        print("Application shutting down...")
        # 添加数据库连接关闭等清理代码

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