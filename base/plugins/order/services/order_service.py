"""
订单服务 - 实现订单业务逻辑
"""
from datetime import datetime, timedelta
from typing import Optional, List
from tortoise.transactions import atomic

try:
    from base.plugins.order.models.order import CustomerOrder as Order, OrderStatus, PaymentMethod
    from base.plugins.customer.models.customer import Customer
    from base.plugins.customer.models.membership import MembershipLevel
except ImportError:
    # 临时处理，避免导入错误
    Order = None
    Customer = None
    MembershipLevel = None
    OrderStatus = None
    PaymentMethod = None


class OrderService:
    """订单服务类 - 客户充值订单"""

    @staticmethod
    async def generate_order_no() -> str:
        """生成订单编号"""
        from base.plugins.order.models.order import generate_order_no
        return generate_order_no()

    @staticmethod
    @atomic
    async def create_order(
        customer_id: int,
        membership_level_id: int,
        payment_method: str,
        client_ip: Optional[str] = None,
        device_info: Optional[dict] = None
    ) -> Order:
        """
        创建充值订单

        Args:
            customer_id: 客户ID
            membership_level_id: 会员等级ID
            payment_method: 支付方式
            client_ip: 客户端IP
            device_info: 设备信息

        Returns:
            创建的订单对象
        """
        # 验证客户是否存在
        customer = await Customer.get_or_none(id=customer_id)
        if not customer:
            raise ValueError("客户不存在")

        # 验证会员等级是否存在
        membership_level = await MembershipLevel.get_or_none(id=membership_level_id)
        if not membership_level:
            raise ValueError("会员等级不存在")

        if not membership_level.is_active:
            raise ValueError("该会员等级已停用")

        # 生成订单编号
        order_no = await OrderService.generate_order_no()

        # 计算过期时间（15分钟后）
        expire_time = datetime.now() + timedelta(minutes=15)

        # 创建订单
        order = await Order.create(
            order_no=order_no,
            customer_id=customer_id,
            membership_level_id=membership_level_id,
            amount=membership_level.price,
            hours=membership_level.hours,
            bonus_hours=membership_level.bonus_hours,
            total_hours=membership_level.hours + membership_level.bonus_hours,
            payment_method=payment_method,
            payment_status=OrderStatus.PENDING,
            expire_time=expire_time,
            client_ip=client_ip,
            device_info=device_info
        )

        return order

    @staticmethod
    async def get_order_by_id(order_id: int) -> Optional[Order]:
        """根据ID获取订单"""
        return await Order.get_or_none(id=order_id).prefetch_related('customer', 'membership_level')

    @staticmethod
    async def get_order_by_no(order_no: str) -> Optional[Order]:
        """根据订单编号获取订单"""
        return await Order.get_or_none(order_no=order_no).prefetch_related('customer', 'membership_level')

    @staticmethod
    async def get_orders_by_customer(customer_id: int, page: int = 1, page_size: int = 20) -> List[Order]:
        """获取客户的订单列表"""
        offset = (page - 1) * page_size
        return await Order.filter(
            customer_id=customer_id
        ).prefetch_related('membership_level').order_by("-created_at").offset(offset).limit(page_size)

    @staticmethod
    async def get_all_orders(page: int = 1, page_size: int = 20) -> List[Order]:
        """获取所有订单列表"""
        offset = (page - 1) * page_size
        return await Order.all().prefetch_related('customer', 'membership_level').order_by("-created_at").offset(offset).limit(page_size)

    @staticmethod
    async def update_order_status(order_id: int, status: str) -> bool:
        """
        更新订单状态

        Args:
            order_id: 订单ID
            status: 订单状态 (OrderStatus枚举值)

        Returns:
            是否更新成功
        """
        # 验证状态值
        if not hasattr(OrderStatus, status.upper()):
            raise ValueError(f"无效的订单状态: {status}")

        result = await Order.filter(id=order_id).update(payment_status=status)
        return result > 0

    @staticmethod
    async def update_payment_status(
        order_id: int,
        status: str,
        payment_method: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> bool:
        """
        更新支付状态

        Args:
            order_id: 订单ID
            status: 支付状态 (OrderStatus枚举值)
            payment_method: 支付方式
            transaction_id: 第三方交易号

        Returns:
            是否更新成功
        """
        # 验证状态值
        try:
            order_status = OrderStatus(status)
        except ValueError:
            raise ValueError(f"无效的支付状态: {status}")

        update_data = {"payment_status": order_status}

        # 如果是支付成功，记录支付时间
        if order_status == OrderStatus.PAID:
            update_data["pay_time"] = datetime.now()

        if transaction_id:
            update_data["trade_no"] = transaction_id

        result = await Order.filter(id=order_id).update(**update_data)
        return result > 0

    @staticmethod
    async def cancel_order(order_no: str) -> bool:
        """
        取消订单

        Args:
            order_no: 订单号

        Returns:
            是否取消成功
        """
        order = await Order.get_or_none(order_no=order_no)
        if not order:
            return False

        if order.payment_status != OrderStatus.PENDING:
            return False

        await Order.filter(order_no=order_no).update(payment_status=OrderStatus.CANCELLED)
        return True
