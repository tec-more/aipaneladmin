"""
hello_world API 路由
"""
from fastapi import APIRouter
from base.common.response import SuccessResponse

router = APIRouter(prefix="/api/v1/hello_world", tags=["Hello World"])


@router.get("/")
async def index():
    """Hello World 首页"""
    return SuccessResponse(data={"message": "Welcome to Hello World plugin"})


@router.get("/health")
async def health():
    """健康检查"""
    return SuccessResponse(data={"status": "ok"})
