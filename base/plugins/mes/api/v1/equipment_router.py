from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from base.plugins.mes.services.equipment_service import EquipmentService
    from base.plugins.mes.schemas.mes_schema import (
        EquipmentCreate, EquipmentUpdate, EquipmentResponse, EquipmentListQuery,
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

    class EquipmentService:
        @staticmethod
        async def get_by_id(id):
            return None
        @staticmethod
        async def create_equipment(data):
            return None
        @staticmethod
        async def update_equipment(id, data):
            return None
        @staticmethod
        async def delete_equipment(id):
            return False
        @staticmethod
        async def change_status(id, status):
            return None
        @staticmethod
        async def get_list(**kwargs):
            return [], 0

    class EquipmentCreate(BaseModel): pass
    class EquipmentUpdate(BaseModel): pass
    class EquipmentResponse(BaseModel): pass
    class EquipmentListQuery(BaseModel): pass
    class ListResponse(BaseModel): pass

router = APIRouter(prefix="/equipment", tags=["设备管理"])

@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(equipment_id: int):
    equipment = await EquipmentService.get_by_id(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equipment

@router.post("", response_model=EquipmentResponse)
async def create_equipment(data: EquipmentCreate):
    try:
        equipment = await EquipmentService.create_equipment(data)
        return equipment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(equipment_id: int, data: EquipmentUpdate):
    try:
        equipment = await EquipmentService.update_equipment(equipment_id, data)
        if not equipment:
            raise HTTPException(status_code=404, detail="设备不存在")
        return equipment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/{equipment_id}")
async def delete_equipment(equipment_id: int):
    success = await EquipmentService.delete_equipment(equipment_id)
    if not success:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"message": "删除成功"}

@router.post("/{equipment_id}/status")
async def change_equipment_status(equipment_id: int, status: str):
    equipment = await EquipmentService.change_status(equipment_id, status)
    if not equipment:
        raise HTTPException(status_code=404, detail="设备不存在")
    return equipment

@router.get("", response_model=ListResponse[EquipmentResponse])
async def list_equipment(
    page: int = 1,
    page_size: int = 10,
    equipment_code: Optional[str] = None,
    equipment_name: Optional[str] = None,
    equipment_type: Optional[str] = None,
    status: Optional[str] = None
):
    items, total = await EquipmentService.get_list(
        page=page, page_size=page_size,
        equipment_code=equipment_code,
        equipment_name=equipment_name,
        equipment_type=equipment_type,
        status=status
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}