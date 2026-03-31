"""
使用统计管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta

from base.common.response import SuccessResponse
from base.common.security import get_current_user_id
from base.plugins.llm.models.usage import LLMUsage

# 导入管理员权限验证
try:
    from base.plugins.llm.utils.auth import check_admin_permission
except ImportError:
    from fastapi import Depends
    async def check_admin_permission():
        return 1
from base.plugins.llm.models.conversation import LLMConversation

usage_router = APIRouter(
    prefix="/usage",
    tags=["使用统计管理"],
    dependencies=[Depends(check_admin_permission)]
)


@usage_router.get("/records", summary="获取使用记录列表")
async def get_usage_records(
    customer_id: Optional[int] = Query(None, description="客户ID筛选"),
    model_id: Optional[int] = Query(None, description="模型ID筛选"),
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取使用记录列表"""
    query = LLMUsage.all()

    if customer_id:
        query = query.filter(customer_id=customer_id)
    if model_id:
        query = query.filter(model_id=model_id)
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(created_at__gte=start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(created_at__lt=end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误")

    total = await query.count()
    usages = await query.offset((page - 1) * page_size).limit(page_size).order_by('-created_at')

    result = []
    for usage in usages:
        result.append({
            "id": usage.id,
            "conversation_id": usage.conversation_id,
            "model_id": usage.model_id,
            "customer_id": usage.customer_id,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "cost": float(usage.cost),
            "created_at": usage.created_at.isoformat() if usage.created_at else None
        })

    return SuccessResponse(data={
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@usage_router.get("/statistics", summary="获取使用统计")
async def get_usage_statistics(
    customer_id: Optional[int] = Query(None, description="客户ID筛选"),
    model_id: Optional[int] = Query(None, description="模型ID筛选"),
    days: int = Query(7, ge=1, le=90, description="统计天数")
):
    """获取使用统计"""
    start_date = datetime.now() - timedelta(days=days)

    query = LLMUsage.filter(created_at__gte=start_date)

    if customer_id:
        query = query.filter(customer_id=customer_id)
    if model_id:
        query = query.filter(model_id=model_id)

    # 获取所有记录后手动计算统计
    usages = await query
    total_records = len(usages)

    total_tokens = sum(u.total_tokens for u in usages)
    total_prompt_tokens = sum(u.prompt_tokens for u in usages)
    total_completion_tokens = sum(u.completion_tokens for u in usages)
    total_cost = sum(float(u.cost) for u in usages)

    return SuccessResponse(data={
        "period_days": days,
        "total_records": total_records,
        "total_tokens": total_tokens,
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_cost": total_cost,
        "average_tokens_per_request": int(total_tokens / total_records) if total_records > 0 else 0
    })


@usage_router.get("/statistics/daily", summary="获取每日使用统计")
async def get_daily_statistics(
    customer_id: Optional[int] = Query(None, description="客户ID筛选"),
    days: int = Query(7, ge=1, le=30, description="统计天数")
):
    """获取每日使用统计"""
    start_date = datetime.now() - timedelta(days=days)

    # 获取记录后按日期分组
    query = LLMUsage.filter(created_at__gte=start_date)

    if customer_id:
        query = query.filter(customer_id=customer_id)

    usages = await query.order_by('created_at')

    # 按日期分组统计
    daily_stats = {}
    for usage in usages:
        date_key = usage.created_at.strftime('%Y-%m-%d')
        if date_key not in daily_stats:
            daily_stats[date_key] = {
                "date": date_key,
                "request_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }
        daily_stats[date_key]["request_count"] += 1
        daily_stats[date_key]["total_tokens"] += usage.total_tokens
        daily_stats[date_key]["total_cost"] += float(usage.cost)

    # 转换为列表并排序
    result = sorted(daily_stats.values(), key=lambda x: x["date"])

    return SuccessResponse(data={
        "period_days": days,
        "daily_stats": result
    })


@usage_router.get("/statistics/model", summary="获取模型使用统计")
async def get_model_statistics(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)")
):
    """获取各模型使用统计排名"""
    query = LLMUsage.all()

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(created_at__gte=start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(created_at__lt=end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误")

    usages = await query

    # 按模型分组统计
    model_stats = {}
    for usage in usages:
        model_id = usage.model_id
        if model_id not in model_stats:
            model_stats[model_id] = {
                "model_id": model_id,
                "request_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }
        model_stats[model_id]["request_count"] += 1
        model_stats[model_id]["total_tokens"] += usage.total_tokens
        model_stats[model_id]["total_cost"] += float(usage.cost)

    # 排序并返回
    result = sorted(model_stats.values(), key=lambda x: x["total_tokens"], reverse=True)

    return SuccessResponse(data={
        "model_stats": result
    })


@usage_router.get("/statistics/customer", summary="获取客户使用统计")
async def get_customer_statistics(
    start_date: Optional[str] = Query(None, description="开始日期 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="结束日期 (YYYY-MM-DD)"),
    top_n: int = Query(10, ge=1, le=100, description="返回前N名")
):
    """获取客户使用统计排名"""
    query = LLMUsage.all()

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(created_at__gte=start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="开始日期格式错误")
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(created_at__lt=end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="结束日期格式错误")

    usages = await query

    # 按客户分组统计
    customer_stats = {}
    for usage in usages:
        customer_id = usage.customer_id
        if customer_id not in customer_stats:
            customer_stats[customer_id] = {
                "customer_id": customer_id,
                "request_count": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            }
        customer_stats[customer_id]["request_count"] += 1
        customer_stats[customer_id]["total_tokens"] += usage.total_tokens
        customer_stats[customer_id]["total_cost"] += float(usage.cost)

    # 排序并返回前N名
    result = sorted(customer_stats.values(), key=lambda x: x["total_tokens"], reverse=True)[:top_n]

    return SuccessResponse(data={
        "top_n": top_n,
        "customer_stats": result
    })
