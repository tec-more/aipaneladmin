from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from base.common.response import SuccessResponse

general_ledger_router = APIRouter(prefix="/general-ledger", tags=["总账查询"])


@general_ledger_router.get("/", summary="获取总账列表")
async def get_general_ledger(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    account_id: Optional[int] = Query(None, description="科目ID"),
    period: Optional[str] = Query(None, description="期间")
):
    return {
        "total": 0,
        "page": page,
        "page_size": page_size,
        "data": []
    }


@general_ledger_router.get("/{account_id}", summary="获取科目总账")
async def get_account_ledger(account_id: int):
    return {
        "account_id": account_id,
        "transactions": []
    }