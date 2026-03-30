"""
厂商管理API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from base.common.response import SuccessResponse, ErrorResponse
from base.plugins.llm.models.provider import LLMProvider
from base.plugins.llm.schemas.llm import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse
)

provider_router = APIRouter(prefix="/providers", tags=["厂商管理"])


@provider_router.get("", summary="获取厂商列表")
async def get_providers(
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取厂商列表"""
    query = LLMProvider.all()

    if status:
        query = query.filter(status=status)

    total = await query.count()
    providers = await query.offset((page - 1) * page_size).limit(page_size)

    # 转换为响应格式
    result = []
    for provider in providers:
        result.append({
            "id": provider.id,
            "name": provider.name,
            "name_en": provider.name_en,
            "logo_url": provider.logo_url,
            "official_url": provider.official_url,
            "status": provider.status,
            "description": provider.description,
            "created_at": provider.created_at.isoformat() if provider.created_at else None,
            "updated_at": provider.updated_at.isoformat() if provider.updated_at else None
        })

    return SuccessResponse(data={
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@provider_router.get("/{provider_id}", summary="获取厂商详情")
async def get_provider(provider_id: int):
    """获取厂商详情"""
    provider = await LLMProvider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")

    return SuccessResponse(data={
        "id": provider.id,
        "name": provider.name,
        "name_en": provider.name_en,
        "logo_url": provider.logo_url,
        "official_url": provider.official_url,
        "status": provider.status,
        "description": provider.description,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
        "updated_at": provider.updated_at.isoformat() if provider.updated_at else None
    })


@provider_router.post("", summary="创建厂商")
async def create_provider(data: ProviderCreate):
    """创建厂商"""
    # 检查名称是否重复
    existing = await LLMProvider.get_or_none(name=data.name)
    if existing:
        raise HTTPException(status_code=400, detail="厂商名称已存在")

    existing_en = await LLMProvider.get_or_none(name_en=data.name_en)
    if existing_en:
        raise HTTPException(status_code=400, detail="英文标识已存在")

    provider = await LLMProvider.create(**data.model_dump())

    return SuccessResponse(data={
        "id": provider.id,
        "name": provider.name,
        "name_en": provider.name_en,
        "status": provider.status
    }, msg="厂商创建成功")


@provider_router.put("/{provider_id}", summary="更新厂商")
async def update_provider(provider_id: int, data: ProviderUpdate):
    """更新厂商"""
    provider = await LLMProvider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")

    # 只更新提供的字段
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)

    await provider.save()

    return SuccessResponse(data={
        "id": provider.id,
        "name": provider.name,
        "name_en": provider.name_en
    }, msg="厂商更新成功")


@provider_router.delete("/{provider_id}", summary="删除厂商")
async def delete_provider(provider_id: int):
    """删除厂商"""
    provider = await LLMProvider.get_or_none(id=provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")

    await provider.delete()

    return SuccessResponse(msg="厂商删除成功")
