from fastapi import APIRouter
from . import audit_log, data_change_log, login_log, audit_config

router = APIRouter()

router.include_router(audit_log.audit_log_router, prefix="/audit-logs", tags=["审计日志"])
router.include_router(data_change_log.data_change_log_router, prefix="/data-changes", tags=["数据变更日志"])
router.include_router(login_log.login_log_router, prefix="/login-logs", tags=["登录日志"])
router.include_router(audit_config.audit_config_router, prefix="/audit-configs", tags=["审计配置"])
