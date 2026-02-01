"""
会员服务 - Fibonacci会员系统实现
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from decimal import Decimal

from base.plugins.aif2f.models import (
    MembershipLevel,
    UserMembership,
    LevelType
)


class FibonacciMembershipSystem:
    """
    Fibonacci会员系统
    基于Fibonacci数列的无限等级系统
    """

    # Fibonacci数列 (前20个)
    FIBONACCI_SEQUENCE = [
        1, 1, 2, 3, 5, 8, 13, 21, 34, 55,
        89, 144, 233, 377, 610, 987, 1597, 2584, 4181, 6765
    ]

    @classmethod
    def get_level_from_hours(cls, total_hours: int) -> int:
        """
        根据总充值小时数计算等级

        规则：
        - 等级1: 1小时
        - 等级2: 1小时
        - 等级3: 2小时
        - 等级4: 3小时
        - 等级5: 5小时
        ...

        Args:
            total_hours: 总充值小时数

        Returns:
            当前等级
        """
        if total_hours <= 0:
            return 0

        level = 0
        accumulated = 0

        for hours in cls.FIBONACCI_SEQUENCE:
            accumulated += hours
            if total_hours <= accumulated:
                level += 1
                break
            level += 1

        return level

    @classmethod
    def get_hours_for_level(cls, level: int) -> int:
        """
        获取指定等级需要的小时数

        Args:
            level: 等级

        Returns:
            需要的小时数
        """
        if level <= 0 or level > len(cls.FIBONACCI_SEQUENCE):
            return 0

        # 计算前level个Fibonacci数的和
        return sum(cls.FIBONACCI_SEQUENCE[:level])

    @classmethod
    def get_next_level_info(cls, total_hours: int) -> Tuple[int, int, int]:
        """
        获取下一等级信息

        Args:
            total_hours: 当前总小时数

        Returns:
            (当前等级, 下一等级需要小时数, 距离下一等级还差多少小时)
        """
        current_level = cls.get_level_from_hours(total_hours)

        if current_level >= len(cls.FIBONACCI_SEQUENCE):
            return current_level, 0, 0

        next_level_hours = cls.get_hours_for_level(current_level + 1)
        remaining = next_level_hours - total_hours

        return current_level, next_level_hours, max(0, remaining)

    @classmethod
    def get_level_privileges(cls, level: int) -> List[str]:
        """
        获取等级特权列表

        Args:
            level: 等级

        Returns:
            特权列表
        """
        base_privileges = ["基础翻译功能"]

        if level >= 3:
            base_privileges.append("优先客服支持")
        if level >= 5:
            base_privileges.append("API访问权限")
        if level >= 8:
            base_privileges.append("离线翻译功能")
        if level >= 10:
            base_privileges.append("无限翻译额度")
        if level >= 15:
            base_privileges.extend(["专属客户经理", "定制化服务"])

        return base_privileges


# 创建全局实例
fibonacci_service = FibonacciMembershipSystem()


class MembershipService:
    """会员服务"""

    @staticmethod
    async def get_all_levels(active_only: bool = True) -> List[MembershipLevel]:
        """获取所有会员等级"""
        query = MembershipLevel.all()
        if active_only:
            query = query.filter(is_active=True)
        return await query.order_by("sort_order", "level")

    @staticmethod
    async def get_level_by_id(level_id: int) -> Optional[MembershipLevel]:
        """根据ID获取会员等级"""
        return await MembershipLevel.get_or_none(id=level_id, is_active=True)

    @staticmethod
    async def get_user_membership(user_id: int) -> Optional[UserMembership]:
        """获取用户会员信息"""
        return await UserMembership.get_or_none(
            user_id=user_id,
            is_active=True
        ).prefetch_related("membership_level")

    @staticmethod
    async def create_user_membership(
        user_id: int,
        membership_level_id: int,
        hours: int
    ) -> UserMembership:
        """创建用户会员"""
        level = await MembershipService.get_level_by_id(membership_level_id)
        if not level:
            raise ValueError("会员等级不存在")

        now = datetime.now()

        # 检查用户是否已有会员
        existing = await MembershipService.get_user_membership(user_id)
        if existing:
            # 如果有，则累加时间
            total_hours = existing.total_hours + hours
            remaining_hours = existing.remaining_hours + hours

            # 如果未过期，延长有效期；否则重新计算
            if not existing.is_expired:
                new_expire_time = existing.expire_time + timedelta(hours=hours)
            else:
                new_expire_time = now + timedelta(
                    days=level.duration_days,
                    hours=level.duration_hours
                )

            existing.total_hours = total_hours
            existing.remaining_hours = remaining_hours
            existing.expire_time = new_expire_time
            existing.level = fibonacci_service.get_level_from_hours(total_hours)
            await existing.save()

            return existing
        else:
            # 创建新会员
            expire_time = now + timedelta(
                days=level.duration_days,
                hours=level.duration_hours
            )

            user_membership = await UserMembership.create(
                user_id=user_id,
                membership_level_id=membership_level_id,
                start_time=now,
                expire_time=expire_time,
                total_hours=hours,
                remaining_hours=hours,
                level=fibonacci_service.get_level_from_hours(hours),
                is_active=True
            )

            return user_membership

    @staticmethod
    async def update_membership_usage(user_id: int, used_hours: float) -> bool:
        """更新会员使用时长"""
        membership = await MembershipService.get_user_membership(user_id)
        if not membership or not membership.is_vip:
            return False

        new_remaining = float(membership.remaining_hours) - used_hours
        if new_remaining < 0:
            new_remaining = 0

        membership.used_hours = float(membership.used_hours) + used_hours
        membership.remaining_hours = new_remaining

        # 如果剩余时长为0，停用会员
        if new_remaining <= 0:
            membership.is_active = False

        await membership.save()
        return True

    @staticmethod
    async def check_membership_status(user_id: int) -> dict:
        """检查会员状态"""
        membership = await MembershipService.get_user_membership(user_id)

        if not membership:
            return {
                "is_vip": False,
                "level": 0,
                "remaining_hours": 0,
                "is_expired": True
            }

        return {
            "is_vip": membership.is_vip,
            "level": membership.level,
            "remaining_hours": float(membership.remaining_hours),
            "is_expired": membership.is_expired,
            "expire_time": membership.expire_time,
            "total_hours": membership.total_hours,
            "used_hours": float(membership.used_hours)
        }

    @staticmethod
    async def calculate_fibonacci_level(hours: int) -> dict:
        """计算Fibonacci等级"""
        current_level, next_hours, remaining = fibonacci_service.get_next_level_info(hours)
        privileges = fibonacci_service.get_level_privileges(current_level)

        return {
            "level": current_level,
            "total_hours": hours,
            "next_level_hours": next_hours if next_hours > 0 else None,
            "remaining_to_next": remaining if remaining > 0 else None,
            "privileges": privileges
        }
