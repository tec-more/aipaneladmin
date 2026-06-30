from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

try:
    from base.plugins.mes.services.base_data_service import (
        MaterialService, BomService, WorkCenterService, ProcessService, RouteService
    )
    from base.plugins.mes.schemas.mes_schema import (
        MaterialCreate, MaterialUpdate, MaterialResponse, MaterialListQuery,
        BomCreate, BomUpdate, BomResponse, BomListQuery,
        WorkCenterCreate, WorkCenterUpdate, WorkCenterResponse, WorkCenterListQuery,
        ProcessCreate, ProcessUpdate, ProcessResponse, ProcessListQuery,
        RouteCreate, RouteUpdate, RouteResponse, RouteListQuery,
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

    class MaterialService:
        @staticmethod
        async def get_by_id(id):
            return None
        @staticmethod
        async def create_material(data):
            return None
        @staticmethod
        async def update_material(id, data):
            return None
        @staticmethod
        async def delete_material(id):
            return False
        @staticmethod
        async def get_list(**kwargs):
            return [], 0

    class BomService(MaterialService): pass
    class WorkCenterService(MaterialService): pass
    class ProcessService(MaterialService): pass
    class RouteService(MaterialService): pass

    class MaterialCreate(BaseModel): pass
    class MaterialUpdate(BaseModel): pass
    class MaterialResponse(BaseModel): pass
    class MaterialListQuery(BaseModel): pass
    class BomCreate(BaseModel): pass
    class BomUpdate(BaseModel): pass
    class BomResponse(BaseModel): pass
    class BomListQuery(BaseModel): pass
    class WorkCenterCreate(BaseModel): pass
    class WorkCenterUpdate(BaseModel): pass
    class WorkCenterResponse(BaseModel): pass
    class WorkCenterListQuery(BaseModel): pass
    class ProcessCreate(BaseModel): pass
    class ProcessUpdate(BaseModel): pass
    class ProcessResponse(BaseModel): pass
    class ProcessListQuery(BaseModel): pass
    class RouteCreate(BaseModel): pass
    class RouteUpdate(BaseModel): pass
    class RouteResponse(BaseModel): pass
    class RouteListQuery(BaseModel): pass
    class ListResponse(BaseModel): pass

base_data_router = APIRouter(prefix="/base-data", tags=["基础数据管理"])

@base_data_router.get("/materials/{material_id}", response_model=MaterialResponse)
async def get_material(material_id: int):
    material = await MaterialService.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="物料不存在")
    return material

@base_data_router.post("/materials", response_model=MaterialResponse)
async def create_material(data: MaterialCreate):
    try:
        material = await MaterialService.create_material(data)
        return material
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.put("/materials/{material_id}", response_model=MaterialResponse)
async def update_material(material_id: int, data: MaterialUpdate):
    try:
        material = await MaterialService.update_material(material_id, data)
        if not material:
            raise HTTPException(status_code=404, detail="物料不存在")
        return material
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.delete("/materials/{material_id}")
async def delete_material(material_id: int):
    success = await MaterialService.delete_material(material_id)
    if not success:
        raise HTTPException(status_code=404, detail="物料不存在")
    return {"message": "删除成功"}

@base_data_router.get("/materials", response_model=ListResponse[MaterialResponse])
async def list_materials(
    page: int = 1,
    page_size: int = 10,
    material_code: Optional[str] = None,
    material_name: Optional[str] = None,
    material_type: Optional[str] = None,
    is_active: Optional[bool] = None
):
    items, total = await MaterialService.get_list(
        page=page, page_size=page_size,
        material_code=material_code,
        material_name=material_name,
        material_type=material_type,
        is_active=is_active
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@base_data_router.get("/boms/{bom_id}", response_model=BomResponse)
async def get_bom(bom_id: int):
    bom = await BomService.get_by_id(bom_id)
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    return bom

@base_data_router.post("/boms", response_model=BomResponse)
async def create_bom(data: BomCreate):
    bom = await BomService.create_bom(data)
    return bom

@base_data_router.put("/boms/{bom_id}", response_model=BomResponse)
async def update_bom(bom_id: int, data: BomUpdate):
    bom = await BomService.update_bom(bom_id, data)
    if not bom:
        raise HTTPException(status_code=404, detail="BOM不存在")
    return bom

@base_data_router.delete("/boms/{bom_id}")
async def delete_bom(bom_id: int):
    success = await BomService.delete_bom(bom_id)
    if not success:
        raise HTTPException(status_code=404, detail="BOM不存在")
    return {"message": "删除成功"}

@base_data_router.get("/boms", response_model=ListResponse[BomResponse])
async def list_boms(
    page: int = 1,
    page_size: int = 10,
    product_code: Optional[str] = None,
    item_code: Optional[str] = None,
    version: Optional[str] = None
):
    items, total = await BomService.get_list(
        page=page, page_size=page_size,
        product_code=product_code,
        item_code=item_code,
        version=version
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@base_data_router.get("/work-centers/{wc_id}", response_model=WorkCenterResponse)
async def get_work_center(wc_id: int):
    wc = await WorkCenterService.get_by_id(wc_id)
    if not wc:
        raise HTTPException(status_code=404, detail="工作中心不存在")
    return wc

@base_data_router.post("/work-centers", response_model=WorkCenterResponse)
async def create_work_center(data: WorkCenterCreate):
    try:
        wc = await WorkCenterService.create_work_center(data)
        return wc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.put("/work-centers/{wc_id}", response_model=WorkCenterResponse)
async def update_work_center(wc_id: int, data: WorkCenterUpdate):
    try:
        wc = await WorkCenterService.update_work_center(wc_id, data)
        if not wc:
            raise HTTPException(status_code=404, detail="工作中心不存在")
        return wc
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.delete("/work-centers/{wc_id}")
async def delete_work_center(wc_id: int):
    success = await WorkCenterService.delete_work_center(wc_id)
    if not success:
        raise HTTPException(status_code=404, detail="工作中心不存在")
    return {"message": "删除成功"}

@base_data_router.get("/work-centers", response_model=ListResponse[WorkCenterResponse])
async def list_work_centers(
    page: int = 1,
    page_size: int = 10,
    work_center_code: Optional[str] = None,
    work_center_name: Optional[str] = None,
    department: Optional[str] = None
):
    items, total = await WorkCenterService.get_list(
        page=page, page_size=page_size,
        work_center_code=work_center_code,
        work_center_name=work_center_name,
        department=department
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@base_data_router.get("/processes/{process_id}", response_model=ProcessResponse)
async def get_process(process_id: int):
    process = await ProcessService.get_by_id(process_id)
    if not process:
        raise HTTPException(status_code=404, detail="工序不存在")
    return process

@base_data_router.post("/processes", response_model=ProcessResponse)
async def create_process(data: ProcessCreate):
    try:
        process = await ProcessService.create_process(data)
        return process
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.put("/processes/{process_id}", response_model=ProcessResponse)
async def update_process(process_id: int, data: ProcessUpdate):
    try:
        process = await ProcessService.update_process(process_id, data)
        if not process:
            raise HTTPException(status_code=404, detail="工序不存在")
        return process
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.delete("/processes/{process_id}")
async def delete_process(process_id: int):
    success = await ProcessService.delete_process(process_id)
    if not success:
        raise HTTPException(status_code=404, detail="工序不存在")
    return {"message": "删除成功"}

@base_data_router.get("/processes", response_model=ListResponse[ProcessResponse])
async def list_processes(
    page: int = 1,
    page_size: int = 10,
    process_code: Optional[str] = None,
    process_name: Optional[str] = None,
    work_center_code: Optional[str] = None
):
    items, total = await ProcessService.get_list(
        page=page, page_size=page_size,
        process_code=process_code,
        process_name=process_name,
        work_center_code=work_center_code
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}

@base_data_router.get("/routes/{route_id}", response_model=RouteResponse)
async def get_route(route_id: int):
    route = await RouteService.get_by_id(route_id)
    if not route:
        raise HTTPException(status_code=404, detail="工艺路线不存在")
    return route

@base_data_router.post("/routes", response_model=RouteResponse)
async def create_route(data: RouteCreate):
    try:
        route = await RouteService.create_route(data)
        return route
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.put("/routes/{route_id}", response_model=RouteResponse)
async def update_route(route_id: int, data: RouteUpdate):
    try:
        route = await RouteService.update_route(route_id, data)
        if not route:
            raise HTTPException(status_code=404, detail="工艺路线不存在")
        return route
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@base_data_router.delete("/routes/{route_id}")
async def delete_route(route_id: int):
    success = await RouteService.delete_route(route_id)
    if not success:
        raise HTTPException(status_code=404, detail="工艺路线不存在")
    return {"message": "删除成功"}

@base_data_router.get("/routes", response_model=ListResponse[RouteResponse])
async def list_routes(
    page: int = 1,
    page_size: int = 10,
    route_code: Optional[str] = None,
    route_name: Optional[str] = None,
    product_code: Optional[str] = None
):
    items, total = await RouteService.get_list(
        page=page, page_size=page_size,
        route_code=route_code,
        route_name=route_name,
        product_code=product_code
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}