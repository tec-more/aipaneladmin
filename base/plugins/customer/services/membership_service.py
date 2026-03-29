"""
会员服务 - Fibonacci会员系统实现
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from decimal import Decimal

from base.plugins.customer.models import (
    MembershipLevel,
    CustomerMembership,
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
        return await MembershipLevel.get_or_none(id=level_id)

    @staticmethod
    async def create_level(level_data: dict) -> MembershipLevel:
        """创建会员等级"""
        return await MembershipLevel.create(**level_data)

    @staticmethod
    async def update_level(level_id: int, level_data: dict) -> Optional[MembershipLevel]:
        """更新会员等级"""
        level = await MembershipLevel.get_or_none(id=level_id)
        if not level:
            return None
        await level.update_from_dict(level_data)
        await level.save()
        return level

    @staticmethod
    async def delete_level(level_id: int) -> bool:
        """删除会员等级"""
        level = await MembershipLevel.get_or_none(id=level_id)
        if not level:
            return False
        await level.delete()
        return True

    @staticmethod
    async def get_customer_membership(customer_id: int) -> Optional[CustomerMembership]:
        """获取客户会员信息"""
        return await CustomerMembership.get_or_none(
            customer_id=customer_id,
            is_active=True
        ).prefetch_related("membership_level")

    @staticmethod
    async def calculate_used_hours_from_logs(customer_id: int) -> float:
        """
        从使用记录表中计算实际已用时长

        Args:
            customer_id: 客户ID

        Returns:
            已用时长（小时）
        """
        from base.plugins.customer.models.usage_log import UsageLog

        # 获取所有使用记录并汇总时长
        usage_logs = await UsageLog.filter(customer_id=customer_id)
        total_seconds = sum(log.duration_seconds for log in usage_logs)
        used_hours = total_seconds / 3600.0  # 转换为小时

        print(f"[MembershipService] 计算客户 {customer_id} 的已用时长: {len(usage_logs)} 条记录, 总计 {used_hours:.2f} 小时")
        return used_hours

    @staticmethod
    async def create_customer_membership(
        customer_id: int,
        membership_level_id: int,
        hours: int
    ) -> CustomerMembership:
        """
        创建客户会员或更新现有会员

        计算规则：
        - total_hours: 累计充值总时长
        - level: 基于total_hours的Fibonacci等级
        - used_hours: 从usage_logs表汇总计算
        - remaining_hours: total_hours - used_hours
        """
        level = await MembershipService.get_level_by_id(membership_level_id)

        # 如果会员等级不存在，创建默认等级
        if not level:
            print(f"[MembershipService] ⚠️  会员等级ID {membership_level_id} 不存在，创建默认等级...")

            # 检查是否有任何等级记录
            all_levels = await MembershipLevel.all()
            if not all_levels:
                print(f"[MembershipService] 创建默认会员等级...")
                level = await MembershipLevel.create(
                    id=1,
                    level_type="yearly",  # 年度会员
                    name="默认等级",
                    description="系统默认会员等级",
                    level=1,
                    sort_order=1,
                    is_active=True,
                    duration_days=365,
                    duration_hours=0,
                    price=0.01,  # 默认价格
                    bonus_hours=0,
                    features=["基础功能"]
                )
                print(f"[MembershipService] ✅ 默认会员等级创建成功! id={level.id}, name={level.name}")
            else:
                # 使用第一个可用等级
                level = all_levels[0]
                print(f"[MembershipService] 使用现有等级: id={level.id}, name={level.name}")

            if not level:
                raise ValueError("无法获取或创建会员等级")

        now = datetime.now()

        # 从使用记录中计算实际已用时长
        used_hours = await MembershipService.calculate_used_hours_from_logs(customer_id)

        # 检查客户是否已有会员记录（包括非激活的）
        all_memberships = await CustomerMembership.filter(customer_id=customer_id)
        print(f"[MembershipService] 客户 {customer_id} 共有 {len(all_memberships)} 条会员记录")

        # 找到最新的会员记录（不管是否激活）
        if all_memberships:
            latest = all_memberships[0]  # 按created_at倒序，第一个是最新的
            print(f"[MembershipService] 找到现有会员记录: ID={latest.id}, total_hours={latest.total_hours}, is_active={latest.is_active}")

            # 如果最新的记录不是激活的，需要激活它
            if not latest.is_active:
                print(f"[MembershipService] 现有会员未激活，将激活并累加充值")

            # 累加充值总时长
            total_hours = latest.total_hours + hours

            # 重新计算剩余时长 = 总时长 - 已用时长（从日志汇总）
            remaining_hours = total_hours - used_hours
            if remaining_hours < 0:
                remaining_hours = 0

            print(f"[MembershipService] 更新会员: customer_id={customer_id}")
            print(f"[MembershipService]   旧: total={latest.total_hours}h, used={latest.used_hours}h, remaining={latest.remaining_hours}h")
            print(f"[MembershipService]   新充值: +{hours}h")
            print(f"[MembershipService]   从日志计算已用: {used_hours:.2f}h")
            print(f"[MembershipService]   新: total={total_hours}h, used={used_hours:.2f}h, remaining={remaining_hours:.2f}h")

            # 如果未过期，延长有效期；否则重新计算
            if not latest.is_expired:
                new_expire_time = latest.expire_time + timedelta(hours=hours)
            else:
                new_expire_time = now + timedelta(
                    days=level.duration_days,
                    hours=level.duration_hours
                )

            latest.total_hours = total_hours
            latest.used_hours = used_hours
            latest.remaining_hours = remaining_hours
            latest.expire_time = new_expire_time
            latest.level = fibonacci_service.get_level_from_hours(total_hours)
            latest.is_active = True  # 激活会员

            await latest.save()

            print(f"[MembershipService] ✅ 会员更新成功: ID={latest.id}")
            return latest
        else:
            # 创建新会员之前，先停用所有旧的会员记录
            print(f"[MembershipService] 创建新会员前，停用所有旧会员记录...")
            old_memberships = await CustomerMembership.filter(customer_id=customer_id, is_active=True)
            for old_m in old_memberships:
                old_m.is_active = False
                await old_m.save()
                print(f"[MembershipService]   停用旧会员: ID={old_m.id}")

            # 创建新会员
            total_hours = hours
            remaining_hours = total_hours - used_hours
            if remaining_hours < 0:
                remaining_hours = 0

            print(f"[MembershipService] 创建新会员: customer_id={customer_id}")
            print(f"[MembershipService]   充值: {hours}h")
            print(f"[MembershipService]   从日志计算已用: {used_hours:.2f}h")
            print(f"[MembershipService]   初始: total={total_hours}h, used={used_hours:.2f}h, remaining={remaining_hours:.2f}h")

            expire_time = now + timedelta(
                days=level.duration_days,
                hours=level.duration_hours
            )

            customer_membership = await CustomerMembership.create(
                customer_id=customer_id,
                membership_level_id=membership_level_id,
                start_time=now,
                expire_time=expire_time,
                total_hours=total_hours,
                used_hours=used_hours if used_hours > 0 else 0,
                remaining_hours=remaining_hours,
                level=fibonacci_service.get_level_from_hours(total_hours),
                is_active=True
            )

            print(f"[MembershipService] ✅ 新会员创建成功: ID={customer_membership.id}")
            return customer_membership

    @staticmethod
    async def update_membership_usage(customer_id: int, used_hours: float) -> bool:
        """更新会员使用时长"""
        membership = await MembershipService.get_customer_membership(customer_id)
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
    async def check_membership_status(customer_id: int) -> dict:
        """
        检查会员状态（实时从使用记录计算）

        Returns:
            会员状态字典，包含从usage_logs实时计算的used_hours
        """
        membership = await MembershipService.get_customer_membership(customer_id)

        if not membership:
            return {
                "is_vip": False,
                "level": 0,
                "remaining_hours": 0,
                "is_expired": True
            }

        # 从使用记录中实时计算已用时长
        used_hours = await MembershipService.calculate_used_hours_from_logs(customer_id)
        remaining_hours = membership.total_hours - used_hours
        if remaining_hours < 0:
            remaining_hours = 0

        return {
            "is_vip": membership.is_vip,
            "level": membership.level,
            "remaining_hours": remaining_hours,
            "is_expired": membership.is_expired,
            "expire_time": membership.expire_time,
            "total_hours": membership.total_hours,
            "used_hours": used_hours
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
