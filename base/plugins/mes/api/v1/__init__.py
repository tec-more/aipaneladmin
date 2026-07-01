from fastapi import APIRouter

from .base_data_router import base_data_router
from .production_router import production_router

router = APIRouter(prefix="/v1/mes")

router.include_router(base_data_router)
router.include_router(production_router)

__all__ = ["router"]