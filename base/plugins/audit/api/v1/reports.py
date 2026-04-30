from fastapi import APIRouter, Depends, Query, status, Body
from typing import Optional, List, Dict, Any
from datetime import datetime

from base.plugins.audit.models.audit_log import AuditReport, AuditLog, RiskAuditRecord, LoginLog
from base.core.users.services.user_service import UserService
from base.common.security import get_current_user_id
from base.common.response import SuccessResponse, ErrorResponse

reports_router = APIRouter(prefix="/reports", tags=["audit reports"])


@reports_router.get("/list")
async def get_report_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user_id: int = Depends(get_current_user_id),
):
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="no permission", status_code=status.HTTP_403_FORBIDDEN)

    query = AuditReport.all()

    if report_type:
        query = query.filter(report_type=report_type)
    if status:
        query = query.filter(status=status)
    if start_time:
        query = query.filter(created_at__gte=start_time)
    if end_time:
        query = query.filter(created_at__lte=end_time)

    total = await query.count()
    offset = (page - 1) * page_size
    reports = await query.offset(offset).limit(page_size).order_by("-created_at")

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


@reports_router.get("/{report_id}")
async def get_report_detail(
    report_id: int,
    current_user_id: int = Depends(get_current_user_id),
):
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="no permission", status_code=status.HTTP_403_FORBIDDEN)

    report = await AuditReport.get_or_none(id=report_id)
    if not report:
        return ErrorResponse(msg="report not found", status_code=status.HTTP_404_NOT_FOUND)

    report_dict = await report.to_dict()
    return SuccessResponse(data=report_dict)


@reports_router.post("/generate/compliance")
async def generate_compliance_report(
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    current_user_id: int = Depends(get_current_user_id),
):
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="no permission", status_code=status.HTTP_403_FORBIDDEN)

    audit_logs_count = await AuditLog.filter(
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()
    
    risk_count = await RiskAuditRecord.filter(
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()
    
    login_count = await LoginLog.filter(
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()

    report_data = {
        "period": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        },
        "summary": {
            "total_audit_logs": audit_logs_count,
            "total_risk_records": risk_count,
            "total_login_records": login_count,
        },
        "compliance_status": "compliant",
        "issues_found": []
    }

    report = await AuditReport.create(
        report_type="compliance",
        report_name=f"compliance report {start_time.strftime('%Y-%m-%d')} - {end_time.strftime('%Y-%m-%d')}",
        start_time=start_time,
        end_time=end_time,
        report_data=report_data,
        summary="compliance report generated",
        generated_by=current_user_id,
        generated_by_name=current_user.username,
        status="generated"
    )

    report_dict = await report.to_dict()
    return SuccessResponse(data=report_dict, msg="report generated")


@reports_router.post("/generate/risk")
async def generate_risk_report(
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    current_user_id: int = Depends(get_current_user_id),
):
    current_user = await UserService.get_by_id(current_user_id)
    if not current_user or not current_user.is_superuser:
        return ErrorResponse(msg="no permission", status_code=status.HTTP_403_FORBIDDEN)

    critical_count = await RiskAuditRecord.filter(
        risk_level="critical",
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()
    
    high_count = await RiskAuditRecord.filter(
        risk_level="high",
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()
    
    medium_count = await RiskAuditRecord.filter(
        risk_level="medium",
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()
    
    low_count = await RiskAuditRecord.filter(
        risk_level="low",
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()

    open_count = await RiskAuditRecord.filter(
        status="open",
        created_at__gte=start_time, 
        created_at__lte=end_time
    ).count()

    report_data = {
        "period": {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        },
        "risk_summary": {
            "critical": critical_count,
            "high": high_count,
            "medium": medium_count,
            "low": low_count,
            "total": critical_count + high_count + medium_count + low_count,
            "open_count": open_count
        },
        "risk_trend": "stable",
        "recommendations": []
    }

    report = await AuditReport.create(
        report_type="risk",
        report_name=f"risk report {start_time.strftime('%Y-%m-%d')} - {end_time.strftime('%Y-%m-%d')}",
        start_time=start_time,
        end_time=end_time,
        report_data=report_data,
        summary="risk report generated",
        generated_by=current_user_id,
        generated_by_name=current_user.username,
        status="generated"
    )

    report_dict = await report.to_dict()
    return SuccessResponse(data=report_dict, msg="report generated")