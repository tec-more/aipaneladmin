"""
订单服务 - 实现订单业务逻辑
"""
from datetime import datetime, timedelta
import uuid
from typing import Optional, List
from tortoise.transactions import atomic

try:
    from base.plugins.order.models.order import Order
    from base.plugins.customer.models.customer import Customer
    from base.plugins.product.models.product import Product
except ImportError:
    # 临时处理，避免导入错误
    Order = None
    Customer = None
    Product = None


class OrderService:
    """订单服务类"""

    @staticmethod
    async def generate_order_no() -> str:
        """生成订单编号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_str = str(uuid.uuid4())[:8]
        return f"ORD{timestamp}{random_str}"

    @staticmethod
    @atomic
    async def create_order(customer_id: int, product_id: int, quantity: int = 1) -> Order:
        """创建订单
        
        Args:
            customer_id: 客户ID
            product_id: 产品ID
            quantity: 购买数量
            
        Returns:
            创建的订单对象
        """
        # 验证客户是否存在
        customer = await Customer.filter(id=customer_id).first()
        if not customer:
            raise ValueError("客户不存在")

        # 验证产品是否存在
        product = await Product.filter(id=product_id).first()
        if not product:
            raise ValueError("产品不存在")

        if not product.is_active:
            raise ValueError("产品已下架")

        if product.stock < quantity:
            raise ValueError("产品库存不足")

        # 确定产品类型和相关属性
        product_type = ""
        product_value = None
        membership_duration = None

        # 根据产品名称或分类判断产品类型
        if "点卷" in product.name or "point" in str(product.tags).lower():
            product_type = "point"
            # 假设点卷值是根据价格计算的，例如 1元 = 10点卷
            product_value = int(float(product.price) * 10)
        elif "会员" in product.name or "membership" in str(product.tags).lower():
            product_type = "membership"
            # 假设会员时长是根据产品名称或标签提取的，例如 "月度会员" 对应 30 天
            if "月度" in product.name:
                membership_duration = 30
            elif "季度" in product.name:
                membership_duration = 90
            elif "年度" in product.name:
                membership_duration = 365
            else:
                membership_duration = 30  # 默认30天

        # 生成订单编号
        order_no = await OrderService.generate_order_no()

        # 计算订单金额
        total_amount = product.price * quantity

        # 创建订单
        order = await Order.create(
            order_no=order_no,
            customer_id=customer_id,
            total_amount=total_amount,
            payment_status=1,  # 假设直接支付成功
            payment_method="虚拟支付",
            payment_time=datetime.now(),
            order_status=1,  # 已支付
            product_id=product_id,
            quantity=quantity,
            unit_price=product.price,
            product_type=product_type,
            product_value=product_value,
            membership_duration=membership_duration
        )

        # 更新产品库存和销售数量
        await Product.filter(id=product_id).update(
            stock=product.stock - quantity,
            sales_count=product.sales_count + quantity
        )

        # 更新客户信息
        if product_type == "point":
            # 增加点卷
            await Customer.filter(id=customer_id).update(
                points=customer.points + (product_value * quantity)
            )
        elif product_type == "membership":
            # 更新会员到期日期
            now = datetime.now()
            if customer.membership_expiry_date and customer.membership_expiry_date > now:
                # 如果会员未过期，累加时长
                new_expiry = customer.membership_expiry_date + timedelta(days=membership_duration * quantity)
            else:
                # 如果会员已过期，从当前时间开始计算
                new_expiry = now + timedelta(days=membership_duration * quantity)
            
            await Customer.filter(id=customer_id).update(
                membership_expiry_date=new_expiry
            )

        return order

    @staticmethod
    async def get_order_by_id(order_id: int) -> Optional[Order]:
        """根据ID获取订单"""
        return await Order.filter(id=order_id).first()

    @staticmethod
    async def get_order_by_no(order_no: str) -> Optional[Order]:
        """根据订单编号获取订单"""
        return await Order.filter(order_no=order_no).first()

    @staticmethod
    async def get_orders_by_customer(customer_id: int, page: int = 1, page_size: int = 20) -> List[Order]:
        """获取客户的订单列表"""
        offset = (page - 1) * page_size
        return await Order.filter(customer_id=customer_id).order_by("-created_at").offset(offset).limit(page_size)

    @staticmethod
    async def get_all_orders(page: int = 1, page_size: int = 20) -> List[Order]:
        """获取所有订单列表"""
        offset = (page - 1) * page_size
        return await Order.order_by("-created_at").offset(offset).limit(page_size)

    @staticmethod
    async def update_order_status(order_id: int, status: int) -> bool:
        """更新订单状态"""
        result = await Order.filter(id=order_id).update(order_status=status)
        return result > 0

    @staticmethod
    async def update_payment_status(order_id: int, status: int, payment_method: str = None, transaction_id: str = None) -> bool:
        """更新支付状态"""
        update_data = {
            "payment_status": status
        }
        
        if status == 1:  # 支付成功
            update_data["payment_time"] = datetime.now()
            
        if payment_method:
            update_data["payment_method"] = payment_method
            
        if transaction_id:
            update_data["transaction_id"] = transaction_id
            
        result = await Order.filter(id=order_id).update(**update_data)
        return result > 0