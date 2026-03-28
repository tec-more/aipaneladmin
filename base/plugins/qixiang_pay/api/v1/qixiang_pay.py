"""
七相支付API路由
"""
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse
from pydantic import ValidationError
import logging
import json

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


@qixiang_pay_router.post("/create-debug", summary="创建七相支付订单（调试模式）")
async def create_order_debug(request: Request):
    """
    调试模式：直接接收原始请求，不验证参数
    用于查看前端发送的原始数据
    """
    try:
        # 获取原始请求体
        body = await request.body()
        body_str = body.decode('utf-8')

        logger.info("=" * 60)
        logger.info("[七相支付 DEBUG] 原始请求信息:")
        logger.info("=" * 60)
        logger.info(f"请求头: {dict(request.headers)}")
        logger.info(f"请求体（原始）: {body_str}")

        # 尝试解析JSON
        try:
            body_json = json.loads(body_str)
            logger.info(f"请求体（JSON）: {json.dumps(body_json, indent=2, ensure_ascii=False)}")
        except:
            logger.warning("无法解析为JSON")

        logger.info("=" * 60)

        return SuccessResponse(data={
            "headers": dict(request.headers),
            "body_raw": body_str,
            "body_json": json.loads(body_str) if body_str else None
        }, msg="获取调试信息成功")

    except Exception as e:
        logger.error(f"[DEBUG] 错误: {e}", exc_info=True)
        return SuccessResponse(data={"error": str(e)}, msg="调试信息获取失败")


@qixiang_pay_router.post("/create", response_model=CreateOrderOut, summary="创建七相支付订单")
async def create_order(request: Request):
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
        # 先获取原始请求体用于调试
        body = await request.body()
        body_str = body.decode('utf-8')

        logger.info("=" * 60)
        logger.info("[七相支付] 收到创建订单请求")
        logger.info("=" * 60)
        logger.info(f"原始请求体: {body_str}")

        # 尝试解析JSON
        try:
            body_json = json.loads(body_str)
            logger.info(f"解析后的JSON:")
            for key, value in body_json.items():
                logger.info(f"  {key}: {value} (类型: {type(value).__name__})")
        except Exception as e:
            logger.error(f"JSON解析失败: {e}")

        # Pydantic 验证
        try:
            order_data = CreateOrderIn(**json.loads(body_str))
            logger.info(f"[SUCCESS] Pydantic 验证通过")
            logger.info(f"  order_no: {order_data.order_no}")
            logger.info(f"  pay_type: {order_data.pay_type}")
            logger.info(f"  amount: {order_data.amount}")
            logger.info(f"  subject: {order_data.subject}")
            logger.info(f"  client_ip: {order_data.client_ip}")
            logger.info(f"  param: {order_data.param}")
        except ValidationError as e:
            logger.error(f"[ERROR] Pydantic 验证失败!")
            logger.error(f"验证错误详情: {e.errors()}")
            error_details = []
            for error in e.errors():
                error_details.append({
                    "field": "->".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"]
                })
                logger.error(f"  字段: {'->'.join(str(loc) for loc in error['loc'])}")
                logger.error(f"  错误: {error['msg']}")
                logger.error(f"  类型: {error['type']}")
            logger.info("=" * 60)

            raise HTTPException(
                status_code=422,
                detail={
                    "msg": "参数验证失败",
                    "errors": error_details
                }
            )

        logger.info("=" * 60)

        service = QixiangPayService()
        result = await service.create_order(order_data.model_dump())

        logger.info(f"[SUCCESS] 创建七相支付订单成功: {order_data.order_no}")

        return SuccessResponse(data=result, msg="创建订单成功")

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"[ERROR] 创建七相支付订单失败（参数错误）: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[ERROR] 创建七相支付订单异常: {str(e)}", exc_info=True)
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
