"""
API密钥管理API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from base.common.response import SuccessResponse, ErrorResponse
from base.plugins.llm.models.api_key import LLMApiKey
from base.plugins.llm.models.provider import LLMProvider
from base.plugins.llm.schemas.llm import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse
)

api_key_router = APIRouter(prefix="/api-keys", tags=["API密钥管理"])


def mask_api_key(api_key: str) -> str:
    """遮蔽API密钥显示"""
    if not api_key or len(api_key) < 8:
        return "****"
    return api_key[:4] + "****" + api_key[-4:]


@api_key_router.get("", summary="获取API密钥列表")
async def get_api_keys(
    provider_id: Optional[int] = Query(None, description="厂商ID筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取API密钥列表"""
    query = LLMApiKey.all()

    if provider_id:
        query = query.filter(provider_id=provider_id)
    if status:
        query = query.filter(status=status)

    total = await query.count()
    api_keys = await query.offset((page - 1) * page_size).limit(page_size).prefetch_related('provider')

    # 转换为响应格式
    result = []
    for key in api_keys:
        result.append({
            "id": key.id,
            "provider_id": key.provider_id,
            "provider_name": key.provider.name if key.provider else None,
            "name": key.name,
            "api_key": mask_api_key(key.api_key),
            "api_secret": mask_api_key(key.api_secret) if key.api_secret else None,
            "endpoint_url": key.endpoint_url,
            "max_quota": key.max_quota,
            "used_quota": key.used_quota,
            "remaining_quota": key.remaining_quota,
            "is_available": key.is_available,
            "status": key.status,
            "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
            "expires_at": key.expires_at.isoformat() if key.expires_at else None,
            "description": key.description,
            "created_at": key.created_at.isoformat() if key.created_at else None,
            "updated_at": key.updated_at.isoformat() if key.updated_at else None
        })

    return SuccessResponse(data={
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })


@api_key_router.get("/{key_id}", summary="获取API密钥详情")
async def get_api_key(key_id: int):
    """获取API密钥详情"""
    key = await LLMApiKey.get_or_none(id=key_id).prefetch_related('provider')
    if not key:
        raise HTTPException(status_code=404, detail="API密钥不存在")

    return SuccessResponse(data={
        "id": key.id,
        "provider_id": key.provider_id,
        "provider": {
            "id": key.provider.id,
            "name": key.provider.name,
            "name_en": key.provider.name_en,
            "logo_url": key.provider.logo_url
        } if key.provider else None,
        "name": key.name,
        "api_key": mask_api_key(key.api_key),
        "api_secret": mask_api_key(key.api_secret) if key.api_secret else None,
        "endpoint_url": key.endpoint_url,
        "max_quota": key.max_quota,
        "used_quota": key.used_quota,
        "remaining_quota": key.remaining_quota,
        "is_available": key.is_available,
        "status": key.status,
        "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
        "expires_at": key.expires_at.isoformat() if key.expires_at else None,
        "quota_reset_date": key.quota_reset_date.isoformat() if key.quota_reset_date else None,
        "description": key.description,
        "created_at": key.created_at.isoformat() if key.created_at else None,
        "updated_at": key.updated_at.isoformat() if key.updated_at else None
    })


@api_key_router.post("", summary="创建API密钥")
async def create_api_key(data: ApiKeyCreate):
    """创建API密钥"""
    # 检查厂商是否存在
    provider = await LLMProvider.get_or_none(id=data.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")

    # TODO: 加密API密钥和Secret
    # encrypted_key = encrypt_api_key(data.api_key)
    # encrypted_secret = encrypt_api_key(data.api_secret) if data.api_secret else None

    api_key = await LLMApiKey.create(
        provider_id=data.provider_id,
        name=data.name,
        api_key=data.api_key,  # 实际应该存加密后的
        api_secret=data.api_secret,  # 实际应该存加密后的
        endpoint_url=data.endpoint_url,
        max_quota=data.max_quota,
        description=data.description
    )

    return SuccessResponse(data={
        "id": api_key.id,
        "name": api_key.name,
        "api_key": mask_api_key(api_key.api_key),
        "provider_name": provider.name
    }, msg="API密钥创建成功")


@api_key_router.put("/{key_id}", summary="更新API密钥")
async def update_api_key(key_id: int, data: ApiKeyUpdate):
    """更新API密钥"""
    key = await LLMApiKey.get_or_none(id=key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API密钥不存在")

    # 如果更新provider_id，检查新厂商是否存在
    if data.provider_id is not None:
        provider = await LLMProvider.get_or_none(id=data.provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="厂商不存在")

    # 只更新提供的字段
    update_data = data.model_dump(exclude_unset=True)

    # TODO: 如果更新了api_key或api_secret，需要加密
    # if 'api_key' in update_data:
    #     update_data['api_key'] = encrypt_api_key(update_data['api_key'])
    # if 'api_secret' in update_data and update_data['api_secret']:
    #     update_data['api_secret'] = encrypt_api_key(update_data['api_secret'])

    for field_name, value in update_data.items():
        setattr(key, field_name, value)

    await key.save()

    return SuccessResponse(data={
        "id": key.id,
        "name": key.name,
        "api_key": mask_api_key(key.api_key)
    }, msg="API密钥更新成功")


@api_key_router.delete("/{key_id}", summary="删除API密钥")
async def delete_api_key(key_id: int):
    """删除API密钥"""
    key = await LLMApiKey.get_or_none(id=key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API密钥不存在")

    await key.delete()

    return SuccessResponse(msg="API密钥删除成功")


@api_key_router.post("/{key_id}/reset-quota", summary="重置配额")
async def reset_quota(key_id: int):
    """重置API密钥配额"""
    key = await LLMApiKey.get_or_none(id=key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API密钥不存在")

    await key.reset_quota_if_needed()

    return SuccessResponse(data={
        "used_quota": key.used_quota,
        "remaining_quota": key.remaining_quota
    }, msg="配额重置成功")


@api_key_router.get("/{key_id}/test", summary="测试API密钥")
async def test_api_key(key_id: int):
    """测试API密钥是否可用"""
    key = await LLMApiKey.get_or_none(id=key_id).prefetch_related('provider')
    if not key:
        raise HTTPException(status_code=404, detail="API密钥不存在")

    # 检查基础状态
    if not key.is_available:
        reason = []
        if key.status != "active":
            reason.append("状态未激活")
        if key.expires_at and key.expires_at < datetime.now():
            reason.append("已过期")
        if key.max_quota > 0 and key.used_quota >= key.max_quota:
            reason.append("配额已用尽")

        return SuccessResponse(data={
            "available": False,
            "reason": ", ".join(reason),
            "remaining_quota": key.remaining_quota
        })

    # TODO: 实际调用厂商API进行连通性测试
    # 可以根据不同厂商发送简单的测试请求

    return SuccessResponse(data={
        "available": True,
        "remaining_quota": key.remaining_quota,
        "message": "API密钥可用"
    })
