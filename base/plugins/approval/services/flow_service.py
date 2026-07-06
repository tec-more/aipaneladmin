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

    # 合法的审批方式（对应 ApprovalEngine.APPROVE_*）
    VALID_APPROVE_TYPES = {"single", "or", "joint"}
    # 合法的审批人来源（对应 ApprovalEngine.get_approver_ids）
    VALID_APPROVER_TYPES = {"user", "role", "dept_head", "dynamic"}
    # 合法的节点类型
    VALID_NODE_TYPES = {"start", "approve", "condition", "fork", "join", "end"}

    @staticmethod
    def validate_flow_config(config: Dict[str, Any]) -> List[str]:
        """校验 flow_config 结构合法性，返回错误信息列表（空列表表示校验通过）。

        仅做结构校验，不触碰引擎与实例流转逻辑；plugin 启用后 engine 已能解析该结构。
        """
        if not config or not isinstance(config, dict):
            return ["流程配置不能为空"]

        nodes = config.get("nodes")
        edges = config.get("edges")
        if not isinstance(nodes, list) or not nodes:
            return ["流程配置必须包含至少一个节点"]
        if not isinstance(edges, list):
            return ["流程配置 edges 必须为数组"]

        node_ids: set = set()
        start_count = 0
        end_count = 0

        for idx, node in enumerate(nodes):
            if not isinstance(node, dict):
                return [f"第 {idx + 1} 个节点格式非法"]
            node_id = node.get("id")
            if not node_id:
                return [f"第 {idx + 1} 个节点缺少 id"]
            if node_id in node_ids:
                return [f"节点 id 重复: {node_id}"]
            node_ids.add(node_id)

            node_type = node.get("type")
            if node_type == "start":
                start_count += 1
            elif node_type == "end":
                end_count += 1
            elif node_type == "approve":
                approve_type = node.get("approve_type")
                if approve_type not in FlowService.VALID_APPROVE_TYPES:
                    return [f"审批节点 {node_id} 的审批方式(approve_type)非法: {approve_type}（应为 single/or/joint）"]
                approver_config = node.get("approver_config") or {}
                approver_type = approver_config.get("type")
                if approver_type not in FlowService.VALID_APPROVER_TYPES:
                    return [f"审批节点 {node_id} 的审批人来源(approver_config.type)非法: {approver_type}（应为 user/role/dept_head/dynamic）"]
                if approver_type == "user" and not approver_config.get("user_ids"):
                    return [f"审批节点 {node_id} 选择了「指定用户」但未选择任何用户"]
                if approver_type == "role" and not approver_config.get("role_ids"):
                    return [f"审批节点 {node_id} 选择了「按角色」但未选择任何角色"]
                # dept_head / dynamic 允许不指定部门（取申请人部门）
            elif node_type == "condition":
                if not node.get("field"):
                    return [f"条件节点 {node_id} 缺少字段(field)"]
                if not node.get("operator"):
                    return [f"条件节点 {node_id} 缺少运算符(operator)"]
                if "value" not in node:
                    return [f"条件节点 {node_id} 缺少值(value)"]
            elif node_type not in FlowService.VALID_NODE_TYPES:
                return [f"未知节点类型: {node_type}（节点 {node_id}）"]

        if start_count != 1:
            return [f"必须且只能有 1 个开始节点（当前 {start_count} 个）"]
        if end_count < 1:
            return ["至少需要 1 个结束节点"]

        for idx, edge in enumerate(edges):
            if not isinstance(edge, dict):
                return [f"第 {idx + 1} 条边格式非法"]
            source = edge.get("source")
            target = edge.get("target")
            if source not in node_ids:
                return [f"第 {idx + 1} 条边的起点(source)不存在: {source}"]
            if target not in node_ids:
                return [f"第 {idx + 1} 条边的终点(target)不存在: {target}"]

        return []

    @staticmethod
    async def create_flow(data: FlowCreate) -> ApprovalFlow:
        """创建流程"""
        # 校验流程配置结构
        errors = FlowService.validate_flow_config(data.flow_config)
        if errors:
            raise ValueError("；".join(errors))

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

        # 若本次更新包含 flow_config，先校验结构
        if data.flow_config is not None:
            errors = FlowService.validate_flow_config(data.flow_config)
            if errors:
                raise ValueError("；".join(errors))

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
