"""增强的错误日志配置"""
import traceback
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


async def log_exception(exc: Exception, request: Request = None):
    """记录异常详细信息到控制台"""
    print("\n" + "="*80)
    print("[ERROR] 发生错误")
    print("="*80)

    if request:
        print(f"[INFO] 请求信息:")
        print(f"   方法: {request.method}")
        print(f"   URL: {request.url}")
        print(f"   客户端: {request.client}")

    print(f"\n[INFO] 错误类型: {type(exc).__name__}")
    print(f"[INFO] 错误信息: {str(exc)}")

    print(f"\n[TRACEBACK] 错误堆栈:")
    traceback.print_exc()

    print("="*80 + "\n")


async def DoesNotExistHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理对象不存在异常"""
    await log_exception(exc, req)

    content = dict(
        code=404,
        msg=f"对象不存在: {str(exc)}",
    )
    return JSONResponse(content=content, status_code=404)


async def IntegrityHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理数据库完整性异常"""
    await log_exception(exc, req)

    content = dict(
        code=500,
        msg=f"数据完整性错误: {str(exc)}",
    )
    return JSONResponse(content=content, status_code=500)


async def HttpExcHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理HTTP异常"""
    # HTTPException 通常不需要完整堆栈，只记录基本信息
    print(f"\n[WARNING] HTTP异常: {exc.status_code} - {exc.detail}")
    if req:
        print(f"   请求: {req.method} {req.url}")

    content = dict(code=exc.status_code, msg=exc.detail, data=None)
    return JSONResponse(content=content, status_code=exc.status_code)


async def RequestValidationHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理请求验证异常"""
    await log_exception(exc, req)

    # 提取详细的验证错误信息
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(f"{field}: {error['msg']}")

    error_detail = "; ".join(errors)

    print(f"\n[ERROR] 请求参数验证失败:")
    print(f"   {error_detail}")

    content = dict(
        code=422,
        msg=f"请求参数验证失败: {error_detail}",
        data={"errors": exc.errors()}
    )
    return JSONResponse(content=content, status_code=422)


async def ResponseValidationHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理响应验证异常"""
    await log_exception(exc, req)

    content = dict(code=500, msg=f"响应验证错误: {str(exc)}")
    return JSONResponse(content=content, status_code=500)


async def GeneralExceptionHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理所有其他未捕获的异常"""
    await log_exception(exc, req)
    
    import traceback
    tb_str = traceback.format_exc()

    content = dict(
        code=500,
        msg=f"服务器内部错误: {type(exc).__name__}: {str(exc)}",
        data={"error": str(exc), "traceback": tb_str} if req.app.debug else None
    )
    return JSONResponse(content=content, status_code=500)


async def NeedApprovalHandle(req: Request, exc: Exception) -> JSONResponse:
    """处理审批门禁抛出的 NeedApprovalError，返回与原中间件一致的 40001 响应。"""
    # 不打印完整堆栈，仅记录基本信息
    content = dict(
        code=40001,
        msg="该操作需要审批",
        require_approval=True,
        instance_id=getattr(exc, "instance_id", None),
        flow_id=getattr(exc, "flow_id", None),
        flow_name=getattr(exc, "flow_name", None),
        business_type=getattr(exc, "business_type", None),
        model=getattr(exc, "model", None),
        action=getattr(exc, "action", None),
    )
    return JSONResponse(content=content, status_code=400)


def register_exceptions_with_logging(app):
    """注册带详细日志的异常处理器"""
    from fastapi.exceptions import HTTPException, RequestValidationError, ResponseValidationError
    from tortoise.exceptions import DoesNotExist, IntegrityError

    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)

    # 添加通用异常处理器（捕获所有异常）
    app.add_exception_handler(Exception, GeneralExceptionHandle)

    # 审批门禁异常（需注册在通用 Exception 处理器之前以获得更具体的匹配）
    try:
        from base.plugins.approval.services.approval_gate import NeedApprovalError
        app.add_exception_handler(NeedApprovalError, NeedApprovalHandle)
    except Exception as e:
        print(f"[WARN] 审批门禁异常处理器注册失败: {e}")

    print("[OK] 已启用详细错误日志")
