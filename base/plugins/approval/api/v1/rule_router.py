"""
审批规则 API 路由
"""
from fastapi import APIRouter, Depends
from base.common.security import get_current_user_id
from base.common.permissions import require_permission
from base.common.response import success_response, fail_response
from base.plugins.approval.schemas.rule_schema import RuleCreate, RuleUpdate, RuleListQuery
from base.plugins.approval.services.rule_service import RuleService

rule_router = APIRouter(prefix="/rules", tags=["审批规则"])


@rule_router.post("")
async def create_rule(
    rule_data: RuleCreate,
    user_id: int = require_permission("approval:rule:manage"),
):
    """创建审批规则"""
    try:
        rule = await RuleService.create_rule(rule_data)
        return success_response(data=await rule.to_dict(), msg="规则创建成功")
    except ValueError as e:
        return fail_response(msg=str(e))


@rule_router.get("")
async def get_rule_list(
    page: int = 1,
    page_size: int = 10,
    business_type: str = None,
    is_active: bool = None,
    user_id: int = require_permission("approval:rule:view"),
):
    """获取审批规则列表"""
    query = RuleListQuery(
        page=page,
        page_size=page_size,
        business_type=business_type,
        is_active=is_active
    )
    result = await RuleService.get_rule_list(query)
    return success_response(data=result)


@rule_router.get("/{rule_id}")
async def get_rule_detail(
    rule_id: int,
    user_id: int = require_permission("approval:rule:view"),
):
    """获取审批规则详情"""
    rule = await RuleService.get_rule(rule_id)
    if not rule:
        return fail_response(msg="规则不存在", code=404)
    return success_response(data=await rule.to_dict())


@rule_router.put("/{rule_id}")
async def update_rule(
    rule_id: int,
    rule_data: RuleUpdate,
    user_id: int = require_permission("approval:rule:manage"),
):
    """更新审批规则"""
    try:
        rule = await RuleService.update_rule(rule_id, rule_data)
        if not rule:
            return fail_response(msg="规则不存在", code=404)
        return success_response(data=await rule.to_dict(), msg="规则更新成功")
    except ValueError as e:
        return fail_response(msg=str(e))


@rule_router.delete("/{rule_id}")
async def delete_rule(
    rule_id: int,
    user_id: int = require_permission("approval:rule:manage"),
):
    """删除审批规则"""
    success = await RuleService.delete_rule(rule_id)
    if not success:
        return fail_response(msg="规则不存在", code=404)
    return success_response(msg="规则删除成功")


@rule_router.post("/check")
async def check_approval_required(
    model: str = None,
    path: str = None,
    method: str = "POST",
    user_id: int = require_permission("approval:rule:view"),
):
    """检查指定模型（或路径）和方法是否需要审批；优先按模型匹配"""
    if model:
        result = await RuleService.check_approval_required_by_model(model, method)
    else:
        result = await RuleService.check_approval_required(path, method)
    return success_response(data=result)


@rule_router.post("/{rule_id}/toggle")
async def toggle_rule_status(
    rule_id: int,
    is_active: bool,
    user_id: int = require_permission("approval:rule:manage"),
):
    """切换规则启用状态"""
    rule = await RuleService.toggle_rule_status(rule_id, is_active)
    if not rule:
        return fail_response(msg="规则不存在", code=404)
    return success_response(data=await rule.to_dict(), msg="状态更新成功")
