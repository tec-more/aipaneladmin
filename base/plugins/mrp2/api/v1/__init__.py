from fastapi import APIRouter

from .forecast_router import forecast_router
from .mps_router import mps_router
from .mrp_router import mrp_router
from .crp_router import crp_router
from .monitor_router import monitor_router

router = APIRouter(prefix="/v1/mrp2")

router.include_router(forecast_router)
router.include_router(mps_router)
router.include_router(mrp_router)
router.include_router(crp_router)
router.include_router(monitor_router)

__all__ = ["router"]