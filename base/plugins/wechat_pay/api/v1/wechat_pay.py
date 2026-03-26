from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any
import xml.etree.ElementTree as ET
import hashlib
from datetime import datetime

router = APIRouter(prefix="/v1/pay/wechat", tags=["WeChat Pay"])

def get_wechat_config():
    """获取微信支付配置"""
    from base.common.config import config
    return {
        "app_id": config.get("aif2f.payment", "wechat_app_id", fallback=""),
        "mch_id": config.get("aif2f.payment", "wechat_mch_id", fallback=""),
        "api_key": config.get("aif2f.payment", "wechat_api_key", fallback=""),
        "notify_url": config.get("aif2f.payment", "wechat_notify_url", fallback="")
    }

def verify_wechat_sign(data: Dict[str, Any], api_key: str) -> bool:
    """验证微信支付签名"""
    sign = data.pop("sign", None)
    if not sign:
        return False

    # 过滤空值
    filtered = {k: v for k, v in data.items() if v != "" and v is not None}
    # 按key字典序排序
    sorted_params = sorted(filtered.items())
    # 拼接字符串
    sign_str = "&".join([f"{k}={v}" for k, v in sorted_params])
    sign_str += f"&key={api_key}"
    # MD5加密并转大写
    calculated_sign = hashlib.md5(sign_str.encode("utf-8")).hexdigest().upper()

    return calculated_sign == sign

def generate_response(return_code: str, return_msg: str) -> str:
    """生成微信支付响应XML"""
    xml_dict = {
        "return_code": return_code,
        "return_msg": return_msg
    }
    root = ET.Element("xml")
    for key, value in xml_dict.items():
        child = ET.SubElement(root, key)
        child.text = str(value)
    return ET.tostring(root, encoding="unicode")

# 微信支付服务
class WeChatPayService:
    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建微信支付订单（待集成微信SDK）"""
        cfg = get_wechat_config()

        # TODO: 集成微信支付SDK
        # 目前返回模拟数据用于测试
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "order_id": "wx" + datetime.now().strftime("%Y%m%d%H%M%S"),
                "prepay_id": "wx" + datetime.now().strftime("%Y%m%d%H%M%S") + "abcdef",
                "appid": cfg["app_id"] or "wx1234567890abcdef",
                "partnerid": cfg["mch_id"] or "1234567890",
                "package": "Sign=WXPay",
                "noncestr": "abcdef1234567890",
                "timestamp": int(datetime.now().timestamp()),
                "sign": "ABCDEF1234567890"
            }
        }

    async def query_order(self, order_id: str) -> Dict[str, Any]:
        """查询微信支付订单（待集成微信SDK）"""
        # TODO: 调用微信支付查询订单接口
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "order_id": order_id,
                "trade_state": "SUCCESS",
                "total_fee": 100,
                "transaction_id": "4200001234567890",
                "time_end": datetime.now().strftime("%Y%m%d%H%M%S")
            }
        }

    async def refund_order(self, refund_data: Dict[str, Any]) -> Dict[str, Any]:
        """微信支付退款（待集成微信SDK）"""
        # TODO: 调用微信支付退款接口
        return {
            "code": 0,
            "msg": "success",
            "data": {
                "refund_id": "500001234567890",
                "out_refund_no": refund_data.get("out_refund_no"),
                "refund_fee": refund_data.get("refund_fee"),
                "total_fee": refund_data.get("total_fee"),
                "refund_status": "SUCCESS"
            }
        }

@router.post("/orders", response_model=Dict[str, Any])
async def create_wechat_order(order_data: Dict[str, Any]):
    """创建微信支付订单"""
    try:
        service = WeChatPayService()
        result = await service.create_order(order_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/orders/{order_id}", response_model=Dict[str, Any])
async def query_wechat_order(order_id: str):
    """查询微信支付订单"""
    try:
        service = WeChatPayService()
        result = await service.query_order(order_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refunds", response_model=Dict[str, Any])
async def refund_wechat_order(refund_data: Dict[str, Any]):
    """微信支付退款"""
    try:
        service = WeChatPayService()
        result = await service.refund_order(refund_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notify")
async def wechat_pay_notify(request_data: str):
    """
    微信支付回调通知处理

    微信支付成功后会调用此接口通知支付结果
    需要验证签名并更新订单状态
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        cfg = get_wechat_config()

        # 解析XML
        try:
            root = ET.fromstring(request_data)
            notify_data = {child.tag: child.text for child in root}
        except Exception as e:
            logger.error(f"解析XML失败: {str(e)}")
            return generate_response("FAIL", "XML格式错误")

        logger.info(f"收到微信支付回调: {notify_data}")

        # 验证签名
        if not verify_wechat_sign(notify_data.copy(), cfg["api_key"]):
            logger.error("签名验证失败")
            return generate_response("FAIL", "签名验证失败")

        # 检查返回码
        return_code = notify_data.get("return_code")
        result_code = notify_data.get("result_code")

        if return_code != "SUCCESS" or result_code != "SUCCESS":
            logger.error(f"支付失败: return_code={return_code}, result_code={result_code}")
            return generate_response("FAIL", "支付失败")

        # 获取订单信息
        out_trade_no = notify_data.get("out_trade_no")  # 商户订单号
        transaction_id = notify_data.get("transaction_id")  # 微信支付订单号
        total_fee = notify_data.get("total_fee")  # 订单金额（分）
        time_end = notify_data.get("time_end")  # 支付完成时间

        if not all([out_trade_no, transaction_id, total_fee]):
            logger.error("回调数据不完整")
            return generate_response("FAIL", "数据不完整")

        # 处理支付回调
        from base.plugins.customer.services.payment_service import wechat_pay_service

        # 转换金额单位（分 -> 元）
        amount = float(total_fee) / 100

        # 调用支付服务处理回调
        success = await wechat_pay_service.process_payment_callback(
            order_no=out_trade_no,
            transaction_id=transaction_id,
            transaction_type="wechat_pay",
            amount=amount,
            notify_data=notify_data
        )

        if success:
            logger.info(f"订单 {out_trade_no} 支付成功，已更新状态")
            return generate_response("SUCCESS", "OK")
        else:
            logger.error(f"订单 {out_trade_no} 处理失败")
            return generate_response("FAIL", "订单处理失败")

    except Exception as e:
        logger.error(f"处理微信支付回调异常: {str(e)}", exc_info=True)
        return generate_response("FAIL", str(e))
