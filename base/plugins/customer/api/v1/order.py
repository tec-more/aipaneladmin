"""
订单相关 API
"""

from fastapi import APIRouter, Depends, Request
from typing import Optional
from base.common.response import success_response, fail_response
from base.plugins.customer.schemas import CreateOrderIn
from base.plugins.customer.services.payment_service import get_payment_service
from base.plugins.customer.models import CustomerOrder, OrderStatus, UsageLog
from base.core.users.models.users import User
from base.common.security import get_current_user
from datetime import datetime
from pydantic import BaseModel

order_router = APIRouter(prefix="/order", tags=["客户订单"])


async def get_or_create_customer(user: User) -> "Customer":
    """获取或创建客户记录"""
    from base.plugins.customer.models.customer import Customer

    # 首先通过system_user关联查找
    customer = await Customer.get_or_none(system_user_id=user.id)

    if not customer:
        # 如果没找到，尝试通过email查找
        customer = await Customer.get_or_none(email=user.email)

        if not customer:
            # 如果还是没找到，创建新的客户记录
            customer = await Customer.create(
                system_user_id=user.id,
                username=user.username,
                email=user.email,
                nickname=getattr(user, "nickname", None),
                avatar=getattr(user, "avatar", None),
                is_active=True
            )
        else:
            # 如果通过email找到了，更新关联
            customer.system_user_id = user.id
            await customer.save()

    return customer


class OrderListQuery(BaseModel):
    """订单列表查询"""
    page: int = 1
    page_size: int = 10
    status: Optional[str] = None


@order_router.post("/create", summary="创建充值订单")
async def create_recharge_order(
    order_data: CreateOrderIn,
    current_user: User = Depends(get_current_user)
):
    """
    创建充值订单

    返回支付信息（二维码或支付URL）
    """
    # 获取客户信息
    customer = await get_or_create_customer(current_user)

    # 创建订单
    payment_service = get_payment_service(order_data.payment_method)
    order = await payment_service.create_order(
        customer_id=customer.id,
        membership_level_id=order_data.membership_level_id,
        payment_method=order_data.payment_method,
        client_ip=order_data.client_ip
    )

    # 创建支付
    payment_info = await payment_service.create_payment(order, order_data.client_ip or "127.0.0.1")

    return success_response(data={
        "order_no": order.order_no,
        "amount": str(order.amount),
        "payment_info": payment_info
    }, msg="订单创建成功")


@order_router.get("/list", summary="获取订单列表")
async def get_order_list(
    page: int = 1,
    page_size: int = 10,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    获取当前客户的订单列表
    """
    customer = await get_or_create_customer(current_user)

    query = CustomerOrder.filter(customer_id=customer.id)

    if status:
        query = query.filter(payment_status=status)

    total = await query.count()
    orders = await query.offset((page - 1) * page_size).limit(page_size).order_by("-created_at")

    return success_response(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": orders
    })


@order_router.get("/{order_no}", summary="获取订单详情")
async def get_order_detail(
    order_no: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取订单详情
    """
    customer = await get_or_create_customer(current_user)

    order = await CustomerOrder.get_or_none(
        order_no=order_no,
        customer_id=customer.id
    ).prefetch_related("membership_level")

    if not order:
        return fail_response(msg="订单不存在")

    return success_response(data=order)


@order_router.post("/{order_no}/cancel", summary="取消订单")
async def cancel_order(
    order_no: str,
    current_user: User = Depends(get_current_user)
):
    """
    取消待支付订单
    """
    customer = await get_or_create_customer(current_user)

    # 验证订单属于当前用户
    order = await CustomerOrder.get_or_none(
        order_no=order_no,
        customer_id=customer.id
    )

    if not order:
        return fail_response(msg="订单不存在")

    payment_service = get_payment_service("alipay")  # 使用任意服务即可
    success = await payment_service.cancel_order(order_no)

    if success:
        return success_response(msg="订单已取消")
    else:
        return fail_response(msg="取消失败，订单可能已支付或不存在")


@order_router.get("/usage/list", summary="获取使用记录列表")
async def get_usage_logs(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    获取当前客户的使用记录
    """
    customer = await get_or_create_customer(current_user)

    query = UsageLog.filter(customer_id=customer.id)

    total = await query.count()
    logs = await query.offset((page - 1) * page_size).limit(page_size).order_by("-created_at")

    return success_response(data={
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": logs
    })


@order_router.post("/webhook/wechat", summary="微信支付回调")
async def wechat_payment_callback(request: Request):
    """
    微信支付回调接口
    """
    # TODO: 验证签名
    notify_data = await request.json()

    order_no = notify_data.get("out_trade_no")
    transaction_id = notify_data.get("transaction_id")
    amount = float(notify_data.get("total_fee", 0)) / 100  # 转换为元

    payment_service = get_payment_service("wechat")
    success = await payment_service.process_payment_callback(
        order_no=order_no,
        transaction_id=transaction_id,
        transaction_type="wechat",
        amount=amount,
        notify_data=notify_data
    )

    if success:
        return {"code": "SUCCESS", "message": "OK"}
    else:
        return {"code": "FAIL", "message": "处理失败"}


@order_router.post("/webhook/alipay", summary="支付宝支付回调")
async def alipay_payment_callback(request: Request):
    """
    支付宝支付回调接口
    """
    # TODO: 验证签名
    notify_data = await request.json()

    order_no = notify_data.get("out_trade_no")
    transaction_id = notify_data.get("trade_no")
    amount = float(notify_data.get("total_amount", 0))

    payment_service = get_payment_service("alipay")
    success = await payment_service.process_payment_callback(
        order_no=order_no,
        transaction_id=transaction_id,
        transaction_type="alipay",
        amount=amount,
        notify_data=notify_data
    )

    if success:
        return {"code": "SUCCESS", "message": "OK"}
    else:
        return {"code": "FAIL", "message": "处理失败"}
