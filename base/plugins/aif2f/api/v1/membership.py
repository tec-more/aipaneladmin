"""
会员相关 API
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from base.common.response import success_response
from base.plugins.aif2f.schemas import (
    MembershipLevelOut,
    FibonacciLevelOut
)
from base.plugins.aif2f.services.membership_service import MembershipService
from base.core.users.models import User
from base.core.users.auth import get_current_user

router = APIRouter(prefix="/aif2f/membership", tags=["AIF2F会员"])


@router.get("/levels", response_model=List[MembershipLevelOut], summary="获取会员等级列表")
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


@router.get("/fibonacci-level", summary="计算Fibonacci等级")
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


@router.get("/my-level", summary="获取我的会员等级")
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
    membership = await MembershipService.get_user_membership(current_user.id)

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
