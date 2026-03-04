from .order import (
    CustomerOrder,
    PaymentMethod,
    OrderStatus,
    generate_order_no
)

# 添加别名以兼容旧代码
Order = CustomerOrder

__all__ = [
    'CustomerOrder',
    'Order',  # 别名
    'PaymentMethod',
    'OrderStatus',
    'generate_order_no',
]
