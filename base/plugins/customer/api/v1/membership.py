"""
会员相关 API
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from base.common.response import success_response, fail_response
from base.plugins.customer.schemas import (
    MembershipLevelOut,
    FibonacciLevelOut
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
