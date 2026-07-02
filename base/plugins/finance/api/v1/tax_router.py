from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from base.common.response import SuccessResponse

tax_router = APIRouter(prefix="/tax", tags=["税务管理"])


@tax_router.get("/out", summary="获取销项发票列表")
async def get_tax_out(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    customer_id: Optional[int] = Query(None, description="客户ID"),
    period: Optional[str] = Query(None, description="期间")
):
    return {
        "total": 0,
        "page": page,
        "page_size": page_size,
        "data": []
    }


@tax_router.post("/out", summary="开具销项发票")
async def create_tax_out():
    return {"id": 1, "message": "开具成功"}


@tax_router.get("/in", summary="获取进项发票列表")
async def get_tax_in(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    supplier_id: Optional[int] = Query(None, description="供应商ID"),
    period: Optional[str] = Query(None, description="期间")
):
    return {
        "total": 0,
        "page": page,
        "page_size": page_size,
        "data": []
    }


@tax_router.post("/in", summary="录入进项发票")
async def create_tax_in():
    return {"id": 1, "message": "录入成功"}


@tax_router.post("/in/{tax_id}/verify", summary="认证进项发票")
async def verify_tax_in(tax_id: int):
    return SuccessResponse(msg="认证成功")