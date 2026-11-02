"""
管理侧资源授权管理 API

溯源：T11 节点2 §3 接口契约；T11 节点1 Q1/Q2 裁定（仅 API，无后台 UI）。
鉴权：require_superuser（沿用 T3/quota admin 惯例）。

职责：发放/撤销/反查资源授权。授权四元组唯一（T1 约束），grant/revoke 幂等。
审计：grant/revoke 写 audit（R-B 越权与操作留痕）。
"""
from typing import Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from base.common.authz.service import ResourceGrantService
from base.common.permissions import require_superuser
from base.common.response import fail_response, success_response

router = APIRouter(prefix="/admin/grants", tags=["资源授权管理"])

RESOURCE_TYPES = ("model", "kb", "tool", "agent", "node_type")


class GrantSchema(BaseModel):
    owner_type: str = Field(..., description="主体类型: cus/usr")
    owner_id: int = Field(..., gt=0, description="主体 ID")
    resource_type: str = Field(..., description="资源类型")
    resource_id: str = Field(..., min_length=1, max_length=100, description="资源 ID")
    expires_at: Optional[str] = Field(None, description="过期时间 ISO（可选）")


def _valid_type(resource_type: str) -> bool:
    return resource_type in RESOURCE_TYPES


def _parse_expires(expires_at: Optional[str]):
    if not expires_at:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(expires_at)
    except (ValueError, TypeError):
        return None


def _grant_to_dict(record) -> dict:
    return {
        "id": record.id,
        "owner_type": record.owner_type,
        "owner_id": record.owner_id,
        "resource_type": record.resource_type,
        "resource_id": record.resource_id,
        "effect": getattr(record, "effect", "allow"),
        "granted_by": getattr(record, "granted_by", ""),
        "expires_at": record.expires_at.isoformat() if getattr(record, "expires_at", None) else None,
    }


@router.post("", summary="发放授权（幂等）")
async def grant_resource(data: GrantSchema, admin_id: int = require_superuser()):
    if not _valid_type(data.resource_type):
        return fail_response(msg=f"非法资源类型: {data.resource_type}")
    record = await ResourceGrantService.grant(
        (data.owner_type, data.owner_id),
        resource_type=data.resource_type,
        resource_id=data.resource_id,
        granted_by=f"admin:{admin_id}",
        expires_at=_parse_expires(data.expires_at),
    )
    # 审计：ResourceGrant 的 ORM create/update 由审计插件 orm_event_service 自动捕获
    return success_response(data=_grant_to_dict(record), msg="授权成功")


@router.delete("", summary="撤销授权（幂等）")
async def revoke_resource(data: GrantSchema, admin_id: int = require_superuser()):
    if not _valid_type(data.resource_type):
        return fail_response(msg=f"非法资源类型: {data.resource_type}")
    deleted = await ResourceGrantService.revoke(
        (data.owner_type, data.owner_id),
        resource_type=data.resource_type,
        resource_id=data.resource_id,
    )
    return success_response(data={"deleted": deleted}, msg="撤销成功" if deleted else "记录本不存在")


@router.get("", summary="按资源反查被授权主体")
async def list_grants_by_resource(
    resource_type: str = Query(...),
    resource_id: str = Query(...),
    admin_id: int = require_superuser(),
):
    if not _valid_type(resource_type):
        return fail_response(msg=f"非法资源类型: {resource_type}")
    records = await ResourceGrantService.list_by_resource(resource_type, resource_id)
    return success_response(data={"items": [_grant_to_dict(r) for r in records]})
