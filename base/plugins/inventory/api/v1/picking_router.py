from typing import Optional
from fastapi import APIRouter, HTTPException, Query

try:
    from base.plugins.inventory.services.inventory_service import (
        PickingService, MoveService
    )
    from base.plugins.inventory.schemas.inventory_schema import (
        StockPickingCreate, StockPickingUpdate, StockPickingResponse,
        ListResponse, MessageResponse
    )
except ImportError:
    class APIRouter:
        def __init__(self, prefix="", tags=None):
            self.prefix = prefix
            self.tags = tags or []

        def get(self, path, response_model=None):
            def decorator(func):
                return func
            return decorator

        def post(self, path, response_model=None):
            def decorator(func):
                return func
            return decorator

        def put(self, path, response_model=None):
            def decorator(func):
                return func
            return decorator

        def delete(self, path, response_model=None):
            def decorator(func):
                return func
            return decorator

    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code = status_code
            self.detail = detail

    class Query:
        def __init__(self, default=None, **kwargs):
            self.default = default

    class PickingService:
        @staticmethod
        async def get_by_id(id): return None
        @staticmethod
        async def create_picking(data): return None
        @staticmethod
        async def update_picking(id, data): return None
        @staticmethod
        async def delete_picking(id): return False
        @staticmethod
        async def confirm_picking(id): return None
        @staticmethod
        async def assign_picking(id): return None
        @staticmethod
        async def do_picking(id): return None
        @staticmethod
        async def cancel_picking(id): return None
        @staticmethod
        async def get_moves_by_picking_id(id): return []
        @staticmethod
        async def get_list(**kwargs): return [], 0

    class MoveService:
        @staticmethod
        async def get_move_lines_by_move_id(id): return []

    class StockPickingCreate: pass
    class StockPickingUpdate: pass
    class StockPickingResponse: pass
    class ListResponse: pass
    class MessageResponse: pass


router = APIRouter(prefix="/pickings", tags=["调拨单管理"])


@router.get("/{picking_id}", response_model=StockPickingResponse, summary="获取调拨单详情")
async def get_picking(picking_id: int):
    """根据ID获取调拨单详情，包含移动明细列表和move_lines"""
    picking = await PickingService.get_by_id(picking_id)
    if not picking:
        raise HTTPException(status_code=404, detail="调拨单不存在")

    moves = await PickingService.get_moves_by_picking_id(picking_id)
    moves_dict = []
    for move in moves:
        move_dict = await move.to_dict()
        move_lines = await MoveService.get_move_lines_by_move_id(move.id)
        move_dict['move_lines'] = [await line.to_dict() for line in move_lines]
        moves_dict.append(move_dict)

    picking_dict = await picking.to_dict()
    picking_dict['moves'] = moves_dict
    return picking_dict


@router.post("", response_model=StockPickingResponse, summary="创建调拨单")
async def create_picking(data: StockPickingCreate):
    """创建新调拨单，自动生成编码，可包含移动明细"""
    try:
        picking = await PickingService.create_picking(data)

        moves = await PickingService.get_moves_by_picking_id(picking.id)
        moves_dict = []
        for move in moves:
            move_dict = await move.to_dict()
            move_lines = await MoveService.get_move_lines_by_move_id(move.id)
            move_dict['move_lines'] = [await line.to_dict() for line in move_lines]
            moves_dict.append(move_dict)

        picking_dict = await picking.to_dict()
        picking_dict['moves'] = moves_dict
        return picking_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{picking_id}", response_model=StockPickingResponse, summary="更新调拨单")
async def update_picking(picking_id: int, data: StockPickingUpdate):
    """更新调拨单信息（仅draft状态）"""
    try:
        picking = await PickingService.update_picking(picking_id, data)
        if not picking:
            raise HTTPException(status_code=404, detail="调拨单不存在")

        moves = await PickingService.get_moves_by_picking_id(picking_id)
        moves_dict = [await move.to_dict() for move in moves]

        picking_dict = await picking.to_dict()
        picking_dict['moves'] = moves_dict
        return picking_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{picking_id}", response_model=MessageResponse, summary="删除调拨单")
async def delete_picking(picking_id: int):
    """删除调拨单（仅draft/cancel状态）"""
    try:
        success = await PickingService.delete_picking(picking_id)
        if not success:
            raise HTTPException(status_code=404, detail="调拨单不存在")
        return {"message": "调拨单删除成功", "success": True}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{picking_id}/confirm", response_model=StockPickingResponse, summary="确认调拨单")
async def confirm_picking(picking_id: int):
    """确认调拨单，检查库存可用性并创建预留"""
    try:
        picking = await PickingService.confirm_picking(picking_id)

        moves = await PickingService.get_moves_by_picking_id(picking_id)
        moves_dict = [await move.to_dict() for move in moves]

        picking_dict = await picking.to_dict()
        picking_dict['moves'] = moves_dict
        return picking_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{picking_id}/assign", response_model=StockPickingResponse, summary="分配库存")
async def assign_picking(picking_id: int):
    """分配库存，更新预留状态"""
    try:
        picking = await PickingService.assign_picking(picking_id)

        moves = await PickingService.get_moves_by_picking_id(picking_id)
        moves_dict = [await move.to_dict() for move in moves]

        picking_dict = await picking.to_dict()
        picking_dict['moves'] = moves_dict
        return picking_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{picking_id}/do", response_model=StockPickingResponse, summary="完成调拨单")
async def do_picking(picking_id: int):
    """完成调拨单，更新库存数量并生成交易记录"""
    try:
        picking = await PickingService.do_picking(picking_id)

        moves = await PickingService.get_moves_by_picking_id(picking_id)
        moves_dict = [await move.to_dict() for move in moves]

        picking_dict = await picking.to_dict()
        picking_dict['moves'] = moves_dict
        return picking_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{picking_id}/cancel", response_model=StockPickingResponse, summary="取消调拨单")
async def cancel_picking(picking_id: int):
    """取消调拨单，释放预留"""
    try:
        picking = await PickingService.cancel_picking(picking_id)

        moves = await PickingService.get_moves_by_picking_id(picking_id)
        moves_dict = [await move.to_dict() for move in moves]

        picking_dict = await picking.to_dict()
        picking_dict['moves'] = moves_dict
        return picking_dict
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{picking_id}/print", response_model=MessageResponse, summary="打印调拨单")
async def print_picking(picking_id: int):
    """标记调拨单为已打印"""
    picking = await PickingService.get_by_id(picking_id)
    if not picking:
        raise HTTPException(status_code=404, detail="调拨单不存在")

    picking.printed = True
    await picking.save()

    return {"message": "调拨单已标记为已打印", "success": True}


@router.get("", response_model=ListResponse, summary="获取调拨单列表")
async def list_pickings(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    picking_code: Optional[str] = Query(None, description="调拨单编码"),
    picking_type_id: Optional[int] = Query(None, description="调拨类型ID"),
    picking_type_code: Optional[str] = Query(None, description="调拨类型编码"),
    origin: Optional[str] = Query(None, description="来源单号"),
    partner_code: Optional[str] = Query(None, description="合作伙伴编码"),
    location_id: Optional[int] = Query(None, description="源库位ID"),
    location_dest_id: Optional[int] = Query(None, description="目标库位ID"),
    state: Optional[str] = Query(None, description="状态"),
    priority: Optional[str] = Query(None, description="优先级")
):
    """获取调拨单列表，支持多条件过滤"""
    items, total = await PickingService.get_list(
        page=page, page_size=page_size,
        picking_code=picking_code, picking_type_id=picking_type_id,
        picking_type_code=picking_type_code, origin=origin,
        partner_code=partner_code, location_id=location_id,
        location_dest_id=location_dest_id, state=state, priority=priority
    )

    items_dict = []
    for item in items:
        item_dict = await item.to_dict()
        moves = await PickingService.get_moves_by_picking_id(item.id)
        item_dict['moves'] = [await move.to_dict() for move in moves]
        items_dict.append(item_dict)

    return {"items": items_dict, "total": total, "page": page, "page_size": page_size}