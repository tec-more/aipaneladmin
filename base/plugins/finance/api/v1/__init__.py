from fastapi import APIRouter

from .account_router import account_router
from .journal_router import journal_router
from .report_router import report_router

finance_api_router = APIRouter()

finance_api_router.include_router(account_router)
finance_api_router.include_router(journal_router)
finance_api_router.include_router(report_router)

__all__ = ["finance_api_router"]