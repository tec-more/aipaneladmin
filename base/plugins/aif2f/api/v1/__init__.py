"""
AIF2F API V1 Router
"""

from fastapi import APIRouter

from .user import router as user_router
from .membership import router as membership_router
from .payment import router as payment_router

router = APIRouter()

# 注册子路由
router.include_router(user_router)
router.include_router(membership_router)
router.include_router(payment_router)

__all__ = ["router"]
