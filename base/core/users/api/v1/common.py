from fastapi import APIRouter
from base.common.setting import settings
from base.common.response import success_response

router = APIRouter(prefix="/v1/common", tags=["公共配置"])


@router.get("/system-config", summary="获取系统公共配置")
async def get_system_config():
    """获取前端可公开的系统配置（无需登录）"""
    return success_response({
        "app_name": settings.app_name,
        "app_version": settings.app_version,
        "app_description": settings.app_description,
        "frontend_name": settings.frontend_name,
        "backend_name": settings.backend_name,
        "debug": settings.debug,
        "install_redirect": settings.install_redirect,
    })
