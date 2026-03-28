"""
支付服务 - 微信支付和支付宝
"""

from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import json
from decimal import Decimal

from base.plugins.customer.models import (
    PaymentTransaction,
    OrderStatus,
    TransactionStatus,
    PaymentMethod
)
# 使用新的订单模型
from base.plugins.order.models.order import CustomerOrder
from base.plugins.customer.models.membership import MembershipLevel


class PaymentService:
    """支付服务基类"""

    def __init__(self):
        self.config = {}
        # TODO: 从配置文件或数据库加载支付配置

    async def create_order(
        self,
        customer_id: int,
        membership_level_id: int,
        payment_method: str,
        client_ip: str = None
    ) -> CustomerOrder:
        """创建支付订单（适配新架构，使用 OrderService）"""
        # 获取会员等级信息
        level = await MembershipLevel.get_or_none(id=membership_level_id)
        if not level:
            raise ValueError("会员等级不存在")

        # 使用新的 OrderService 创建订单
        from base.plugins.order.services.order_service import OrderService

        order = await OrderService.create_membership_order(
            customer_id=customer_id,
            membership_level_id=membership_level_id,
            payment_method=payment_method,
            client_ip=client_ip
        )

        return order

    async def get_order(self, order_no: str) -> Optional[CustomerOrder]:
        """获取订单"""
        # 新架构：预加载 customer 和 items 关系
        return await CustomerOrder.get_or_none(order_no=order_no).prefetch_related(
            "customer", "items"
        )

    async def cancel_order(self, order_no: str) -> bool:
        """取消订单"""
        order = await self.get_order(order_no)
        if not order or order.payment_status != OrderStatus.PENDING:
            return False

        order.payment_status = OrderStatus.CANCELLED
        await order.save()
        return True

    async def check_order_expired(self) -> None:
        """检查并更新过期订单（定时任务调用）"""
        expired_orders = await CustomerOrder.filter(
            payment_status=OrderStatus.PENDING
        ).filter(expire_time__lt=datetime.now())

        for order in expired_orders:
            order.payment_status = OrderStatus.EXPIRED
            await order.save()

    async def process_payment_callback(
        self,
        order_no: str,
        transaction_id: str,
        transaction_type: str,
        amount: float,
        notify_data: Dict[str, Any]
    ) -> bool:
        """处理支付回调（适配新订单架构）"""
        # 获取订单（包含明细）
        order = await self.get_order(order_no)
        if not order:
            print(f"[PaymentCallback] 订单不存在: {order_no}")
            return False

        # 检查订单状态
        if order.payment_status == OrderStatus.PAID:
            print(f"[PaymentCallback] 订单已支付，跳过: {order_no}")
            return True  # 已处理，避免重复

        # 验证金额（使用新字段 final_amount）
        if float(order.final_amount) != amount:
            print(f"[PaymentCallback] 金额不匹配! 期望: {order.final_amount}, 实际: {amount}")
            return False

        # 创建交易记录
        transaction = await PaymentTransaction.create(
            order_id=order.id,
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            amount=Decimal(str(amount)),
            status=TransactionStatus.SUCCESS,
            notify_data=notify_data
        )
        print(f"[PaymentCallback] 创建交易记录成功: {transaction.id}")

        # 更新订单状态
        order.payment_status = OrderStatus.PAID
        order.trade_no = transaction_id
        order.pay_time = datetime.now()
        await order.save()
        print(f"[PaymentCallback] 订单状态更新成功: {order_no} -> PAID")

        # 处理会员权益（从订单明细中获取）
        try:
            from base.plugins.order.models.order import OrderItem

            # 获取订单明细
            items = await OrderItem.filter(order_id=order.id)
            print(f"[PaymentCallback] 订单 {order_no} 有 {len(items)} 个明细")

            for item in items:
                # 只处理会员类型的商品
                if item.product_type == "membership" and item.extra_info:
                    extra = item.extra_info
                    membership_level_id = extra.get("membership_level_id")
                    total_hours = extra.get("total_hours")

                    if membership_level_id and total_hours:
                        print(f"[PaymentCallback] 创建会员: level={membership_level_id}, hours={total_hours}")

                        from base.plugins.customer.services.membership_service import MembershipService
                        await MembershipService.create_customer_membership(
                            customer_id=order.customer_id,
                            membership_level_id=membership_level_id,
                            hours=total_hours
                        )
                        print(f"[PaymentCallback] 会员创建成功")
        except Exception as e:
            print(f"[PaymentCallback] 处理会员权益失败: {e}")
            import traceback
            traceback.print_exc()
            # 会员创建失败不影响支付成功状态

        return True


class WechatPayService(PaymentService):
    """微信支付服务"""

    def __init__(self):
        super().__init__()
        # TODO: 配置微信支付参数
        self.app_id = ""  # 从配置读取
        self.mch_id = ""  # 商户号
        self.api_key = ""  # API密钥
        self.notify_url = ""  # 回调地址

    async def create_payment(
        self,
        order: CustomerOrder,
        client_ip: str
    ) -> Dict[str, Any]:
        """
        创建微信支付
        返回支付二维码URL或支付参数
        """
        # TODO: 调用微信支付统一下单API
        # 这里是示例代码框架

        # 1. 构造请求参数
        params = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "nonce_str": self._generate_nonce(),
            "body": f"{order.membership_level.name} - {order.total_hours}小时",
            "out_trade_no": order.order_no,
            "total_fee": int(float(order.amount) * 100),  # 单位：分
            "spbill_create_ip": client_ip or "127.0.0.1",
            "notify_url": self.notify_url,
            "trade_type": "NATIVE"  # Native支付（扫码）
        }

        # 2. 生成签名
        params["sign"] = self._generate_sign(params)

        # 3. 调用微信API（需要使用requests等HTTP客户端）
        # response = await self._call_wechat_api(params)

        # 4. 返回支付信息
        return {
            "order_no": order.order_no,
            "amount": str(order.amount),
            "qr_code": "weixin://wxpay/bizpayurl?pr=xxxxx",  # 实际从微信API返回
            "expire_time": order.expire_time
        }

    def _generate_nonce(self) -> str:
        """生成随机字符串"""
        import random
        import string
        return ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成签名"""
        # 按照微信支付规则生成签名
        sorted_params = sorted(params.items())
        sign_str = "&".join([f"{k}={v}" for k, v in sorted_params if v != ""])
        sign_str += f"&key={self.api_key}"

        return hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    async def verify_notify(self, notify_data: Dict[str, Any]) -> bool:
        """验证回调签名"""
        # TODO: 实现签名验证
        return True


class AlipayService(PaymentService):
    """支付宝支付服务"""

    def __init__(self):
        super().__init__()
        # TODO: 配置支付宝参数
        self.app_id = ""  # 应用ID
        self.private_key = ""  # 应用私钥
        self.public_key = ""  # 支付宝公钥
        self.notify_url = ""  # 异步通知地址

    async def create_payment(
        self,
        order: CustomerOrder,
        client_ip: str
    ) -> Dict[str, Any]:
        """
        创建支付宝支付
        返回支付表单或二维码
        """
        # TODO: 调用支付宝支付API
        # 这里是示例代码框架

        # 1. 构造请求参数
        params = {
            "app_id": self.app_id,
            "method": "alipay.trade.precreate",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "biz_content": json.dumps({
                "out_trade_no": order.order_no,
                "total_amount": str(order.amount),
                "subject": f"{order.membership_level.name} - {order.total_hours}小时",
                "timeout_express": "15m"  # 15分钟过期
            })
        }

        # 2. 生成签名
        params["sign"] = self._generate_sign(params)

        # 3. 调用支付宝API
        # response = await self._call_alipay_api(params)

        # 4. 返回支付信息
        return {
            "order_no": order.order_no,
            "amount": str(order.amount),
            "qr_code": "https://qr.alipay.com/xxxxx",  # 实际从支付宝API返回
            "expire_time": order.expire_time
        }

    def _generate_sign(self, params: Dict[str, Any]) -> str:
        """生成签名"""
        # 按照支付宝规则生成RSA签名
        # TODO: 使用RSA私钥签名
        return ""

    async def verify_notify(self, notify_data: Dict[str, Any]) -> bool:
        """验证回调签名"""
        # TODO: 实现RSA签名验证
        return True


# 创建服务实例
wechat_pay_service = WechatPayService()
alipay_service = AlipayService()


def get_payment_service(method: str) -> PaymentService:
    """根据支付方式获取对应的服务"""
    if method == PaymentMethod.WECHAT:
        return wechat_pay_service
    elif method == PaymentMethod.ALIPAY:
        return alipay_service
    else:
        raise ValueError(f"不支持的支付方式: {method}")
