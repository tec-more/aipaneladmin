from fastapi import APIRouter

from .base_data_router import base_data_router
from .production_router import production_router
from .quality_router import quality_router
from .equipment_router import equipment_router

router = APIRouter(prefix="/v1/mes")

router.include_router(base_data_router)
router.include_router(production_router)
router.include_router(quality_router)
router.include_router(equipment_router)

__all__ = ["router"]