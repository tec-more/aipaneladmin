from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from base.plugins.mes.services.production_service import (
        ManufacturingOrderService, WorkOrderService
    )
    from base.plugins.mes.schemas.mes_schema import (
        ManufacturingOrderCreate, ManufacturingOrderUpdate, ManufacturingOrderResponse, ManufacturingOrderListQuery,
        WorkOrderCreate, WorkOrderUpdate, WorkOrderResponse, WorkOrderListQuery,
        ListResponse
    )
except ImportError:
    class BaseModel:
        pass

    class APIRouter:
        def __init__(self, prefix="", tags=None):
            self.prefix = prefix
            self.tags = tags or []

        def get(self, path):
            def decorator(func):
                return func
            return decorator

        def post(self, path):
            def decorator(func):
                return func
            return decorator

        def put(self, path):
            def decorator(func):
                return func
            return decorator

        def delete(self, path):
            def decorator(func):
                return func
            return decorator

    class Depends:
        def __init__(self, func):
            pass

    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            pass

    class ManufacturingOrderService:
        @staticmethod
        async def get_by_id(id):
            return None
        @staticmethod
        async def create_mo(data):
            return None
        @staticmethod
        async def update_mo(id, data):
            return None
        @staticmethod
        async def delete_mo(id):
            return False
        @staticmethod
        async def release_mo(id):
            return None
        @staticmethod
        async def complete_mo(id):
            return None
        @staticmethod
        async def cancel_mo(id):
            return None
        @staticmethod
        async def get_list(**kwargs):
            return [], 0

    class WorkOrderService(ManufacturingOrderService):
        @staticmethod
        async def create_wo(data):
            return None
        @staticmethod
        async def update_wo(id, data):
            return None
        @staticmethod
        async def delete_wo(id):
            return False
        @staticmethod
        async def release_wo(id):
            return None
        @staticmethod
        async def start_wo(id, operator=None):
            return None
        @staticmethod
        async def complete_wo(id, actual_qty, scrap_qty=0):
            return None
        @staticmethod
        async def close_wo(id):
            return None

    class WorkOrderCreate(BaseModel): pass
    class WorkOrderUpdate(BaseModel): pass
    class WorkOrderResponse(BaseModel): pass
    class WorkOrderListQuery(BaseModel): pass
    class ListResponse(BaseModel): pass

router = APIRouter(prefix="/production", tags=["生产计划管理"])

@router.get("/manufacturing-orders/{mo_id}", response_model=ManufacturingOrderResponse)
async def get_mo(mo_id: int):
    mo = await ManufacturingOrderService.get_by_id(mo_id)
    if not mo:
        raise HTTPException(status_code=404, detail="制造单不存在")
    return mo

@router.post("/manufacturing-orders", response_model=ManufacturingOrderResponse)
async def create_mo(data: ManufacturingOrderCreate):
    try:
        mo = await ManufacturingOrderService.create_mo(data)
        return mo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/manufacturing-orders/{mo_id}", response_model=ManufacturingOrderResponse)
async def update_mo(mo_id: int, data: ManufacturingOrderUpdate):
    try:
        mo = await ManufacturingOrderService.update_mo(mo_id, data)
        if not mo:
            raise HTTPException(status_code=404, detail="制造单不存在")
        return mo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/manufacturing-orders/{mo_id}")
async def delete_mo(mo_id: int):
    success = await ManufacturingOrderService.delete_mo(mo_id)
    if not success:
        raise HTTPException(status_code=404, detail="制造单不存在")
    return {"message": "删除成功"}

@router.post("/manufacturing-orders/{mo_id}/release")
async def release_mo(mo_id: int):
    try:
        mo = await ManufacturingOrderService.release_mo(mo_id)
        if not mo:
            raise HTTPException(status_code=404, detail="制造单不存在")
        return mo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/manufacturing-orders/{mo_id}/complete")
async def complete_mo(mo_id: int):
    try:
        mo = await ManufacturingOrderService.complete_mo(mo_id)
        if not mo:
            raise HTTPException(status_code=404, detail="制造单不存在")
        return mo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/manufacturing-orders/{mo_id}/cancel")
async def cancel_mo(mo_id: int):
    try:
        mo = await ManufacturingOrderService.cancel_mo(mo_id)
        if not mo:
            raise HTTPException(status_code=404, detail="制造单不存在")
        return mo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/manufacturing-orders", response_model=ListResponse[ManufacturingOrderResponse])
async def list_mos(
    page: int = 1,
    page_size: int = 10,
    mo_code: Optional[str] = None,
    product_code: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None
):
    items, total = await ManufacturingOrderService.get_list(
        page=page, page_size=page_size,
        mo_code=mo_code,
        product_code=product_code,
        status=status,
        priority=priority
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@router.get("/work-orders/{wo_id}", response_model=WorkOrderResponse)
async def get_wo(wo_id: int):
    wo = await WorkOrderService.get_by_id(wo_id)
    if not wo:
        raise HTTPException(status_code=404, detail="工单不存在")
    return wo

@router.post("/work-orders", response_model=WorkOrderResponse)
async def create_wo(data: WorkOrderCreate):
    try:
        wo = await WorkOrderService.create_wo(data)
        return wo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/work-orders/{wo_id}", response_model=WorkOrderResponse)
async def update_wo(wo_id: int, data: WorkOrderUpdate):
    try:
        wo = await WorkOrderService.update_wo(wo_id, data)
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return wo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/work-orders/{wo_id}")
async def delete_wo(wo_id: int):
    success = await WorkOrderService.delete_wo(wo_id)
    if not success:
        raise HTTPException(status_code=404, detail="工单不存在")
    return {"message": "删除成功"}

@router.post("/work-orders/{wo_id}/release")
async def release_wo(wo_id: int):
    try:
        wo = await WorkOrderService.release_wo(wo_id)
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return wo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/work-orders/{wo_id}/start")
async def start_wo(wo_id: int, operator: Optional[str] = None):
    try:
        wo = await WorkOrderService.start_wo(wo_id, operator)
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return wo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/work-orders/{wo_id}/complete")
async def complete_wo(wo_id: int, actual_quantity: int, scrap_quantity: int = 0):
    try:
        wo = await WorkOrderService.complete_wo(wo_id, actual_quantity, scrap_quantity)
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return wo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/work-orders/{wo_id}/close")
async def close_wo(wo_id: int):
    try:
        wo = await WorkOrderService.close_wo(wo_id)
        if not wo:
            raise HTTPException(status_code=404, detail="工单不存在")
        return wo
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/work-orders", response_model=ListResponse[WorkOrderResponse])
async def list_wos(
    page: int = 1,
    page_size: int = 10,
    wo_code: Optional[str] = None,
    mo_code: Optional[str] = None,
    product_code: Optional[str] = None,
    status: Optional[str] = None,
    work_center_code: Optional[str] = None
):
    items, total = await WorkOrderService.get_list(
        page=page, page_size=page_size,
        wo_code=wo_code,
        mo_code=mo_code,
        product_code=product_code,
        status=status,
        work_center_code=work_center_code
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}