"""
API密钥管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime

from base.common.response import SuccessResponse, ErrorResponse
from base.common.security import get_current_user_id
from base.plugins.llm.models.api_key import LLMApiKey

# 导入管理员权限验证
try:
    from base.plugins.llm.utils.auth import check_admin_permission
except ImportError:
    from fastapi import Depends
    async def check_admin_permission():
        return 1
from base.plugins.llm.models.provider import LLMProvider
from base.plugins.llm.schemas.llm import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse
)

api_key_router = APIRouter(
    prefix="/api-keys",
    tags=["API密钥管理"],
    dependencies=[Depends(get_current_user_id)]
)


def mask_app_key(app_key: str) -> str:
    """遮蔽App Key显示"""
    if not app_key or len(app_key) < 8:
        return "****"
    return app_key[:4] + "****" + app_key[-4:]


@api_key_router.get("", summary="获取API密钥列表")
async def get_api_keys(
    provider_id: Optional[int] = Query(None, description="厂商ID筛选"),
    model_service_type: Optional[str] = Query(None, description="服务类型筛选"),
    status: Optional[str] = Query(None, description="状态筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量")
):
    """获取API密钥列表"""
    print("\n" + "="*80)
    print("[DEBUG] ===== API Keys 列表接口被调用 =====")
    print("="*80)
    print(f"[DEBUG] 请求参数:")
    print(f"  provider_id: {provider_id}")
    print(f"  status: {status}")
    print(f"  page: {page}")
    print(f"  page_size: {page_size}")

    try:
        print(f"\n[DEBUG] 步骤 1: 创建查询")
        query = LLMApiKey.all()
        print(f"  [OK] 查询对象创建成功")

        if provider_id:
            print(f"\n[DEBUG] 步骤 2: 过滤 provider_id = {provider_id}")
            query = query.filter(provider_id=provider_id)
        if model_service_type:
            print(f"\n[DEBUG] 步骤 2.5: 过滤 model_service_type = {model_service_type}")
            query = query.filter(model_service_type=model_service_type)
        if status:
            print(f"\n[DEBUG] 步骤 3: 过滤 status = {status}")
            query = query.filter(status=status)

        print(f"\n[DEBUG] 步骤 4: 执行 count 查询")
        total = await query.count()
        print(f"  [OK] 总记录数: {total}")

        print(f"\n[DEBUG] 步骤 5: 执行分页查询 (offset={(page - 1) * page_size}, limit={page_size})")
        print(f"[DEBUG] 步骤 6: 预加载 provider 关系")
        api_keys = await query.offset((page - 1) * page_size).limit(page_size).prefetch_related('provider')
        print(f"  [OK] 查询到 {len(api_keys)} 条记录")

        # 转换为响应格式
        print(f"\n[DEBUG] 步骤 7: 转换响应格式")
        result = []
        for i, key in enumerate(api_keys, 1):
            print(f"\n[DEBUG] 处理第 {i} 条记录:")
            print(f"  ID: {key.id}")

            try:
                # 检查字段是否存在
                print(f"  检查字段 api_id: {hasattr(key, 'api_id')}")
                print(f"  检查字段 app_key: {hasattr(key, 'app_key')}")

                if not hasattr(key, 'api_id'):
                    print(f"  [ERROR] api_id 字段不存在!")
                    raise AttributeError("LLMApiKey missing api_id field")

                if not hasattr(key, 'app_key'):
                    print(f"  [ERROR] app_key 字段不存在!")
                    raise AttributeError("LLMApiKey missing app_key field")

                # 尝试访问 provider
                print(f"  检查 provider: {key.provider is not None}")
                provider_name = None
                if key.provider:
                    print(f"    provider.name: {key.provider.name}")
                    provider_name = key.provider.name

                # 获取服务类型显示名称
                from base.plugins.llm.models.enums import ModelServiceType
                service_type_display = ModelServiceType.display_name(key.model_service_type)

                record = {
                    "id": key.id,
                    "provider_id": key.provider_id,
                    "provider_name": provider_name,
                    # 服务类型（新增）
                    "model_service_type": key.model_service_type,
                    "model_service_type_display": service_type_display,
                    # 统一的认证字段
                    "api_id": key.api_id,
                    "api_key": mask_app_key(key.api_key) if key.api_key else mask_app_key(key.app_key),
                    "api_secret": mask_app_key(key.api_secret) if key.api_secret else None,
                    "access_token": key.access_token,  # 新字段
                    "endpoint_url": key.endpoint_url,
                    # 旧字段（保留用于向后兼容）
                    "app_key": mask_app_key(key.app_key),
                    "api_id_voice": key.api_id_voice,
                    "app_key_voice": mask_app_key(key.app_key_voice) if key.app_key_voice else None,
                    "api_secret_voice": mask_app_key(key.api_secret_voice) if key.api_secret_voice else None,
                    "endpoint_url_voice": key.endpoint_url_voice,
                    # 状态
                    "is_voice_service": key.is_voice_service,  # 新增
                    "has_voice_credentials": key.has_voice_credentials,  # 保留
                    # 配额和状态
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
                }

                result.append(record)
                print(f"  [OK] 记录处理成功")

            except Exception as e:
                print(f"  [ERROR] 处理记录失败: {str(e)}")
                import traceback
                traceback.print_exc()
                raise

        print(f"\n[DEBUG] 步骤 8: 构建响应")
        response_data = {
            "items": result,
            "total": total,
            "page": page,
            "page_size": page_size
        }
        print(f"  [OK] 响应数据准备完成: {len(result)} 条记录")

        print("\n" + "="*80)
        print("[DEBUG] ===== API Keys 列表接口执行成功 =====")
        print("="*80 + "\n")

        return SuccessResponse(data=response_data)

    except Exception as e:
        print("\n" + "="*80)
        print(f"[ERROR] ===== API Keys 列表接口执行失败 =====")
        print(f"错误信息: {str(e)}")
        print("="*80)
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        raise


@api_key_router.get("/{key_id}", summary="获取API密钥详情")
async def get_api_key(key_id: int):
    """获取API密钥详情"""
    key = await LLMApiKey.get_or_none(id=key_id).prefetch_related('provider')
    if not key:
        raise HTTPException(status_code=404, detail="API密钥不存在")

    # 获取服务类型显示名称
    from base.plugins.llm.models.enums import ModelServiceType
    service_type_display = ModelServiceType.display_name(key.model_service_type)

    return SuccessResponse(data={
        "id": key.id,
        "provider_id": key.provider_id,
        "provider": {
            "id": key.provider.id,
            "name": key.provider.name,
            "name_en": key.provider.name_en,
            "logo_url": key.provider.logo_url
        } if key.provider else None,
        # 服务类型（新增）
        "model_service_type": key.model_service_type,
        "model_service_type_display": service_type_display,
        # 统一的认证字段
        "api_id": key.api_id,
        "api_key": mask_app_key(key.api_key) if key.api_key else mask_app_key(key.app_key),
        "api_secret": mask_app_key(key.api_secret) if key.api_secret else None,
        "access_token": key.access_token,  # 新字段
        "endpoint_url": key.endpoint_url,
        # 旧字段（保留用于向后兼容）
        "app_key": mask_app_key(key.app_key),
        "api_id_voice": key.api_id_voice,
        "app_key_voice": mask_app_key(key.app_key_voice) if key.app_key_voice else None,
        "api_secret_voice": mask_app_key(key.api_secret_voice) if key.api_secret_voice else None,
        "endpoint_url_voice": key.endpoint_url_voice,
        # 状态
        "is_voice_service": key.is_voice_service,  # 新增
        "has_voice_credentials": key.has_voice_credentials,  # 保留
        # 配额和状态
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
async def create_api_key(
    data: ApiKeyCreate,
    user_id: int = Depends(check_admin_permission)
):
    """创建API密钥"""
    # 检查厂商是否存在
    provider = await LLMProvider.get_or_none(id=data.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="厂商不存在")

    # TODO: 加密API密钥和Secret
    # encrypted_key = encrypt_api_key(data.api_key)
    # encrypted_secret = encrypt_api_key(data.api_secret) if data.api_secret else None

    # 处理字段兼容性：优先使用新字段，如果为空则使用旧字段
    final_api_key = data.api_key or data.app_key

    api_key = await LLMApiKey.create(
        provider_id=data.provider_id,
        # 服务类型
        model_service_type=data.model_service_type,
        # 统一的认证字段
        api_id=data.api_id,
        api_key=final_api_key,
        api_secret=data.api_secret,
        access_token=data.access_token,
        endpoint_url=data.endpoint_url,
        # 旧字段（保留）
        app_key=data.app_key,
        api_id_voice=data.api_id_voice,
        app_key_voice=data.app_key_voice,
        api_secret_voice=data.api_secret_voice,
        endpoint_url_voice=data.endpoint_url_voice,
        # 其他
        max_quota=data.max_quota,
        description=data.description
    )

    return SuccessResponse(data={
        "id": api_key.id,
        "model_service_type": api_key.model_service_type,
        "api_id": api_key.api_id,
        "api_key": mask_app_key(api_key.api_key) if api_key.api_key else mask_app_key(api_key.app_key),
        "api_id_voice": api_key.api_id_voice,
        "app_key_voice": mask_app_key(api_key.app_key_voice) if api_key.app_key_voice else None,
        "provider_name": provider.name,
        "is_voice_service": api_key.is_voice_service,
        "has_voice_credentials": api_key.has_voice_credentials
    }, msg="API密钥创建成功")


@api_key_router.put("/{key_id}", summary="更新API密钥")
async def update_api_key(
    key_id: int,
    data: ApiKeyUpdate,
    user_id: int = Depends(check_admin_permission)
):
    """更新API密钥"""
    print("\n" + "="*80)
    print("[DEBUG] ===== 更新API密钥接口 =====")
    print(f"[DEBUG] key_id: {key_id}")

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
    print(f"[DEBUG] 接收到的更新数据 (exclude_unset=True):")
    for k, v in update_data.items():
        print(f"  {k}: {repr(v)}")

    # 检查语音字段是否在update_data中
    voice_fields = ['api_id_voice', 'app_key_voice', 'api_secret_voice', 'endpoint_url_voice']
    print(f"[DEBUG] 语音字段检查:")
    for field in voice_fields:
        if field in update_data:
            print(f"  ✓ {field}: {repr(update_data[field])}")
        else:
            print(f"  ✗ {field}: 不在update_data中")

    # 处理空字符串：将空字符串转换为None
    for field_name, value in list(update_data.items()):
        if value == '':
            update_data[field_name] = None
            print(f"[DEBUG] 将空字符串转换为None: {field_name}")

    # 记录更新前的值
    print(f"[DEBUG] 更新前的语音字段:")
    print(f"  api_id_voice: {repr(key.api_id_voice)}")
    print(f"  app_key_voice: {repr(key.app_key_voice)}")
    print(f"  api_secret_voice: {repr(key.api_secret_voice)}")
    print(f"  endpoint_url_voice: {repr(key.endpoint_url_voice)}")

    # 执行更新
    for field_name, value in update_data.items():
        setattr(key, field_name, value)
        print(f"[DEBUG] 设置字段: {field_name} = {repr(value)}")

    await key.save()
    print(f"[DEBUG] 数据库保存成功")

    # 记录更新后的值
    print(f"[DEBUG] 更新后的语音字段:")
    print(f"  api_id_voice: {repr(key.api_id_voice)}")
    print(f"  app_key_voice: {repr(key.app_key_voice)}")
    print(f"  api_secret_voice: {repr(key.api_secret_voice)}")
    print(f"  endpoint_url_voice: {repr(key.endpoint_url_voice)}")
    print(f"  has_voice_credentials: {key.has_voice_credentials}")

    # 准备返回数据
    response_data = {
        "id": key.id,
        "model_service_type": key.model_service_type,
        "api_id": key.api_id,
        "api_key": mask_app_key(key.api_key) if key.api_key else mask_app_key(key.app_key),
        "api_id_voice": key.api_id_voice,
        "app_key_voice": mask_app_key(key.app_key_voice) if key.app_key_voice else None,
        "api_secret_voice": mask_app_key(key.api_secret_voice) if key.api_secret_voice else None,
        "endpoint_url_voice": key.endpoint_url_voice,
        "is_voice_service": key.is_voice_service,
        "has_voice_credentials": key.has_voice_credentials
    }

    print(f"[DEBUG] 返回给前端的数据:")
    for k, v in response_data.items():
        print(f"  {k}: {repr(v)}")

    print("="*80 + "\n")

    return SuccessResponse(data=response_data, msg="API密钥更新成功")


@api_key_router.delete("/{key_id}", summary="删除API密钥")
async def delete_api_key(
    key_id: int,
    user_id: int = Depends(check_admin_permission)
):
    """删除API密钥"""
    key = await LLMApiKey.get_or_none(id=key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API密钥不存在")

    await key.delete()

    return SuccessResponse(msg="API密钥删除成功")


@api_key_router.post("/{key_id}/reset-quota", summary="重置配额")
async def reset_quota(
    key_id: int,
    user_id: int = Depends(check_admin_permission)
):
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
async def test_api_key(
    key_id: int,
    user_id: int = Depends(check_admin_permission)
):
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
