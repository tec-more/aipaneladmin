"""
支付相关 API
"""

from fastapi import APIRouter, Depends, Header, Request
from base.common.response import success_response, fail_response
from base.plugins.aif2f.schemas import CreateOrderIn, OrderOut
from base.plugins.aif2f.services.payment_service import get_payment_service
from base.plugins.aif2f.models import PaymentMethod
from base.core.users.models import User
from base.core.users.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aif2f/payment", tags=["AIF2F支付"])


@router.post("/create-order", summary="创建充值订单")
async def create_recharge_order(
    order_data: CreateOrderIn,
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """
    创建充值订单并获取支付信息

    支付方式：
    - wechat: 微信支付（扫码）
    - alipay: 支付宝（扫码）

    返回：
    - 订单号
    - 支付金额
    - 二维码URL
    - 过期时间
    """
    try:
        # 获取客户端IP
        client_ip = None
        if request:
            # 尝试从多个头部获取真实IP
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                client_ip = forwarded.split(",")[0].strip()
            else:
                client_ip = request.client.host if request.client else None

        # 添加到order_data
        if not order_data.client_ip:
            order_data.client_ip = client_ip

        # 创建订单
        payment_service = get_payment_service(order_data.payment_method)
        order = await payment_service.create_order(
            user_id=current_user.id,
            membership_level_id=order_data.membership_level_id,
            payment_method=order_data.payment_method,
            client_ip=order_data.client_ip
        )

        # 创建支付
        payment_info = await payment_service.create_payment(
            order=order,
            client_ip=order_data.client_ip or "127.0.0.1"
        )

        return success_response(data=payment_info, msg="订单创建成功")

    except Exception as e:
        logger.error(f"创建订单失败: {str(e)}")
        return fail_response(msg=f"创建订单失败: {str(e)}")


@router.get("/order/{order_no}", summary="查询订单状态")
async def get_order_status(
    order_no: str,
    current_user: User = Depends(get_current_user)
):
    """
    查询订单支付状态

    返回：
    - 订单号
    - 订单状态
    - 支付时间（已支付）
    """
    payment_service = get_payment_service("wechat")  # 使用任意服务获取订单
    order = await payment_service.get_order(order_no)

    if not order:
        return fail_response(msg="订单不存在")

    # 验证订单属于当前用户
    if order.user_id != current_user.id:
        return fail_response(msg="无权访问此订单")

    return success_response(data={
        "order_no": order.order_no,
        "payment_status": order.payment_status,
        "pay_time": order.pay_time,
        "amount": str(order.amount),
        "total_hours": order.total_hours,
        "is_paid": order.is_paid,
        "is_expired": order.is_expired
    })


@router.post("/cancel-order/{order_no}", summary="取消订单")
async def cancel_order(
    order_no: str,
    current_user: User = Depends(get_current_user)
):
    """
    取消未支付的订单

    只能取消状态为"待支付"的订单
    """
    payment_service = get_payment_service("wechat")
    order = await payment_service.get_order(order_no)

    if not order:
        return fail_response(msg="订单不存在")

    # 验证订单属于当前用户
    if order.user_id != current_user.id:
        return fail_response(msg="无权操作此订单")

    # 取消订单
    success = await payment_service.cancel_order(order_no)

    if success:
        return success_response(msg="订单已取消")
    else:
        return fail_response(msg="取消失败，订单可能已支付或已过期")


@router.post("/wechat/notify", summary="微信支付回调")
async def wechat_pay_notify(request: Request):
    """
    微信支付回调通知

    注意：
    - 此接口由微信服务器调用
    - 需要验证签名
    - 返回特定的XML格式响应
    """
    try:
        # 获取回调数据
        body = await request.body()
        # TODO: 解析XML数据

        # TODO: 验证签名
        # wechat_service = get_payment_service("wechat")
        # is_valid = await wechat_service.verify_notify(notify_data)

        # TODO: 处理支付结果
        # await wechat_service.process_payment_callback(...)

        # 返回微信要求的格式
        return success_response(msg="OK")

    except Exception as e:
        logger.error(f"微信支付回调处理失败: {str(e)}")
        return fail_response(msg="FAIL")


@router.post("/alipay/notify", summary="支付宝回调")
async def alipay_notify(request: Request):
    """
    支付宝回调通知

    注意：
    - 此接口由支付宝服务器调用
    - 需要验证签名
    - 返回特定的文本响应
    """
    try:
        # 获取回调数据
        form_data = await request.form()

        # TODO: 验证签名
        # alipay_service = get_payment_service("alipay")
        # is_valid = await alipay_service.verify_notify(dict(form_data))

        # TODO: 处理支付结果
        # await alipay_service.process_payment_callback(...)

        return success_response(msg="success")

    except Exception as e:
        logger.error(f"支付宝回调处理失败: {str(e)}")
        return fail_response(msg="failure")
