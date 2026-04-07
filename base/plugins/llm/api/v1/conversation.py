"""
对话记录管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from base.common.response import SuccessResponse
from base.common.security import get_current_user_id
from base.plugins.llm.models.usage import LLMUsageRecord

# 导入管理员权限验证
try:
    from base.plugins.llm.utils.auth import check_admin_permission
except ImportError:
    from fastapi import Depends
    async def check_admin_permission():
        return 1

conversation_router = APIRouter(
    prefix="/conversations",
    tags=["对话记录管理"],
    dependencies=[Depends(check_admin_permission)]
)


@conversation_router.get("", summary="获取对话列表")
async def get_conversations(
    customer_id: Optional[int] = Query(None, description="客户ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取对话列表"""
    query = LLMUsageRecord.filter(record_type="conversation")

    if customer_id:
        query = query.filter(customer_id=customer_id)
    if status:
        query = query.filter(status=status)

    total = await query.count()
    conversations = await query.offset((page - 1) * page_size).limit(page_size).order_by('-created_at')

    # 转换为响应格式
    result = []
    for conv in conversations:
        result.append({
            "id": conv.id,
            "conversation_id": conv.conversation_id,
            "customer_id": conv.customer_id,
            "model_id": conv.model_id,
            "input_text": conv.input_text,
            "output_text": conv.output_text,
            "tokens": conv.tokens,
            "cost": float(conv.cost),
            "status": conv.status,
            "created_at": conv.created_at.isoformat() if conv.created_at else None
        })

    return SuccessResponse(data={
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@conversation_router.get("/{conversation_id}/usage", summary="获取对话使用记录")
async def get_conversation_usage(
    conversation_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取对话的使用记录"""
    query = LLMUsageRecord.filter(conversation_id=conversation_id, record_type="conversation")
    total = await query.count()
    usages = await query.offset((page - 1) * page_size).limit(page_size).order_by('-created_at')

    result = []
    for usage in usages:
        result.append({
            "id": usage.id,
            "model_id": usage.model_id,
            "input_text": usage.input_text,
            "output_text": usage.output_text,
            "tokens": usage.tokens,
            "cost": float(usage.cost),
            "status": usage.status,
            "created_at": usage.created_at.isoformat() if usage.created_at else None
        })

    return SuccessResponse(data={
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@conversation_router.get("/{conversation_id}/summary", summary="获取对话统计汇总")
async def get_conversation_summary(conversation_id: str):
    """获取对话的统计汇总"""
    # 聚合统计
    usages = await LLMUsageRecord.filter(conversation_id=conversation_id, record_type="conversation")

    total_tokens = sum(u.tokens for u in usages)
    total_requests = len(usages)
    total_usage_cost = sum(float(u.cost) for u in usages)

    return SuccessResponse(data={
        "conversation_id": conversation_id,
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "total_cost": total_usage_cost,
        "average_tokens_per_request": total_tokens // total_requests if total_requests > 0 else 0
    })
