from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from datetime import datetime

from base.plugins.audit.schemas.audit_log import (
    AuditLogResponse,
    AuditLogUpdate,
    AuditLogQuery,
    InputLayerLogResponse,
    DecisionLayerLogResponse,
    ExecutionLayerLogResponse,
    OutputLayerLogResponse,
    SystemLayerLogResponse,
    AuditReportResponse,
    RiskAuditRecordResponse,
    RiskAuditRecordUpdate,
    FullTraceResponse
)
from base.plugins.audit.services.audit_service import (
    AuditLogService,
    AuditTraceService,
    InputLayerService,
    DecisionLayerService,
    ExecutionLayerService,
    OutputLayerService,
    SystemLayerService,
    AuditReportService,
    RiskAuditService
)
from base.core.users.services.user_service import UserService
from base.common.security import get_current_user_id
from base.common.response import SuccessResponse, ErrorResponse

audit_log_router = APIRouter()


# ============ 全链路追踪API ============

@audit_log_router.get("/trace/{trace_id}")
async def get_full_trace(
    trace_id: str,
    current_user_id: int = Depends(get_current_user_id)
):
    """获取完整的追踪链路"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)
    
    trace = await AuditTraceService.get_full_trace(trace_id)
    return SuccessResponse(data=trace.model_dump())


# ============ 审计日志API ============

@audit_log_router.get("/audit-logs/list")
async def get_audit_log_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    trace_id: Optional[str] = Query(None, description="追踪ID"),
    username: Optional[str] = Query(None, description="用户名"),
    module: Optional[str] = Query(None, description="模块"),
    operation: Optional[str] = Query(None, description="操作"),
    method: Optional[str] = Query(None, description="请求方法"),
    level: Optional[str] = Query(None, description="审计级别"),
    status: Optional[str] = Query(None, description="审计状态"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    ip_address: Optional[str] = Query(None, description="IP地址"),
    current_user_id: int = Depends(get_current_user_id),
):
    """获取审计日志列表"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    logs, total = await AuditLogService.get_log_list(
        page=page,
        page_size=page_size,
        trace_id=trace_id,
        username=username,
        module=module,
        operation=operation,
        method=method,
        level=level,
        status=status,
        start_time=start_time,
        end_time=end_time,
        ip_address=ip_address,
    )

    log_list = []
    for log in logs:
        log_dict = await log.to_dict()
        log_list.append(log_dict)

    response_data = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": log_list,
    }

    return SuccessResponse(data=response_data)


@audit_log_router.get("/audit-logs/{log_id}")
async def get_audit_log(
    log_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取审计日志详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    log = await AuditLogService.get_log_by_id(log_id)
    if not log:
        return ErrorResponse(msg="审计日志不存在", status_code=status.HTTP_404_NOT_FOUND)

    log_dict = await log.to_dict()
    return SuccessResponse(data=log_dict)


@audit_log_router.put("/audit-logs/{log_id}")
async def update_audit_log(
    log_id: int,
    data: AuditLogUpdate,
    current_user_id: int = Depends(get_current_user_id),
):
    """更新审计日志（审核）"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    log = await AuditLogService.update_log(log_id, data, review_user_id=current_user_id)
    if not log:
        return ErrorResponse(msg="审计日志不存在", status_code=status.HTTP_404_NOT_FOUND)

    log_dict = await log.to_dict()
    return SuccessResponse(data=log_dict, msg="审核成功")


@audit_log_router.delete("/audit-logs/cleanup")
async def cleanup_old_logs(
    days: int = Query(90, ge=1, description="保留天数"),
    current_user_id: int = Depends(get_current_user_id),
):
    """清理旧审计日志"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    deleted_count = await AuditLogService.delete_old_logs(days)
    return SuccessResponse(data={"deleted_count": deleted_count}, msg=f"已清理 {deleted_count} 条旧日志")


@audit_log_router.get("/audit-logs/statistics/overview")
async def get_audit_statistics(
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user_id: int = Depends(get_current_user_id),
):
    """获取审计统计信息"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    statistics = await AuditLogService.get_statistics(start_time=start_time, end_time=end_time)
    return SuccessResponse(data=statistics)


# ============ 各层审计日志API ============

@audit_log_router.get("/input-layers/{log_id}")
async def get_input_layer_log(
    log_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取输入层日志详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    log = await InputLayerService.get_log_by_id(log_id)
    if not log:
        return ErrorResponse(msg="输入层日志不存在", status_code=status.HTTP_404_NOT_FOUND)

    log_dict = await log.to_dict()
    return SuccessResponse(data=log_dict)


@audit_log_router.get("/decision-layers/{log_id}")
async def get_decision_layer_log(
    log_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取决策层日志详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    log = await DecisionLayerService.get_log_by_id(log_id)
    if not log:
        return ErrorResponse(msg="决策层日志不存在", status_code=status.HTTP_404_NOT_FOUND)

    log_dict = await log.to_dict()
    return SuccessResponse(data=log_dict)


@audit_log_router.get("/execution-layers/{log_id}")
async def get_execution_layer_log(
    log_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取执行层日志详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    log = await ExecutionLayerService.get_log_by_id(log_id)
    if not log:
        return ErrorResponse(msg="执行层日志不存在", status_code=status.HTTP_404_NOT_FOUND)

    log_dict = await log.to_dict()
    return SuccessResponse(data=log_dict)


@audit_log_router.get("/output-layers/{log_id}")
async def get_output_layer_log(
    log_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取输出层日志详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    log = await OutputLayerService.get_log_by_id(log_id)
    if not log:
        return ErrorResponse(msg="输出层日志不存在", status_code=status.HTTP_404_NOT_FOUND)

    log_dict = await log.to_dict()
    return SuccessResponse(data=log_dict)


@audit_log_router.get("/system-layers/{log_id}")
async def get_system_layer_log(
    log_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取系统层日志详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    log = await SystemLayerService.get_log_by_id(log_id)
    if not log:
        return ErrorResponse(msg="系统层日志不存在", status_code=status.HTTP_404_NOT_FOUND)

    log_dict = await log.to_dict()
    return SuccessResponse(data=log_dict)


# ============ 审计报告API ============

@audit_log_router.get("/reports/list")
async def get_audit_report_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    report_type: Optional[str] = Query(None, description="报告类型"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user_id: int = Depends(get_current_user_id),
):
    """获取审计报告列表"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    reports, total = await AuditReportService.get_report_list(
        page=page,
        page_size=page_size,
        report_type=report_type,
        start_time=start_time,
        end_time=end_time
    )

    report_list = []
    for report in reports:
        report_dict = await report.to_dict()
        report_list.append(report_dict)

    response_data = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": report_list,
    }

    return SuccessResponse(data=response_data)


@audit_log_router.get("/reports/{report_id}")
async def get_audit_report(
    report_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取审计报告详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    report = await AuditReportService.get_report_by_id(report_id)
    if not report:
        return ErrorResponse(msg="审计报告不存在", status_code=status.HTTP_404_NOT_FOUND)

    report_dict = await report.to_dict()
    return SuccessResponse(data=report_dict)


@audit_log_router.post("/reports/generate/compliance")
async def generate_compliance_report(
    start_time: datetime,
    end_time: datetime,
    current_user_id: int = Depends(get_current_user_id),
):
    """生成合规审计报告"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    report = await AuditReportService.generate_compliance_report(
        start_time=start_time,
        end_time=end_time,
        generated_by=current_user_id,
        generated_by_name=current_user.username
    )

    report_dict = await report.to_dict()
    return SuccessResponse(data=report_dict, msg="合规审计报告生成成功")


@audit_log_router.post("/reports/generate/risk")
async def generate_risk_report(
    start_time: datetime,
    end_time: datetime,
    current_user_id: int = Depends(get_current_user_id),
):
    """生成风险审计报告"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    report = await AuditReportService.generate_risk_report(
        start_time=start_time,
        end_time=end_time,
        generated_by=current_user_id,
        generated_by_name=current_user.username
    )

    report_dict = await report.to_dict()
    return SuccessResponse(data=report_dict, msg="风险审计报告生成成功")


# ============ 风险审计API ============

@audit_log_router.get("/risks/list")
async def get_risk_record_list(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    trace_id: Optional[str] = Query(None, description="追踪ID"),
    risk_type: Optional[str] = Query(None, description="风险类型"),
    risk_level: Optional[str] = Query(None, description="风险级别"),
    status: Optional[str] = Query(None, description="状态"),
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    current_user_id: int = Depends(get_current_user_id),
):
    """获取风险记录列表"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    records, total = await RiskAuditService.get_record_list(
        page=page,
        page_size=page_size,
        trace_id=trace_id,
        risk_type=risk_type,
        risk_level=risk_level,
        status=status,
        start_time=start_time,
        end_time=end_time
    )

    record_list = []
    for record in records:
        record_dict = await record.to_dict()
        record_list.append(record_dict)

    response_data = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": record_list,
    }

    return SuccessResponse(data=response_data)


@audit_log_router.get("/risks/{record_id}")
async def get_risk_record(
    record_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    """获取风险记录详情"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    record = await RiskAuditService.get_record_by_id(record_id)
    if not record:
        return ErrorResponse(msg="风险记录不存在", status_code=status.HTTP_404_NOT_FOUND)

    record_dict = await record.to_dict()
    return SuccessResponse(data=record_dict)


@audit_log_router.put("/risks/{record_id}")
async def update_risk_record(
    record_id: int,
    data: RiskAuditRecordUpdate,
    current_user_id: int = Depends(get_current_user_id),
):
    """更新风险记录"""
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="无权限执行此操作", status_code=status.HTTP_403_FORBIDDEN)

    record = await RiskAuditService.update_record(record_id, data)
    if not record:
        return ErrorResponse(msg="风险记录不存在", status_code=status.HTTP_404_NOT_FOUND)

    record_dict = await record.to_dict()
    return SuccessResponse(data=record_dict, msg="风险记录更新成功")
