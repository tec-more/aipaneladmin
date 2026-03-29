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

    与Flutter端保持完全一致的等级计算逻辑
    """

    @staticmethod
    def get_fibonacci(n: int) -> int:
        """
        动态计算第n个Fibonacci数（从1开始）

        Args:
            n: 第n个Fibonacci数

        Returns:
            Fibonacci数值

        示例:
            F(1) = 1, F(2) = 1, F(3) = 2, F(4) = 3, F(5) = 5
        """
        if n <= 0:
            return 1
        if n == 1 or n == 2:
            return 1

        a, b = 1, 1
        for _ in range(3, n + 1):
            a, b = b, a + b
        return b

    @classmethod
    def get_level_from_hours(cls, total_hours: int) -> int:
        """
        根据总充值小时数计算等级（与Dart端逻辑一致）

        计算规则：
        - 累加Fibonacci数列直到超过总小时数
        - level = n，当 sum(F(1) to F(n)) <= total_hours < sum(F(1) to F(n+1))

        示例：
        - 0小时 → Level 0
        - 1小时 → Level 1 (F(1)=1, 累计1)
        - 2小时 → Level 2 (F(1)+F(2)=1+1=2)
        - 3-4小时 → Level 3 (1+1+2=4)
        - 5-7小时 → Level 4 (1+1+2+3=7)
        - 8-12小时 → Level 5 (1+1+2+3+5=12)

        Args:
            total_hours: 总充值小时数

        Returns:
            当前等级
        """
        if total_hours <= 0:
            return 0

        level = 0
        accumulated_hours = 0

        while True:
            next_hours = cls.get_fibonacci(level + 1)
            if accumulated_hours + next_hours > total_hours:
                break
            accumulated_hours += next_hours
            level += 1

        return level

    @classmethod
    def get_hours_for_level(cls, level: int) -> int:
        """
        获取达到指定等级所需的累计时长（小时）

        等级n需要 sum(F(1) to F(n)) 小时

        Args:
            level: 等级

        Returns:
            需要的小时数
        """
        if level < 1:
            return 0

        total_hours = 0
        for i in range(1, level + 1):
            total_hours += cls.get_fibonacci(i)
        return total_hours

    @classmethod
    def get_hours_to_next_level(cls, current_level: int, total_hours: int) -> int:
        """
        获取升级到下一等级所需的额外小时数

        Args:
            current_level: 当前等级
            total_hours: 当前总小时数

        Returns:
            距离下一等级还差多少小时
        """
        required_hours = cls.get_hours_for_level(current_level + 1)
        return max(0, required_hours - total_hours)

    @classmethod
    def get_level_progress(cls, total_hours: int) -> float:
        """
        计算当前等级的进度百分比（0.0-1.0）

        Args:
            total_hours: 当前总小时数

        Returns:
            进度百分比（0.0-1.0）
        """
        level = cls.get_level_from_hours(total_hours)
        previous_level_hours = cls.get_hours_for_level(level)
        next_level_hours = cls.get_hours_for_level(level + 1)

        if next_level_hours == previous_level_hours:
            return 1.0

        progress = (total_hours - previous_level_hours) / (next_level_hours - previous_level_hours)
        return max(0.0, min(1.0, progress))

    # 等级称号定义（与Dart端一致）
    LEVEL_TITLES = {
        0: "免费用户",
        range(1, 3): "体验会员",
        range(3, 5): "正式会员",
        range(5, 8): "高级会员",
        range(8, 13): "青铜会员",
        range(13, 21): "白银会员",
        range(21, 34): "黄金会员",
        range(34, 55): "铂金会员",
        range(55, 89): "钻石会员",
        range(89, 144): "至尊会员",
    }

    @classmethod
    def get_level_title(cls, level: int) -> str:
        """
        获取等级称号（与Dart端一致）

        Args:
            level: 等级

        Returns:
            等级称号
        """
        if level >= 144:
            return "传奇会员"

        for level_range, title in cls.LEVEL_TITLES.items():
            if isinstance(level_range, range) and level in level_range:
                return title
        return "免费用户"

    @classmethod
    def get_level_color(cls, level: int) -> str:
        """
        获取等级颜色（十六进制颜色代码，与Dart端一致）

        Args:
            level: 等级

        Returns:
            颜色代码
        """
        if level >= 144:
            return "#FFD700"  # 金色
        elif level >= 89:
            return "#9C27B0"  # 紫色
        elif level >= 55:
            return "#2196F3"  # 蓝色
        elif level >= 34:
            return "#607D8B"  # 铅蓝
        elif level >= 21:
            return "#FFC107"  # 琥珀
        elif level >= 13:
            return "#9E9E9E"  # 灰色
        elif level >= 8:
            return "#795548"  # 棕色
        elif level >= 5:
            return "#4CAF50"  # 绿色
        elif level >= 3:
            return "#03A9F4"  # 浅蓝
        elif level >= 1:
            return "#9E9E9E"  # 浅灰
        else:
            return "#BDBDBD"  # 深灰

    @classmethod
    def get_level_icon(cls, level: int) -> str:
        """
        获取等级图标名称（与Dart端Material Icons对应）

        Args:
            level: 等级

        Returns:
            图标名称
        """
        if level >= 144:
            return "military_tech"
        elif level >= 89:
            return "stars"
        elif level >= 55:
            return "diamond"
        elif level >= 34:
            return "workspace_premium"
        elif level >= 21:
            return "emoji_events"
        elif level >= 13:
            return "card_membership"
        elif level >= 8:
            return "verified"
        elif level >= 5:
            return "star"
        elif level >= 3:
            return "bookmark"
        elif level >= 1:
            return "person"
        else:
            return "person_outline"

    @classmethod
    def get_level_privileges(cls, level: int) -> list:
        """
        获取等级特权列表（与Dart端完全一致）

        Args:
            level: 等级

        Returns:
            特权列表
        """
        base_privileges = ["基础翻译功能"]

        if level >= 1:
            base_privileges.extend([
                "每日100字翻译额度",
                "标准客服支持",
            ])

        if level >= 3:
            base_privileges.extend([
                "每日500字翻译额度",
                "去除主界面广告",
            ])

        if level >= 5:
            base_privileges.extend([
                "每日2000字翻译额度",
                "优先客服支持",
                "多语言互译",
            ])

        if level >= 8:
            base_privileges.extend([
                "每日5000字翻译额度",
                "专属客服支持",
                "离线翻译功能",
            ])

        if level >= 13:
            base_privileges.extend([
                "每日10000字翻译额度",
                "API访问权限",
                "定制化主题",
            ])

        if level >= 21:
            base_privileges.extend([
                "每日20000字翻译额度",
                "优先功能体验",
                "批量翻译",
            ])

        if level >= 34:
            base_privileges.extend([
                "每日50000字翻译额度",
                "多账号管理",
                "团队协作功能",
            ])

        if level >= 55:
            base_privileges.extend([
                "每日100000字翻译额度",
                "专属客户经理",
                "企业级支持",
            ])

        if level >= 89:
            base_privileges.extend([
                "无限翻译额度",
                "7x24小时专属客服",
                "定制开发服务",
            ])

        if level >= 144:
            base_privileges.extend([
                "所有功能永久使用",
                "平台合作权益",
                "品牌联名机会",
            ])

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
        """
        计算Fibonacci等级完整信息

        Args:
            hours: 总充值小时数

        Returns:
            包含等级、称号、颜色、图标、特权、进度等信息
        """
        level = fibonacci_service.get_level_from_hours(hours)

        return {
            "level": level,
            "total_hours": hours,
            "title": fibonacci_service.get_level_title(level),
            "color": fibonacci_service.get_level_color(level),
            "icon": fibonacci_service.get_level_icon(level),
            "privileges": fibonacci_service.get_level_privileges(level),
            "progress": fibonacci_service.get_level_progress(hours),
            "hours_to_next_level": fibonacci_service.get_hours_to_next_level(level, hours),
            "next_level_title": fibonacci_service.get_level_title(level + 1),
        }

    @staticmethod
    def is_premium(level: int) -> bool:
        """判断是否为高级会员（等级5+）"""
        return level >= 5

    @staticmethod
    def is_vip(level: int) -> bool:
        """判断是否为VIP会员（等级13+）"""
        return level >= 13

    @staticmethod
    def is_supreme(level: int) -> bool:
        """判断是否为至尊会员（等级89+）"""
        return level >= 89
