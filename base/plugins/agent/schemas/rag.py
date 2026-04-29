"""
RAG (Retrieval-Augmented Generation) Schemas
"""
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class RAGKnowledgeBaseBase(BaseModel):
    """知识库基础schema"""
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    status: str = Field(default="active", description="状态: active/inactive")
    vector_dimension: int = Field(default=1024, description="向量维度")
    config: Optional[dict] = Field(None, description="知识库配置")
    embedding_model_id: Optional[int] = Field(None, description="关联的Embedding模型ID")


class RAGKnowledgeBaseCreate(RAGKnowledgeBaseBase):
    """创建知识库schema"""
    pass


class RAGKnowledgeBaseUpdate(BaseModel):
    """更新知识库schema"""
    name: Optional[str] = Field(None, description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    status: Optional[str] = Field(None, description="状态: active/inactive")
    config: Optional[dict] = Field(None, description="知识库配置")


class RAGKnowledgeBaseResponse(RAGKnowledgeBaseBase):
    """知识库响应schema"""
    id: int = Field(..., description="知识库ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    document_count: int = Field(default=0, description="文档数量")

    class Config:
        from_attributes = True


class RAGDocumentBase(BaseModel):
    """文档基础schema"""
    knowledge_base_id: int = Field(..., description="知识库ID")
    title: str = Field(..., description="文档标题")
    file_name: Optional[str] = Field(None, description="文件名")
    file_type: Optional[str] = Field(None, description="文件类型")
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    file_path: Optional[str] = Field(None, description="文件存储路径")
    content: Optional[str] = Field(None, description="文档内容")
    metadata: Optional[dict] = Field(None, description="元数据")


class RAGDocumentCreate(RAGDocumentBase):
    """创建文档schema"""
    pass


class RAGDocumentUpdate(BaseModel):
    """更新文档schema"""
    title: Optional[str] = Field(None, description="文档标题")
    content: Optional[str] = Field(None, description="文档内容")
    metadata: Optional[dict] = Field(None, description="元数据")


class RAGDocumentResponse(RAGDocumentBase):
    """文档响应schema"""
    id: int = Field(..., description="文档ID")
    status: str = Field(..., description="状态: pending/processing/completed/failed")
    chunk_count: int = Field(default=0, description="分块数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class RAGDocumentChunkBase(BaseModel):
    """文档片段基础schema"""
    document_id: int = Field(..., description="文档ID")
    chunk_index: int = Field(..., description="分块索引")
    content: str = Field(..., description="分块内容")
    metadata: Optional[dict] = Field(None, description="元数据")


class RAGDocumentChunkCreate(RAGDocumentChunkBase):
    """创建文档片段schema"""
    pass


class RAGDocumentChunkResponse(RAGDocumentChunkBase):
    """文档片段响应schema"""
    id: int = Field(..., description="片段ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    similarity: Optional[float] = Field(None, description="相似度(检索时返回)")

    class Config:
        from_attributes = True


class RAGSearchRequest(BaseModel):
    """RAG搜索请求schema"""
    knowledge_base_id: int = Field(..., description="知识库ID")
    query: str = Field(..., description="搜索查询")
    top_k: int = Field(default=5, description="返回结果数量")
    similarity_threshold: Optional[float] = Field(None, description="相似度阈值")


class RAGSearchResponse(BaseModel):
    """RAG搜索响应schema"""
    query: str = Field(..., description="搜索查询")
    results: List[RAGDocumentChunkResponse] = Field(..., description="搜索结果")
    total: int = Field(..., description="总结果数")
