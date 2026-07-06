"""
审批流程规则 API 路由（流程本身即审批规则）
"""
from fastapi import APIRouter, Query
from base.common.security import get_current_user_id
from base.common.permissions import require_permission
from base.common.response import success_response, fail_response
from base.plugins.approval.schemas.flow_schema import FlowCreate, FlowUpdate, FlowListQuery
from base.plugins.approval.services.flow_service import FlowService

flow_router = APIRouter(prefix="/flow-rules", tags=["审批流程规则"])


@flow_router.get("/models")
async def get_available_models(
    user_id: int = require_permission("approval:flowrule:view"),
):
    """获取所有可用的业务模型（用于流程规则配置）"""
    models = FlowService.get_available_models()
    return success_response(data=models)


@flow_router.get("/actions")
async def get_model_actions(
    model: str = Query(..., description="业务模型标识"),
    user_id: int = require_permission("approval:flowrule:view"),
):
    """根据业务模型获取可配置的执行动作"""
    actions = FlowService.get_model_actions(model)
    return success_response(data=actions)


@flow_router.post("/check")
async def check_approval_required(
    payload: dict,
    user_id: int = require_permission("approval:flowrule:view"),
):
    """根据业务模型和方法检查是否需要审批（基于模型匹配）"""
    model = payload.get("model")
    method = payload.get("method", "POST")
    if not model:
        return fail_response(msg="缺少 model 参数")
    result = await FlowService.check_approval_required_by_model(model, method)
    return success_response(data=result)


@flow_router.post("")
async def create_flow(
    flow_data: FlowCreate,
    user_id: int = require_permission("approval:flowrule:manage"),
):
    """创建审批流程规则"""
    try:
        flow = await FlowService.create_flow(flow_data)
        return success_response(data=await flow.to_dict(), msg="流程创建成功")
    except ValueError as e:
        return fail_response(msg=str(e))


@flow_router.post("/validate")
async def validate_flow(
    flow_data: FlowCreate,
    user_id: int = require_permission("approval:flowrule:view"),
):
    """校验流程配置结构（不落库），供前端实时校验使用"""
    errors = FlowService.validate_flow_config(flow_data.flow_config)
    if errors:
        return success_response(data={"valid": False, "errors": errors})
    return success_response(data={"valid": True, "errors": []})


@flow_router.get("")
async def get_flow_list(
    page: int = 1,
    page_size: int = 10,
    name: str = None,
    business_type: str = None,
    model: str = None,
    action: str = None,
    is_active: bool = None,
    user_id: int = require_permission("approval:flowrule:view"),
):
    """获取审批流程规则列表"""
    query = FlowListQuery(
        page=page,
        page_size=page_size,
        name=name,
        business_type=business_type,
        model=model,
        action=action,
        is_active=is_active
    )
    result = await FlowService.get_flow_list(query)
    return success_response(data=result)


@flow_router.get("/{flow_id}")
async def get_flow_detail(
    flow_id: int,
    user_id: int = require_permission("approval:flowrule:view"),
):
    """获取审批流程规则详情"""
    flow = await FlowService.get_flow(flow_id)
    if not flow:
        return fail_response(msg="流程不存在", code=404)
    return success_response(data=await flow.to_dict())


@flow_router.put("/{flow_id}")
async def update_flow(
    flow_id: int,
    flow_data: FlowUpdate,
    user_id: int = require_permission("approval:flowrule:manage"),
):
    """更新审批流程规则"""
    try:
        flow = await FlowService.update_flow(flow_id, flow_data)
        if not flow:
            return fail_response(msg="流程不存在", code=404)
        return success_response(data=await flow.to_dict(), msg="流程更新成功")
    except ValueError as e:
        return fail_response(msg=str(e))


@flow_router.delete("/{flow_id}")
async def delete_flow(
    flow_id: int,
    user_id: int = require_permission("approval:flowrule:manage"),
):
    """删除审批流程规则"""
    try:
        success = await FlowService.delete_flow(flow_id)
        if not success:
            return fail_response(msg="流程不存在", code=404)
        return success_response(msg="流程删除成功")
    except ValueError as e:
        return fail_response(msg=str(e))


@flow_router.post("/{flow_id}/toggle")
async def toggle_flow_status(
    flow_id: int,
    is_active: bool,
    user_id: int = require_permission("approval:flowrule:manage"),
):
    """切换流程规则启用状态"""
    flow = await FlowService.toggle_flow_status(flow_id, is_active)
    if not flow:
        return fail_response(msg="流程不存在", code=404)
    return success_response(data=await flow.to_dict(), msg="状态更新成功")


@flow_router.get("/business-type/{business_type}")
async def get_flow_by_business_type(
    business_type: str,
    user_id: int = require_permission("approval:flowrule:view"),
):
    """根据业务类型获取启用的流程规则"""
    flow = await FlowService.get_flow_by_business_type(business_type)
    if not flow:
        return success_response(data=None, msg="未找到对应流程")
    return success_response(data=await flow.to_dict())
