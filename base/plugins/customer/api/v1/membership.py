"""
会员相关 API
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from base.common.response import success_response, fail_response
from base.plugins.customer.schemas import (
    MembershipLevelOut,
    FibonacciLevelOut,
    MembershipLevelIn
)
from base.plugins.customer.services.membership_service import MembershipService
from base.core.users.models.users import User
from base.common.security import get_current_user

membership_router = APIRouter(prefix="/membership", tags=["客户会员"])


async def get_or_create_customer(user: User) -> "Customer":
    """获取或创建客户记录"""
    from base.plugins.customer.models.customer import Customer

    # 首先通过system_user关联查找
    customer = await Customer.get_or_none(system_user_id=user.id)

    if not customer:
        # 如果没找到，尝试通过email查找
        customer = await Customer.get_or_none(email=user.email)

        if not customer:
            # 如果还是没找到，创建新的客户记录
            customer = await Customer.create(
                system_user_id=user.id,
                username=user.username,
                email=user.email,
                nickname=getattr(user, "nickname", None),
                avatar=getattr(user, "avatar", None),
                is_active=True
            )
        else:
            # 如果通过email找到了，更新关联
            customer.system_user_id = user.id
            await customer.save()

    return customer


@membership_router.get("/levels", response_model=List[MembershipLevelOut], summary="获取会员等级列表")
async def get_membership_levels(
    active_only: bool = True
):
    """
    获取所有可用的会员等级

    参数：
    - active_only: 只显示启用的等级（默认True）

    返回：
    - 会员等级列表
    - 包含价格、时长、特权等信息
    """
    levels = await MembershipService.get_all_levels(active_only=active_only)
    return success_response(data=levels)


@membership_router.get("/fibonacci-level", summary="计算Fibonacci等级")
async def calculate_fibonacci_level(
    hours: int = Query(..., ge=0, description="总充值小时数")
):
    """
    根据充值小时数计算Fibonacci等级

    返回：
    - 当前等级
    - 下一等级需要的小时数
    - 距离下一等级还差多少小时
    - 当前等级特权列表
    """
    result = await MembershipService.calculate_fibonacci_level(hours)
    return success_response(data=result)


@membership_router.get("/my-level", summary="获取我的会员等级")
async def get_my_membership_level(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的会员等级信息

    包含：
    - 会员等级详情
    - Fibonacci等级计算
    - 特权列表
    """
    customer = await get_or_create_customer(current_user)

    membership = await MembershipService.get_customer_membership(customer.id)

    if not membership:
        return success_response(data={
            "message": "暂未开通会员",
            "level": 0
        })

    # 计算Fibonacci等级
    fibonacci_info = await MembershipService.calculate_fibonacci_level(membership.total_hours)

    return success_response(data={
        "membership": membership,
        "fibonacci_level": fibonacci_info
    })


@membership_router.post("/levels", summary="创建会员等级")
async def create_membership_level(
    level_data: MembershipLevelIn,
    current_user: User = Depends(get_current_user)
):
    """
    创建会员等级

    管理员功能
    """
    try:
        # 将 Pydantic 模型转换为字典
        level_dict = level_data.model_dump()

        level = await MembershipService.create_level(level_dict)

        # 转换为字典确保datetime字段被正确格式化
        if hasattr(level, 'to_dict'):
            level_dict = await level.to_dict()
        elif hasattr(level, 'dict'):
            level_dict = level.dict()
        else:
            level_dict = dict(level)

        return success_response(data=level_dict, msg="会员等级创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@membership_router.put("/levels/{level_id}", summary="更新会员等级")
async def update_membership_level(
    level_id: int,
    level_data: MembershipLevelIn,
    current_user: User = Depends(get_current_user)
):
    """
    更新会员等级

    管理员功能
    """
    try:
        # 将 Pydantic 模型转换为字典
        update_dict = level_data.model_dump(exclude_unset=True)

        level = await MembershipService.update_level(level_id, update_dict)

        if not level:
            return fail_response(msg="会员等级不存在")

        # 转换为字典确保datetime字段被正确格式化
        if hasattr(level, 'to_dict'):
            level_dict = await level.to_dict()
        elif hasattr(level, 'dict'):
            level_dict = level.dict()
        else:
            level_dict = dict(level)

        return success_response(data=level_dict, msg="会员等级更新成功")
    except Exception as e:
        return fail_response(msg=str(e))


@membership_router.delete("/levels/{level_id}", summary="删除会员等级")
async def delete_membership_level(
    level_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    删除会员等级

    管理员功能
    """
    try:
        success = await MembershipService.delete_level(level_id)
        if not success:
            return fail_response(msg="会员等级不存在")
        return success_response(msg="会员等级删除成功")
    except Exception as e:
        return fail_response(msg=str(e))


@membership_router.patch("/levels/{level_id}", summary="切换会员等级状态")
async def toggle_membership_level_status(
    level_id: int,
    status_data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """
    切换会员等级启用状态

    管理员功能
    """
    try:
        if status_data is None:
            status_data = {}

        is_active = status_data.get("is_active", True)
        level = await MembershipService.update_level(level_id, {"is_active": is_active})

        if not level:
            return fail_response(msg="会员等级不存在")

        # 转换为字典确保datetime字段被正确格式化
        if hasattr(level, 'to_dict'):
            level_dict = await level.to_dict()
        elif hasattr(level, 'dict'):
            level_dict = level.dict()
        else:
            level_dict = dict(level)

        status_text = "启用" if is_active else "禁用"
        return success_response(data=level_dict, msg=f"会员等级已{status_text}")
    except Exception as e:
        return fail_response(msg=str(e))
