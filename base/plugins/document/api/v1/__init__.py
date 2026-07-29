"""
文档管理 API v1 路由聚合
"""
from fastapi import APIRouter
from base.plugins.document.api.v1.category_router import category_router
from base.plugins.document.api.v1.document_router import document_router
from base.plugins.document.api.v1.version_router import version_router
from base.plugins.document.api.v1.preview_router import preview_router

document_v1_router = APIRouter()

document_v1_router.include_router(category_router, prefix="/categories", tags=["文档分类"])
document_v1_router.include_router(document_router, prefix="/documents", tags=["文档管理"])
document_v1_router.include_router(version_router, prefix="/versions", tags=["文档版本"])
document_v1_router.include_router(preview_router, prefix="/preview", tags=["文档预览"])
