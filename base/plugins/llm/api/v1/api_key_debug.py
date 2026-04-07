"""
API密钥管理API - 调试版本
添加详细的日志输出，方便调试更新接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime
import logging

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

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

api_key_debug_router = APIRouter(
    prefix="/api-keys",
    tags=["API密钥管理-调试"],
    dependencies=[Depends(get_current_user_id)]
)


def mask_app_key(app_key: str) -> str:
    """遮蔽App Key显示"""
    if not app_key or len(app_key) < 8:
        return "****"
    return app_key[:4] + "****" + app_key[-4:]


@api_key_debug_router.put("/{key_id}", summary="更新API密钥（调试版）")
async def update_api_key_debug(
    key_id: int,
    data: ApiKeyUpdate,
    user_id: int = Depends(check_admin_permission)
):
    """
    更新API密钥 - 带详细调试日志

    调试信息会输出到控制台和日志文件
    """
    print("\n" + "=" * 80)
    print("[DEBUG] ===== API Key 更新接口被调用 =====")
    print("=" * 80)
    print(f"[DEBUG] 参数:")
    print(f"  key_id: {key_id}")
    print(f"  user_id: {user_id}")

    try:
        # 步骤1: 查询API Key
        print(f"\n[DEBUG] 步骤 1: 查询API Key")
        key = await LLMApiKey.get_or_none(id=key_id)
        if not key:
            print(f"  [ERROR] API密钥不存在: {key_id}")
            raise HTTPException(status_code=404, detail="API密钥不存在")
        print(f"  [OK] 找到API Key: {key.api_id}")

        # 步骤2: 显示更新前的数据
        print(f"\n[DEBUG] 步骤 2: 更新前的数据")
        print(f"  LLM密钥:")
        print(f"    api_id: {key.api_id}")
        print(f"    app_key: {mask_app_key(key.app_key)}")
        print(f"    api_secret: {mask_app_key(key.api_secret) if key.api_secret else None}")
        print(f"    endpoint_url: {key.endpoint_url}")

        print(f"  语音密钥:")
        print(f"    api_id_voice: {key.api_id_voice}")
        print(f"    app_key_voice: {mask_app_key(key.app_key_voice) if key.app_key_voice else None}")
        print(f"    api_secret_voice: {mask_app_key(key.api_secret_voice) if key.api_secret_voice else None}")
        print(f"    endpoint_url_voice: {key.endpoint_url_voice}")

        print(f"  状态:")
        print(f"    has_voice_credentials: {key.has_voice_credentials}")

        # 步骤3: 检查provider_id
        print(f"\n[DEBUG] 步骤 3: 检查provider_id")
        if data.provider_id is not None:
            print(f"  provider_id in request: {data.provider_id}")
            provider = await LLMProvider.get_or_none(id=data.provider_id)
            if not provider:
                print(f"  [ERROR] 厂商不存在: {data.provider_id}")
                raise HTTPException(status_code=404, detail="厂商不存在")
            print(f"  [OK] 厂商存在: {provider.name}")
        else:
            print(f"  provider_id: 未提供（不更新）")

        # 步骤4: 获取更新数据
        print(f"\n[DEBUG] 步骤 4: 获取更新数据")
        update_data = data.model_dump(exclude_unset=True)
        print(f"  update_data (exclude_unset=True):")
        print(f"    {update_data}")

        print(f"\n  详细字段检查:")
        all_fields = [
            'provider_id', 'api_id', 'app_key', 'api_secret', 'endpoint_url',
            'api_id_voice', 'app_key_voice', 'api_secret_voice', 'endpoint_url_voice',
            'max_quota', 'description'
        ]

        for field in all_fields:
            if field in update_data:
                value = update_data[field]
                display_value = value
                if 'key' in field or 'secret' in field:
                    if value:
                        display_value = mask_app_key(value) if len(value) > 8 else '****'
                print(f"    ✓ {field}: {display_value}")
            else:
                print(f"    - {field}: [未提供]")

        # 步骤5: 处理空字符串
        print(f"\n[DEBUG] 步骤 5: 处理空字符串")
        empty_fields = []
        for field_name, value in list(update_data.items()):
            if value == '':
                print(f"  检测到空字符串: {field_name}")
                update_data[field_name] = None
                empty_fields.append(field_name)

        if empty_fields:
            print(f"  已将以下字段从空字符串转为None: {empty_fields}")
        else:
            print(f"  无空字符串需要处理")

        # 步骤6: 执行更新
        print(f"\n[DEBUG] 步骤 6: 执行更新")
        updated_fields = []
        for field_name, value in update_data.items():
            old_value = getattr(key, field_name, None)
            print(f"  更新 {field_name}:")
            print(f"    旧值: {old_value}")
            print(f"    新值: {value}")
            setattr(key, field_name, value)
            updated_fields.append(field_name)

        print(f"  共更新 {len(updated_fields)} 个字段")

        # 步骤7: 保存到数据库
        print(f"\n[DEBUG] 步骤 7: 保存到数据库")
        await key.save()
        print(f"  [OK] 数据库保存成功")

        # 步骤8: 重新查询验证
        print(f"\n[DEBUG] 步骤 8: 验证更新结果")
        await key.refresh_from_db()

        print(f"  更新后的数据:")
        print(f"    api_id_voice: {key.api_id_voice}")
        print(f"    app_key_voice: {mask_app_key(key.app_key_voice) if key.app_key_voice else None}")
        print(f"    api_secret_voice: {mask_app_key(key.api_secret_voice) if key.api_secret_voice else None}")
        print(f"    endpoint_url_voice: {key.endpoint_url_voice}")
        print(f"    has_voice_credentials: {key.has_voice_credentials}")

        # 步骤9: 构建响应
        print(f"\n[DEBUG] 步骤 9: 构建响应")
        response_data = {
            "id": key.id,
            "api_id": key.api_id,
            "app_key": mask_app_key(key.app_key),
            "api_id_voice": key.api_id_voice,
            "app_key_voice": mask_app_key(key.app_key_voice) if key.app_key_voice else None,
            "has_voice_credentials": key.has_voice_credentials
        }

        print(f"  响应数据: {response_data}")

        print("\n" + "=" * 80)
        print("[DEBUG] ===== API Key 更新成功 =====")
        print("=" * 80 + "\n")

        return SuccessResponse(data=response_data, msg="API密钥更新成功")

    except HTTPException:
        raise
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"[ERROR] ===== API Key 更新失败 =====")
        print(f"错误信息: {str(e)}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        print("=" * 80 + "\n")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")
