"""
全局审批中间件
拦截配置了审批规则的业务操作（POST/PUT/DELETE），返回提示引导用户提交审批
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger
import json


# 中间件配置（供自动发现机制读取）
ENABLED = True
PRIORITY = 10  # 优先级较低，确保较早执行（在业务路由之前）


class ApprovalMiddleware(BaseHTTPMiddleware):
    """全局审批检查中间件"""

    # 排除的路径前缀（审批模块自身的API不需要拦截）
    EXCLUDE_PATH_PREFIXES = [
        "/api/v1/approval",
        "/v1/approval",
        "/api/v1/auth",
        "/v1/auth",
        "/docs",
        "/openapi",
        "/redoc",
        "/health",
        "/metrics",
        "/static",
    ]

    # 排除的方法（只拦截写操作）
    ALLOWED_METHODS = ["POST", "PUT", "DELETE", "PATCH"]

    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method

        # 排除特定路径
        if self._should_exclude(path):
            return await call_next(request)

        # 只检查写操作方法
        if method not in self.ALLOWED_METHODS:
            return await call_next(request)

        try:
            # 检查是否需要审批
            from base.plugins.approval.services.rule_service import RuleService
            check_result = await RuleService.check_approval_required(path, method)

            if check_result.get("require_approval"):
                logger.info(f"拦截需要审批的操作: {method} {path} -> 流程: {check_result.get('flow_name')}")

                # 返回特殊响应，前端拦截器会捕获并引导用户提交审批
                return JSONResponse(
                    status_code=400,
                    content={
                        "code": 40001,
                        "msg": "该操作需要审批",
                        "require_approval": True,
                        "flow_id": check_result.get("flow_id"),
                        "flow_name": check_result.get("flow_name"),
                        "business_type": check_result.get("business_type", ""),
                        "path": path,
                        "method": method
                    }
                )

        except Exception as e:
            # 中间件异常不应阻断正常业务，记录日志后放行
            logger.error(f"审批中间件检查失败: {e}")

        return await call_next(request)

    def _should_exclude(self, path: str) -> bool:
        """判断路径是否应该排除"""
        # 标准化路径（去掉 /api 前缀进行比较）
        normalized_path = path
        if normalized_path.startswith("/api"):
            normalized_path = normalized_path[4:]

        for prefix in self.EXCLUDE_PATH_PREFIXES:
            normalized_prefix = prefix
            if normalized_prefix.startswith("/api"):
                normalized_prefix = normalized_prefix[4:]

            if normalized_path.startswith(normalized_prefix):
                return True

        return False


def register_approval_middleware(app):
    """注册审批中间件"""
    app.add_middleware(ApprovalMiddleware)
    logger.info("审批中间件已注册")
