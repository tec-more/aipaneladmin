"""
七相支付API路由
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
import logging

from base.common.response import SuccessResponse
from base.plugins.qixiang_pay.schemas.qixiang_schema import CreateOrderIn, CreateOrderOut, QueryOrderOut
from base.plugins.qixiang_pay.services.qixiang_service import QixiangPayService

logger = logging.getLogger(__name__)

# 创建路由实例
# 注意：插件管理器会查找 qixiang_pay_router 变量名
# 路由前缀已在 manifest.json 的 route_prefix 中定义，此处不需要再设置
qixiang_pay_router = APIRouter(
    tags=["七相支付"],
    responses={404: {"description": "Not found"}},
)

# 为了向后兼容，也提供 router 别名
router = qixiang_pay_router


@qixiang_pay_router.post("/create", response_model=CreateOrderOut, summary="创建七相支付订单")
async def create_order(order_data: CreateOrderIn):
    """
    创建七相支付订单

    支持支付宝和微信支付（自适应）

    - **order_no**: 商户订单号（必填）
    - **pay_type**: 支付类型，alipay或wxpay（必填）
    - **amount**: 支付金额，单位元（必填）
    - **subject**: 商品名称（必填）
    - **client_ip**: 客户端IP（可选，默认127.0.0.1）
    - **param**: 业务扩展参数（可选）

    返回:
    - **trade_no**: 七相订单号
    - **payurl**: 支付跳转URL（PC端扫码/手机端H5）
    - **qrcode**: 二维码链接（如有）
    """
    try:
        service = QixiangPayService()
        result = await service.create_order(order_data.model_dump())

        logger.info(f"创建七相支付订单成功: {order_data.order_no}")

        return SuccessResponse(data=result, msg="创建订单成功")

    except ValueError as e:
        logger.error(f"创建七相支付订单失败（参数错误）: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建七相支付订单异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="创建订单失败")


@qixiang_pay_router.get("/query/{order_no}", response_model=QueryOrderOut, summary="查询七相支付订单")
async def query_order(order_no: str):
    """
    查询七相支付订单状态

    用于前端轮询查询支付状态

    - **order_no**: 商户订单号

    返回:
    - **status**: 支付状态（success/pending/failed）
    - **trade_no**: 七相订单号
    - **amount**: 订单金额
    """
    try:
        service = QixiangPayService()
        result = await service.query_order(order_no)

        logger.info(f"查询七相支付订单成功: {order_no}, 状态: {result.get('status')}")

        return SuccessResponse(data=result, msg="查询成功")

    except ValueError as e:
        logger.error(f"查询七相支付订单失败（参数错误）: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"查询七相支付订单异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询订单失败")


@qixiang_pay_router.post("/notify", summary="七相支付异步回调")
async def payment_notify(request: Request):
    """
    七相支付异步回调通知

    接收七相支付的服务器异步通知，验证签名并更新订单状态

    注意：
    - 必须返回纯文本"success"表示接收成功
    - 七相支付会多次重试直到收到success
    - 需要验证签名确保通知真实性
    """
    try:
        # 获取回调数据（form-data格式）
        notify_data = dict(await request.form())

        logger.info(f"收到七相支付回调通知: {notify_data.get('out_trade_no')}")

        # 处理回调
        service = QixiangPayService()
        success = await service.process_notify(notify_data)

        if success:
            logger.info(f"七相支付回调处理成功: {notify_data.get('out_trade_no')}")
            # 必须返回纯文本"success"
            return PlainTextResponse(content="success")
        else:
            logger.error(f"七相支付回调处理失败: {notify_data.get('out_trade_no')}")
            return PlainTextResponse(content="fail", status_code=400)

    except ValueError as e:
        logger.error(f"七相支付回调验证失败: {str(e)}")
        return PlainTextResponse(content="fail", status_code=400)

    except Exception as e:
        logger.error(f"处理七相支付回调异常: {str(e)}", exc_info=True)
        return PlainTextResponse(content="fail", status_code=500)


@qixiang_pay_router.get("/return", summary="七相支付跳转通知")
async def payment_return():
    """
    七相支付页面跳转通知

    用户支付完成后跳转回来的页面
    支付结果以异步通知为准，跳转通知仅供参考
    """
    # 这里可以返回一个前端页面，展示支付结果
    # 实际支付状态应该通过查询接口确认
    return SuccessResponse(data={
        "message": "支付完成，正在跳转...",
        "notice": "实际支付状态请通过查询接口确认"
    }, msg="支付跳转")
