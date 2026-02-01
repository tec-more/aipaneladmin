"""
用户相关 API
"""

from fastapi import APIRouter, Depends
from base.common.response import success_response, fail_response
from base.plugins.aif2f.schemas import UserProfileOut, UserProfileUpdate
from base.plugins.aif2f.services.membership_service import MembershipService
from base.core.users.auth import get_current_user
from base.core.users.models import User

router = APIRouter(prefix="/aif2f/user", tags=["AIF2F用户"])


@router.get("/profile", response_model=UserProfileOut, summary="获取用户资料")
async def get_user_profile(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的资料信息

    包含：
    - 用户基本信息
    - 会员信息
    """
    user_data = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "nickname": getattr(current_user, "nickname", None),
        "avatar": getattr(current_user, "avatar", None),
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }

    # 获取会员信息
    membership_status = await MembershipService.check_membership_status(current_user.id)
    user_data["membership"] = membership_status

    return success_response(data=user_data)


@router.put("/profile", summary="更新用户资料")
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    更新用户资料

    支持更新：
    - 昵称
    - 头像
    - 邮箱
    """
    update_data = profile_update.dict(exclude_unset=True)

    if update_data:
        # 更新用户字段
        for field, value in update_data.items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)

        await current_user.save()

    return success_response(msg="资料更新成功")


@router.get("/membership", summary="获取我的会员信息")
async def get_my_membership(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户的会员详细信息

    包含：
    - 会员等级
    - 剩余时长
    - 过期时间
    - Fibonacci等级信息
    """
    membership = await MembershipService.get_user_membership(current_user.id)

    if not membership:
        return success_response(data={
            "is_vip": False,
            "message": "暂未开通会员"
        })

    # 获取Fibonacci等级信息
    fibonacci_info = await MembershipService.calculate_fibonacci_level(membership.total_hours)

    return success_response(data={
        "is_vip": membership.is_vip,
        "is_expired": membership.is_expired,
        "level": membership.level,
        "remaining_hours": float(membership.remaining_hours),
        "total_hours": membership.total_hours,
        "used_hours": float(membership.used_hours),
        "start_time": membership.start_time,
        "expire_time": membership.expire_time,
        "fibonacci_info": fibonacci_info,
        "membership_level": membership.membership_level
    })
