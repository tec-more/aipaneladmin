"""
订单服务 - 订单主表 + 订单明细表业务逻辑
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from tortoise.transactions import atomic
from decimal import Decimal

try:
    from base.plugins.order.models.order import (
        CustomerOrder, OrderItem, OrderStatus, PaymentMethod, generate_order_no
    )
    from base.plugins.customer.models.customer import Customer
    from base.plugins.product.models.product import Product
except ImportError:
    # 临时处理，避免导入错误
    CustomerOrder = None
    OrderItem = None
    OrderStatus = None
    PaymentMethod = None
    Customer = None
    Product = None


class OrderService:
    """订单服务类 - 支持订单主表 + 订单明细表"""

    @staticmethod
    async def generate_order_no() -> str:
        """生成订单编号"""
        from base.plugins.order.models.order import generate_order_no
        return generate_order_no()

    @staticmethod
    @atomic()
    async def create_order(
        customer_id: int,
        items: List[Dict[str, Any]],
        payment_method: str,
        client_ip: Optional[str] = None,
        device_info: Optional[dict] = None,
        remark: Optional[str] = None
    ) -> CustomerOrder:
        """
        创建订单（支持多商品）

        Args:
            customer_id: 客户ID
            items: 订单明细列表
                [{
                    "product_id": 1,
                    "product_name": "SVIP会员",
                    "product_type": "membership",
                    "quantity": 1,
                    "unit_price": 15.00,
                    "extra_info": {...}
                }]
            payment_method: 支付方式
            client_ip: 客户端IP
            device_info: 设备信息
            remark: 备注

        Returns:
            创建的订单对象（包含明细）
        """
        print("\n[OrderService] 开始创建订单...")
        print(f"[OrderService] customer_id: {customer_id}")
        print(f"[OrderService] payment_method: {payment_method}")
        print(f"[OrderService] items 数量: {len(items)}")

        # 验证客户是否存在
        print(f"[OrderService] 检查客户是否存在...")
        customer = await Customer.get_or_none(id=customer_id)
        if not customer:
            print(f"[OrderService] ERROR: 客户不存在！customer_id={customer_id}")
            raise ValueError("客户不存在")
        print(f"[OrderService] 客户存在: {customer.id}")

        # 计算订单金额
        print(f"[OrderService] 计算订单金额...")
        total_amount = Decimal("0.00")
        for idx, item_data in enumerate(items):
            quantity = item_data.get("quantity", 1)
            unit_price = Decimal(str(item_data.get("unit_price", 0)))
            item_total = unit_price * quantity
            total_amount += item_total
            print(f"[OrderService]   item[{idx+1}]: quantity={quantity}, unit_price={unit_price}, total={item_total}")
        print(f"[OrderService] 订单总金额: {total_amount}")

        # 生成订单号和过期时间
        print(f"[OrderService] 生成订单号和过期时间...")
        order_no = await OrderService.generate_order_no()
        expire_time = datetime.now() + timedelta(minutes=15)
        print(f"[OrderService] order_no: {order_no}")
        print(f"[OrderService] expire_time: {expire_time}")

        # 将字符串转换为枚举
        print(f"[OrderService] 转换支付方式枚举...")
        try:
            payment_method_enum = PaymentMethod(payment_method)
            print(f"[OrderService] payment_method_enum: {payment_method_enum}")
        except ValueError as e:
            print(f"[OrderService] ERROR: 无效的支付方式: {payment_method}, error: {e}")
            raise ValueError(f"无效的支付方式: {payment_method}，支持的方式: wechat, alipay, balance")

        # 创建订单主表
        print(f"[OrderService] 创建订单主表...")
        try:
            order = await CustomerOrder.create(
                order_no=order_no,
                customer_id=customer_id,
                total_amount=total_amount,
                discount_amount=Decimal("0.00"),
                final_amount=total_amount,
                payment_method=payment_method_enum,
                payment_status=OrderStatus.PENDING,
                expire_time=expire_time,
                client_ip=client_ip,
                device_info=device_info,
                remark=remark
            )
            print(f"[OrderService] 订单主表创建成功! order_id={order.id}")
        except Exception as e:
            print(f"[OrderService] ERROR: 创建订单主表失败! error: {e}")
            import traceback
            traceback.print_exc()
            raise

        # 创建订单明细
        print(f"[OrderService] 创建订单明细...")
        for idx, item_data in enumerate(items):
            print(f"[OrderService]   创建明细[{idx+1}]...")
            quantity = item_data.get("quantity", 1)
            unit_price = Decimal(str(item_data.get("unit_price", 0)))
            total_price = unit_price * quantity

            print(f"[OrderService]     order_id: {order.id}")
            print(f"[OrderService]     product_id: {item_data.get('product_id')}")
            print(f"[OrderService]     product_name: {item_data.get('product_name')}")
            print(f"[OrderService]     product_type: {item_data.get('product_type')}")
            print(f"[OrderService]     product_image: {item_data.get('product_image')}")
            print(f"[OrderService]     quantity: {quantity}")
            print(f"[OrderService]     unit_price: {unit_price}")
            print(f"[OrderService]     total_price: {total_price}")
            print(f"[OrderService]     extra_info: {item_data.get('extra_info')}")

            try:
                order_item = await OrderItem.create(
                    order_id=order.id,
                    product_id=item_data.get("product_id"),
                    product_name=item_data.get("product_name"),
                    product_type=item_data.get("product_type"),
                    product_image=item_data.get("product_image"),
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price,
                    extra_info=item_data.get("extra_info")
                )
                print(f"[OrderService]     明细创建成功! item_id={order_item.id}")
            except Exception as e:
                print(f"[OrderService]     ERROR: 创建明细失败! error: {e}")
                import traceback
                traceback.print_exc()
                raise

        # 重新加载订单（包含明细）
        print(f"[OrderService] 重新加载订单（包含明细）...")
        await order.fetch_related('items')
        print(f"[OrderService] 订单创建完成! 订单明细数量: {len(order.items)}")
        return order

    @staticmethod
    @atomic()
    async def create_membership_order(
        customer_id: int,
        membership_level_id: int,
        payment_method: str,
        client_ip: Optional[str] = None,
        device_info: Optional[dict] = None
    ) -> CustomerOrder:
        """
        创建会员充值订单（便捷方法）

        Args:
            customer_id: 客户ID
            membership_level_id: 会员等级ID
            payment_method: 支付方式
            client_ip: 客户端IP
            device_info: 设备信息

        Returns:
            创建的订单对象
        """
        from base.plugins.customer.models.membership import MembershipLevel

        # 获取会员等级
        level = await MembershipLevel.get_or_none(id=membership_level_id)
        if not level:
            raise ValueError("会员等级不存在")

        if not level.is_active:
            raise ValueError("该会员等级已停用")

        # 构建订单明细
        items = [{
            "product_id": None,  # 会员等级可能没有对应的产品
            "product_name": level.name,
            "product_type": "membership",
            "product_image": None,
            "quantity": 1,
            "unit_price": float(level.price),
            "extra_info": {
                "membership_level_id": level.id,
                "membership_level_name": level.name,
                "hours": level.duration_hours,
                "bonus_hours": level.bonus_hours,
                "total_hours": level.duration_hours + level.bonus_hours
            }
        }]

        # 调用通用创建订单方法
        return await OrderService.create_order(
            customer_id=customer_id,
            items=items,
            payment_method=payment_method,
            client_ip=client_ip,
            device_info=device_info
        )

    @staticmethod
    async def get_order_by_id(order_id: int) -> Optional[CustomerOrder]:
        """根据ID获取订单（包含明细）"""
        order = await CustomerOrder.get_or_none(id=order_id).prefetch_related('customer', 'items')
        return order

    @staticmethod
    async def get_order_by_no(order_no: str) -> Optional[CustomerOrder]:
        """根据订单号获取订单（包含明细）"""
        order = await CustomerOrder.get_or_none(order_no=order_no).prefetch_related('customer', 'items')
        return order

    @staticmethod
    async def get_orders_by_customer(
        customer_id: int,
        page: int = 1,
        page_size: int = 20
    ) -> List[CustomerOrder]:
        """获取客户的订单列表"""
        offset = (page - 1) * page_size
        return await CustomerOrder.filter(
            customer_id=customer_id
        ).prefetch_related('items').order_by("-created_at").offset(offset).limit(page_size)

    @staticmethod
    async def get_all_orders(page: int = 1, page_size: int = 20) -> List[CustomerOrder]:
        """获取所有订单列表"""
        offset = (page - 1) * page_size
        return await CustomerOrder.all().prefetch_related('customer', 'items').order_by("-created_at").offset(offset).limit(page_size)

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

        result = await CustomerOrder.filter(id=order_id).update(payment_status=status)
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

        result = await CustomerOrder.filter(id=order_id).update(**update_data)
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
        order = await CustomerOrder.get_or_none(order_no=order_no)
        if not order:
            return False

        if order.payment_status != OrderStatus.PENDING:
            return False

        await CustomerOrder.filter(order_no=order_no).update(payment_status=OrderStatus.CANCELLED)
        return True

    @staticmethod
    async def get_order_items(order_id: int) -> List[OrderItem]:
        """获取订单的所有明细"""
        return await OrderItem.filter(order_id=order_id)

    @staticmethod
    async def process_payment_callback(
        order_no: str,
        transaction_id: str,
        transaction_type: str,
        amount: float,
        notify_data: Dict[str, Any]
    ) -> bool:
        """
        处理支付回调（兼容旧的支付服务）

        Args:
            order_no: 订单号
            transaction_id: 第三方交易号
            transaction_type: 交易类型
            amount: 支付金额
            notify_data: 回调数据

        Returns:
            是否处理成功
        """
        # 获取订单
        order = await OrderService.get_order_by_no(order_no)
        if not order:
            return False

        # 检查订单状态
        if order.payment_status == OrderStatus.PAID:
            return True  # 已处理，避免重复

        # 验证金额
        if float(order.final_amount) != amount:
            return False

        # 更新订单状态
        order.payment_status = OrderStatus.PAID
        order.trade_no = transaction_id
        order.pay_time = datetime.now()
        await order.save()

        # 处理会员权益（如果订单包含会员商品）
        items = await OrderService.get_order_items(order.id)
        for item in items:
            if item.product_type == "membership" and item.extra_info:
                from base.plugins.customer.services.membership_service import MembershipService

                extra = item.extra_info
                await MembershipService.create_customer_membership(
                    customer_id=order.customer_id,
                    membership_level_id=extra.get("membership_level_id"),
                    hours=extra.get("total_hours")
                )

        return True
