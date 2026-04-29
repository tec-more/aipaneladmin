"""
RAG (Retrieval-Augmented Generation) 模型
"""
from tortoise import fields
from base.common.model import BaseModel, TimestampMixin
from base.common.pgvector import VectorField


class RAGKnowledgeBase(BaseModel, TimestampMixin):
    """RAG知识库模型"""
    name = fields.CharField(max_length=200, description="知识库名称")
    description = fields.TextField(null=True, description="知识库描述")
    status = fields.CharField(max_length=20, default="active", description="状态: active/inactive")
    vector_dimension = fields.IntField(default=1024, description="向量维度")
    config = fields.JSONField(null=True, description="知识库配置")
    
    # 搜索模式配置: llm_index, pgvector
    search_mode = fields.CharField(max_length=20, default="pgvector", description="搜索模式: llm_index, pgvector")
    
    embedding_model = fields.ForeignKeyField(
        "models.LLMModel",
        related_name="rag_knowledge_bases",
        on_delete=fields.SET_NULL,
        null=True,
        description="关联的Embedding模型"
    )

    class Meta:
        table = "rag_knowledge_base"

    def __str__(self):
        return self.name


class RAGDocument(BaseModel, TimestampMixin):
    """RAG文档模型"""
    knowledge_base = fields.ForeignKeyField(
        "models.RAGKnowledgeBase",
        related_name="documents",
        on_delete=fields.CASCADE,
        description="所属知识库"
    )
    title = fields.CharField(max_length=500, description="文档标题")
    file_name = fields.CharField(max_length=500, null=True, description="文件名")
    file_type = fields.CharField(max_length=50, null=True, description="文件类型")
    file_size = fields.BigIntField(null=True, description="文件大小(字节)")
    file_path = fields.CharField(max_length=1000, null=True, description="文件存储路径")
    content = fields.TextField(null=True, description="文档内容")
    status = fields.CharField(max_length=20, default="pending", description="状态: pending/processing/completed/failed")
    chunk_count = fields.IntField(default=0, description="分块数量")
    metadata = fields.JSONField(null=True, description="元数据")

    class Meta:
        table = "rag_document"

    def __str__(self):
        return self.title


class RAGDocumentChunk(BaseModel, TimestampMixin):
    """RAG文档片段模型（含向量）"""
    document = fields.ForeignKeyField(
        "models.RAGDocument",
        related_name="chunks",
        on_delete=fields.CASCADE,
        description="所属文档"
    )
    chunk_index = fields.IntField(description="分块索引")
    content = fields.TextField(description="分块内容")
    
    # VectorField: 使用 pgvector 格式存储向量
    vector = VectorField(dimension=1024, null=True, description="向量数据")
    
    metadata = fields.JSONField(null=True, description="元数据")
    node_id = fields.CharField(max_length=100, null=True, description="LlamaIndex Node ID")

    class Meta:
        table = "rag_document_chunk"

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"
