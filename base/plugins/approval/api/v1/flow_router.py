"""
审批流程 API 路由
"""
from fastapi import APIRouter, Depends
from base.common.security import get_current_user_id
from base.common.permissions import require_permission
from base.common.response import success_response, fail_response
from base.plugins.approval.schemas.flow_schema import FlowCreate, FlowUpdate, FlowListQuery
from base.plugins.approval.services.flow_service import FlowService

flow_router = APIRouter(prefix="/flows", tags=["审批流程"])


@flow_router.post("")
async def create_flow(
    flow_data: FlowCreate,
    user_id: int = require_permission("approval:flow:manage"),
):
    """创建审批流程"""
    try:
        flow = await FlowService.create_flow(flow_data)
        return success_response(data=await flow.to_dict(), msg="流程创建成功")
    except ValueError as e:
        return fail_response(msg=str(e))


@flow_router.post("/validate")
async def validate_flow(
    flow_data: FlowCreate,
    user_id: int = require_permission("approval:flow:view"),
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
    is_active: bool = None,
    user_id: int = require_permission("approval:flow:view"),
):
    """获取审批流程列表"""
    query = FlowListQuery(
        page=page,
        page_size=page_size,
        name=name,
        business_type=business_type,
        is_active=is_active
    )
    result = await FlowService.get_flow_list(query)
    return success_response(data=result)


@flow_router.get("/{flow_id}")
async def get_flow_detail(
    flow_id: int,
    user_id: int = require_permission("approval:flow:view"),
):
    """获取审批流程详情"""
    flow = await FlowService.get_flow(flow_id)
    if not flow:
        return fail_response(msg="流程不存在", code=404)
    return success_response(data=await flow.to_dict())


@flow_router.put("/{flow_id}")
async def update_flow(
    flow_id: int,
    flow_data: FlowUpdate,
    user_id: int = require_permission("approval:flow:manage"),
):
    """更新审批流程"""
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
    user_id: int = require_permission("approval:flow:manage"),
):
    """删除审批流程"""
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
    user_id: int = require_permission("approval:flow:manage"),
):
    """切换流程启用状态"""
    flow = await FlowService.toggle_flow_status(flow_id, is_active)
    if not flow:
        return fail_response(msg="流程不存在", code=404)
    return success_response(data=await flow.to_dict(), msg="状态更新成功")


@flow_router.get("/business-type/{business_type}")
async def get_flow_by_business_type(
    business_type: str,
    user_id: int = require_permission("approval:flow:view"),
):
    """根据业务类型获取启用的流程"""
    flow = await FlowService.get_flow_by_business_type(business_type)
    if not flow:
        return success_response(data=None, msg="未找到对应流程")
    return success_response(data=await flow.to_dict())
