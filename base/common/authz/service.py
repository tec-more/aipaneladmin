"""
M8 资源授权服务（ResourceGrant）

溯源：
- docs/arch/04 §6 内部接口：M3→M8 check_resource_access(owner, resource_type, resource_id) -> bool
- docs/用户侧智能体设计流PRD.md §7.2 授权矩阵（模型/知识库/工具/子Agent/节点类型）
- 模型定义见 models/resource_grant.py（T1 交付，四元组唯一约束）

默认策略（PRD §7.2）：模型仅基础可用、工具/子 Agent 默认关闭、公共知识库需显式授权。
因此本服务只做显式授权判定（存在 allow 且未过期即放行），不做任何隐式放行。
"""
from datetime import datetime, timezone
from typing import List, Optional, Sequence, Set, Tuple, Union

from .context import OwnerContext
from .models.resource_grant import ResourceGrant

# check_resource_access 接受 OwnerContext 或 (owner_type, owner_id) 二元组
OwnerLike = Union[OwnerContext, Tuple[str, int]]


def _split_owner(owner: OwnerLike) -> Tuple[str, int]:
    if isinstance(owner, OwnerContext):
        return owner.owner_type, owner.owner_id
    return owner[0], owner[1]


def _is_valid_grant(record: ResourceGrant) -> bool:
    """授权记录有效性：effect=allow 且未过期（时区安全：naive 按本地时间、aware 按 UTC 比较）"""
    if record.effect != "allow":
        return False
    if record.expires_at is None:
        return True
    expires = record.expires_at
    if expires.tzinfo is not None:
        return expires > datetime.now(timezone.utc)
    return expires > datetime.now()


class ResourceGrantService:
    """ResourceGrant 内部服务接口（T5/T6/T11 消费，禁止业务层直接拼装授权判断）"""

    @staticmethod
    async def check_resource_access(
        owner: OwnerLike,
        resource_type: str,
        resource_id: Union[str, int],
    ) -> bool:
        """
        判定主体是否已获某资源授权

        Args:
            owner: OwnerContext 或 (owner_type, owner_id)
            resource_type: model/kb/tool/agent/node_type
            resource_id: 资源标识（数值 ID 字符串形式或类型编码）

        Returns:
            存在 effect=allow 且未过期的授权记录 → True
        """
        owner_type, owner_id = _split_owner(owner)
        # 四元组唯一（T1 约束），至多一行；过期判定在 Python 侧做时区安全比较
        record = await ResourceGrant.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            resource_type=resource_type,
            resource_id=str(resource_id),
            effect="allow",
        ).first()
        return record is not None and _is_valid_grant(record)

    @staticmethod
    async def check_many(
        owner: OwnerLike,
        resource_type: str,
        resource_ids: Sequence[Union[str, int]],
    ) -> Set[str]:
        """
        批量判定（资源选择器/保存时引用校验用）

        Returns:
            已授权 resource_id 集合（字符串形式）
        """
        if not resource_ids:
            return set()
        owner_type, owner_id = _split_owner(owner)
        rows = await ResourceGrant.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            resource_type=resource_type,
            resource_id__in=[str(r) for r in resource_ids],
            effect="allow",
        )
        return {r.resource_id for r in rows if _is_valid_grant(r)}

    @staticmethod
    async def grant(
        owner: OwnerLike,
        resource_type: str,
        resource_id: Union[str, int],
        granted_by: str = "admin",
        expires_at: Optional[datetime] = None,
    ) -> ResourceGrant:
        """
        授权（幂等：四元组唯一约束，重复授权返回既有记录并刷新过期时间）

        R-06 openGauss 红线：使用 get_or_create，不使用 ON CONFLICT。
        """
        owner_type, owner_id = _split_owner(owner)
        record, created = await ResourceGrant.get_or_create(
            owner_type=owner_type,
            owner_id=owner_id,
            resource_type=resource_type,
            resource_id=str(resource_id),
            defaults={
                "effect": "allow",
                "granted_by": granted_by,
                "expires_at": expires_at,
            },
        )
        if not created:
            # 幂等重放：仅刷新元信息，不新增行
            changed = False
            if record.effect != "allow":
                record.effect = "allow"
                changed = True
            if expires_at is not None and record.expires_at != expires_at:
                record.expires_at = expires_at
                changed = True
            if changed:
                await record.save()
        return record

    @staticmethod
    async def revoke(
        owner: OwnerLike,
        resource_type: str,
        resource_id: Union[str, int],
    ) -> int:
        """
        撤销授权

        Returns:
            删除的记录数（0 表示本不存在，幂等）
        """
        owner_type, owner_id = _split_owner(owner)
        return await ResourceGrant.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            resource_type=resource_type,
            resource_id=str(resource_id),
        ).delete()

    @staticmethod
    async def list_by_subject(
        owner: OwnerLike,
        resource_type: Optional[str] = None,
        only_valid: bool = True,
    ) -> List[ResourceGrant]:
        """按主体查询授权清单（资源选择器"已授权"视图用）"""
        owner_type, owner_id = _split_owner(owner)
        query = ResourceGrant.filter(owner_type=owner_type, owner_id=owner_id)
        if resource_type:
            query = query.filter(resource_type=resource_type)
        records = await query.order_by("resource_type", "resource_id")
        if only_valid:
            records = [r for r in records if _is_valid_grant(r)]
        return records

    @staticmethod
    async def list_by_resource(
        resource_type: str,
        resource_id: Union[str, int],
    ) -> List[ResourceGrant]:
        """按资源反查被授权主体（管理侧授权管理/审计用）"""
        return await ResourceGrant.filter(
            resource_type=resource_type,
            resource_id=str(resource_id),
        ).order_by("owner_type", "owner_id")


async def check_resource_access(
    owner: OwnerLike,
    resource_type: str,
    resource_id: Union[str, int],
) -> bool:
    """模块级便捷入口（04-§6 契约签名）"""
    return await ResourceGrantService.check_resource_access(owner, resource_type, resource_id)
