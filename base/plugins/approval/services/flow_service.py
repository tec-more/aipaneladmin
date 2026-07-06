"""
流程定义 Service
"""
from typing import Optional, List, Dict, Any
from tortoise.expressions import Q
from loguru import logger

from base.plugins.approval.models.approval_flow import ApprovalFlow
from base.plugins.approval.schemas.flow_schema import FlowCreate, FlowUpdate, FlowListQuery


class FlowService:
    """审批流程定义服务"""

    @staticmethod
    async def create_flow(data: FlowCreate) -> ApprovalFlow:
        """创建流程"""
        # 检查编码是否已存在
        existing = await ApprovalFlow.get_or_none(code=data.code)
        if existing:
            raise ValueError(f"流程编码 {data.code} 已存在")

        flow = await ApprovalFlow.create(
            name=data.name,
            code=data.code,
            description=data.description,
            form_config=data.form_config,
            flow_config=data.flow_config,
            business_type=data.business_type,
            is_active=data.is_active
        )
        return flow

    @staticmethod
    async def update_flow(flow_id: int, data: FlowUpdate) -> Optional[ApprovalFlow]:
        """更新流程"""
        flow = await ApprovalFlow.get_or_none(id=flow_id)
        if not flow:
            return None

        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(flow, key, value)

        await flow.save()
        return flow

    @staticmethod
    async def delete_flow(flow_id: int) -> bool:
        """删除流程"""
        flow = await ApprovalFlow.get_or_none(id=flow_id)
        if not flow:
            return False

        if flow.is_system:
            raise ValueError("系统预设流程不可删除")

        await flow.delete()
        return True

    @staticmethod
    async def get_flow(flow_id: int) -> Optional[ApprovalFlow]:
        """获取流程"""
        return await ApprovalFlow.get_or_none(id=flow_id)

    @staticmethod
    async def get_flow_by_code(code: str) -> Optional[ApprovalFlow]:
        """根据编码获取流程"""
        return await ApprovalFlow.get_or_none(code=code)

    @staticmethod
    async def get_flow_by_business_type(business_type: str) -> Optional[ApprovalFlow]:
        """根据业务类型获取启用的流程"""
        return await ApprovalFlow.get_or_none(
            business_type=business_type,
            is_active=True
        )

    @staticmethod
    async def get_flow_list(query: FlowListQuery) -> Dict[str, Any]:
        """获取流程列表"""
        q = Q()
        if query.name:
            q &= Q(name__icontains=query.name)
        if query.business_type:
            q &= Q(business_type=query.business_type)
        if query.is_active is not None:
            q &= Q(is_active=query.is_active)

        total = await ApprovalFlow.filter(q).count()
        flows = await ApprovalFlow.filter(q).offset(
            (query.page - 1) * query.page_size
        ).limit(query.page_size)

        return {
            "total": total,
            "items": [await flow.to_dict() for flow in flows],
            "page": query.page,
            "page_size": query.page_size
        }

    @staticmethod
    async def toggle_flow_status(flow_id: int, is_active: bool) -> Optional[ApprovalFlow]:
        """切换流程启用状态"""
        flow = await ApprovalFlow.get_or_none(id=flow_id)
        if not flow:
            return None
        flow.is_active = is_active
        await flow.save()
        return flow

    @staticmethod
    async def initialize_default_data():
        """初始化默认数据"""
        # 检查是否已存在默认流程
        existing = await ApprovalFlow.get_or_none(code="default_purchase_approval")
        if existing:
            return

        # 创建采购审批默认流程
        default_flow_config = {
            "nodes": [
                {
                    "id": "start",
                    "type": "start",
                    "name": "开始",
                    "approver_config": {},
                    "approve_type": "single"
                },
                {
                    "id": "manager_approve",
                    "type": "approve",
                    "name": "部门经理审批",
                    "approver_config": {
                        "type": "dynamic",
                        "expression": "applicant.dept_head"
                    },
                    "approve_type": "single"
                },
                {
                    "id": "director_approve",
                    "type": "approve",
                    "name": "总监审批",
                    "approver_config": {
                        "type": "role",
                        "role_ids": [1]
                    },
                    "approve_type": "single"
                },
                {
                    "id": "end",
                    "type": "end",
                    "name": "结束",
                    "approver_config": {},
                    "approve_type": "single"
                }
            ],
            "edges": [
                {"source": "start", "target": "manager_approve", "type": "approve"},
                {"source": "manager_approve", "target": "director_approve", "type": "approve"},
                {"source": "director_approve", "target": "end", "type": "approve"},
                {"source": "manager_approve", "target": "end", "type": "reject"},
                {"source": "director_approve", "target": "end", "type": "reject"}
            ]
        }

        await ApprovalFlow.create(
            name="采购审批流程",
            code="default_purchase_approval",
            description="采购订单审批默认流程",
            form_config=[
                {"field": "title", "label": "标题", "type": "text", "required": True},
                {"field": "amount", "label": "金额", "type": "number", "required": True},
                {"field": "reason", "label": "事由", "type": "textarea", "required": False}
            ],
            flow_config=default_flow_config,
            business_type="purchase_order",
            is_active=True,
            is_system=True
        )
        logger.info("创建默认采购审批流程")
