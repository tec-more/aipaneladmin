"""
支付服务 - 微信支付和支付宝
"""

from typing import Optional, Dict, Any
from datetime import datetime
import hashlib
import json
from base.common.setting import settings
from base.plugins.aif2f.models import (
    RechargeOrder,
    PaymentTransaction,
    OrderStatus,
    TransactionStatus,
    PaymentMethod
)


class PaymentService:
    """支付服务基类"""

    def __init__(self):
        self.config = {}
        # TODO: 从配置文件或数据库加载支付配置

    async def create_order(
        self,
        user_id: int,
        membership_level_id: int,
        payment_method: str,
        client_ip: str = None
    ) -> RechargeOrder:
        """创建支付订单"""
        # 使用模型的方法创建订单
        order = await RechargeOrder.create_order(
            user_id=user_id,
            membership_level_id=membership_level_id,
            payment_method=payment_method,
            client_ip=client_ip
        )
        await order.save()
        return order

    async def get_order(self, order_no: str) -> Optional[RechargeOrder]:
        """获取订单"""
        return await RechargeOrder.get_or_none(order_no=order_no).prefetch_related(
            "membership_level"
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
        expired_orders = await RechargeOrder.filter(
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
        """处理支付回调"""
        # 获取订单
        order = await self.get_order(order_no)
        if not order:
            return False

        # 检查订单状态
        if order.payment_status == OrderStatus.PAID:
            return True  # 已处理，避免重复

        # 验证金额
        if float(order.amount) != amount:
            return False

        # 创建交易记录
        transaction = await PaymentTransaction.create(
            order_id=order.id,
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            amount=amount,
            status=TransactionStatus.SUCCESS,
            notify_data=notify_data
        )

        # 更新订单状态
        order.payment_status = OrderStatus.PAID
        order.trade_no = transaction_id
        order.pay_time = datetime.now()
        await order.save()

        # 创建或更新用户会员
        from base.plugins.aif2f.services.membership_service import MembershipService
        await MembershipService.create_user_membership(
            user_id=order.user_id,
            membership_level_id=order.membership_level_id,
            hours=order.total_hours
        )

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
        order: RechargeOrder,
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
        order: RechargeOrder,
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
