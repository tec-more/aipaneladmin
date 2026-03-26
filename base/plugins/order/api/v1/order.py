"""
订单API路由
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from base.common.response import SuccessResponse
from base.plugins.order.schemas.order_schema import (
    CreateOrderIn, OrderOut, OrderListResponse, OrderUpdateRequest, OrderCreateResponse
)
from base.plugins.order.services.order_service import OrderService


# 创建路由实例
order_router = APIRouter(
    prefix="",
    tags=["订单管理"],
    responses={404: {"description": "Not found"}},
)


# ============ 具体路由（固定路径）必须放在参数化路由之前 ============

@order_router.post("/create", response_model=OrderCreateResponse, summary="创建充值订单")
async def create_order(order_create: CreateOrderIn):
    """创建充值订单

    - **membership_level_id**: 会员等级ID
    - **payment_method**: 支付方式(wechat/alipay)
    - **client_ip**: 客户端IP（可选）
    - **device_info**: 设备信息（可选）
    """
    try:
        order = await OrderService.create_order(
            customer_id=order_create.customer_id,
            membership_level_id=order_create.membership_level_id,
            payment_method=order_create.payment_method,
            client_ip=order_create.client_ip,
            device_info=order_create.device_info
        )
        return SuccessResponse(
            data={
                "order_id": order.id,
                "order_no": order.order_no
            },
            msg="订单创建成功"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="创建订单失败")


@order_router.get("/by-order-no/{order_no}", response_model=OrderOut, summary="根据订单号获取订单详情")
async def get_order_by_no(order_no: str):
    """根据订单编号获取订单详情"""
    order = await OrderService.get_order_by_no(order_no)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # 转换为字典确保datetime字段被正确格式化
    if hasattr(order, 'to_dict'):
        order_dict = await order.to_dict()
    elif hasattr(order, 'dict'):
        order_dict = order.dict()
    else:
        order_dict = dict(order)
    return SuccessResponse(data=order_dict, msg="获取订单详情成功")


@order_router.get("/customer/{customer_id}", response_model=OrderListResponse, summary="获取客户订单列表")
async def get_customer_orders(
        customer_id: int,
        page: int = Query(1, ge=1, description="页码"),
        page_size: int = Query(20, ge=1, le=1000, description="每页数量")
):
    """获取指定客户的订单列表"""
    orders = await OrderService.get_orders_by_customer(customer_id, page, page_size)
    # 计算总数
    from base.plugins.order.models import Order
    total = await Order.filter(customer_id=customer_id).count()

    # 转换为字典列表确保datetime字段被正确格式化
    order_list = []
    for order in orders:
        if hasattr(order, 'to_dict'):
            order_dict = await order.to_dict()
        elif hasattr(order, 'dict'):
            order_dict = order.dict()
        else:
            order_dict = dict(order)
        order_list.append(order_dict)

    return SuccessResponse(data={"total": total, "items": order_list}, msg="获取客户订单列表成功")


@order_router.get("/", response_model=OrderListResponse, summary="获取所有订单列表")
async def get_all_orders(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=1000, description="每页数量"),
    order_no: Optional[str] = Query(None, description="订单号"),
    customer_name: Optional[str] = Query(None, description="客户名称"),
    product_name: Optional[str] = Query(None, description="产品名称")
):
    """获取所有订单列表（分页）"""
    # 如果有筛选条件，可以在这里添加过滤逻辑
    # 目前先忽略筛选条件，返回所有订单
    orders = await OrderService.get_all_orders(page, page_size)
    # 计算总数
    from base.plugins.order.models import Order
    total = await Order.all().count()

    # 转换为字典列表确保datetime字段被正确格式化
    order_list = []
    for order in orders:
        if hasattr(order, 'to_dict'):
            order_dict = await order.to_dict()
        elif hasattr(order, 'dict'):
            order_dict = order.dict()
        else:
            order_dict = dict(order)
        order_list.append(order_dict)

    return SuccessResponse(data={"total": total, "items": order_list}, msg="获取所有订单列表成功")


@order_router.get("/list", response_model=OrderListResponse, summary="获取所有订单列表(别名路由)")
async def get_all_orders_alias(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=1000, description="每页数量"),
    order_no: Optional[str] = Query(None, description="订单号"),
    customer_name: Optional[str] = Query(None, description="客户名称"),
    product_name: Optional[str] = Query(None, description="产品名称")
):
    """获取所有订单列表（分页）- 别名路由"""
    return await get_all_orders(page=page, page_size=page_size, order_no=order_no, customer_name=customer_name, product_name=product_name)


@order_router.delete("/batch", summary="批量删除订单")
async def batch_delete_order(request_data: dict):
    """批量删除订单"""
    try:
        from base.plugins.order.models import Order

        ids = request_data.get("ids", [])
        if not ids:
            raise HTTPException(status_code=400, detail="请选择要删除的订单")

        success_count = 0
        for order_id in ids:
            order = await Order.get_or_none(id=order_id)
            if order:
                await order.delete()
                success_count += 1

        return SuccessResponse(data={"deleted": success_count, "total": len(ids)}, msg=f"成功删除{success_count}/{len(ids)}个订单")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="批量删除订单失败")


# ============ 参数化路由（必须放在最后） ============

@order_router.get("/{order_id}", response_model=OrderOut, summary="获取订单详情")
async def get_order(order_id: int):
    """根据订单ID获取订单详情"""
    order = await OrderService.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    # 转换为字典确保datetime字段被正确格式化
    if hasattr(order, 'to_dict'):
        order_dict = await order.to_dict()
    elif hasattr(order, 'dict'):
        order_dict = order.dict()
    else:
        order_dict = dict(order)
    return SuccessResponse(data=order_dict, msg="获取订单详情成功")


@order_router.put("/{order_id}", response_model=OrderOut, summary="更新订单信息")
async def update_order(order_id: int, order_update: OrderUpdateRequest):
    """更新订单信息

    - **payment_status**: 支付状态（可选）
    - **remark**: 订单备注（可选）
    """
    # 检查订单是否存在
    order = await OrderService.get_order_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 更新订单状态
    update_data = order_update.model_dump(exclude_unset=True)

    if "payment_status" in update_data:
        success = await OrderService.update_payment_status(
            order_id=order_id,
            status=update_data["payment_status"]
        )
        if not success:
            raise HTTPException(status_code=500, detail="更新支付状态失败")

    if "remark" in update_data:
        from base.plugins.order.models import Order
        await Order.filter(id=order_id).update(remark=update_data["remark"])

    # 重新获取更新后的订单
    updated_order = await OrderService.get_order_by_id(order_id)
    # 转换为字典确保datetime字段被正确格式化
    if hasattr(updated_order, 'to_dict'):
        order_dict = await updated_order.to_dict()
    elif hasattr(updated_order, 'dict'):
        order_dict = updated_order.dict()
    else:
        order_dict = dict(updated_order)
    return SuccessResponse(data=order_dict, msg="更新订单信息成功")


@order_router.delete("/{order_id}", summary="删除订单")
async def delete_order(order_id: int):
    """删除订单"""
    try:
        from base.plugins.order.models import Order
        order = await Order.get_or_none(id=order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        await order.delete()
        return SuccessResponse(msg="订单删除成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="删除订单失败")


@order_router.patch("/{order_id}/status", summary="更新订单状态")
async def update_order_status_only(order_id: int, status_data: dict):
    """更新订单状态（别名路由）"""
    try:
        order = await OrderService.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        status = status_data.get("status")
        if status:
            success = await OrderService.update_order_status(order_id, status)
            if not success:
                raise HTTPException(status_code=500, detail="更新订单状态失败")

        updated_order = await OrderService.get_order_by_id(order_id)
        if hasattr(updated_order, 'to_dict'):
            order_dict = await updated_order.to_dict()
        elif hasattr(updated_order, 'dict'):
            order_dict = updated_order.dict()
        else:
            order_dict = dict(updated_order)
        return SuccessResponse(data=order_dict, msg="订单状态更新成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="更新订单状态失败")


@order_router.patch("/{order_id}/payment-status", summary="更新支付状态")
async def update_payment_status_only(order_id: int, payment_data: dict):
    """更新支付状态（别名路由）"""
    try:
        order = await OrderService.get_order_by_id(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="订单不存在")

        status = payment_data.get("payment_status")
        if status is not None:
            success = await OrderService.update_payment_status(
                order_id=order_id,
                status=status,
                payment_method=payment_data.get("payment_method"),
                transaction_id=payment_data.get("transaction_id")
            )
            if not success:
                raise HTTPException(status_code=500, detail="更新支付状态失败")

        updated_order = await OrderService.get_order_by_id(order_id)
        if hasattr(updated_order, 'to_dict'):
            order_dict = await updated_order.to_dict()
        elif hasattr(updated_order, 'dict'):
            order_dict = updated_order.dict()
        else:
            order_dict = dict(updated_order)
        return SuccessResponse(data=order_dict, msg="支付状态更新成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="更新支付状态失败")
