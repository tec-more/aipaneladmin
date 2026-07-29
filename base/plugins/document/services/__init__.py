"""
文档管理 Service 模块初始化
"""
from base.plugins.document.services.document_service import (
    CategoryService,
    DocumentService,
    VersionService,
    PreviewService,
)

__all__ = [
    "CategoryService",
    "DocumentService",
    "VersionService",
    "PreviewService",
]
