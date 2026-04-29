"""
RAG (Retrieval-Augmented Generation) Service
"""
import logging
import struct
import re
import os
from pathlib import Path
from typing import List, Optional
from fastapi import UploadFile
from base.plugins.agent.models.rag import (
    RAGKnowledgeBase,
    RAGDocument,
    RAGDocumentChunk
)
from base.plugins.agent.schemas.rag import (
    RAGKnowledgeBaseCreate,
    RAGKnowledgeBaseUpdate,
    RAGDocumentCreate,
    RAGDocumentUpdate,
    RAGDocumentChunkCreate
)

logger = logging.getLogger(__name__)


class TextSplitter:
    """文本切片器"""
    
    @staticmethod
    def split_by_paragraph(text: str) -> List[str]:
        """按段落分割"""
        paragraphs = re.split(r'\n\s*\n', text.strip())
        return [p.strip() for p in paragraphs if p.strip()]
    
    @staticmethod
    def split_by_sentence(text: str) -> List[str]:
        """按句子分割"""
        sentence_endings = r'[.!?。！？]'
        sentences = re.split(f'({sentence_endings})', text)
        result = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                result.append(sentences[i] + sentences[i + 1])
            else:
                result.append(sentences[i])
        return [s.strip() for s in result if s.strip()]


class VectorService:
    """向量服务"""

    VECTOR_DIMENSION = 1024

    @staticmethod
    def vector_to_bytes(vector: List[float]) -> bytes:
        """将向量列表转换为二进制数据"""
        if len(vector) != VectorService.VECTOR_DIMENSION:
            raise ValueError(f"向量维度必须为 {VectorService.VECTOR_DIMENSION}")
        return struct.pack(f'{VectorService.VECTOR_DIMENSION}f', *vector)

    @staticmethod
    def bytes_to_vector(data: bytes) -> List[float]:
        """将二进制数据转换为向量列表"""
        if len(data) != VectorService.VECTOR_DIMENSION * 4:
            raise ValueError(f"向量数据长度不正确")
        return list(struct.unpack(f'{VectorService.VECTOR_DIMENSION}f', data))

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """计算余弦相似度"""
        if len(v1) != len(v2):
            raise ValueError("向量维度不匹配")

        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class RAGService:
    """RAG服务"""

    @staticmethod
    async def create_knowledge_base(data: RAGKnowledgeBaseCreate) -> RAGKnowledgeBase:
        """创建知识库"""
        kb = await RAGKnowledgeBase.create(
            name=data.name,
            description=data.description,
            status=data.status,
            vector_dimension=data.vector_dimension,
            config=data.config,
            embedding_model_id=data.embedding_model_id
        )
        logger.info(f"创建知识库: {kb.name} (ID: {kb.id})")
        return kb

    @staticmethod
    async def get_knowledge_base(kb_id: int) -> Optional[RAGKnowledgeBase]:
        """获取知识库"""
        return await RAGKnowledgeBase.get_or_none(id=kb_id)

    @staticmethod
    async def list_knowledge_bases(skip: int = 0, limit: int = 100, name: str = "", status: str = "") -> List[RAGKnowledgeBase]:
        """列出知识库"""
        query = RAGKnowledgeBase.all()
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
        return await query.offset(skip).limit(limit).order_by("-created_at")

    @staticmethod
    async def count_knowledge_bases(name: str = "", status: str = "") -> int:
        """统计知识库数量"""
        query = RAGKnowledgeBase.all()
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
        return await query.count()

    @staticmethod
    async def update_knowledge_base(kb_id: int, data: RAGKnowledgeBaseUpdate) -> Optional[RAGKnowledgeBase]:
        """更新知识库"""
        kb = await RAGService.get_knowledge_base(kb_id)
        if not kb:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(kb, field, value)
        await kb.save()
        logger.info(f"更新知识库: {kb.name} (ID: {kb.id})")
        return kb

    @staticmethod
    async def delete_knowledge_base(kb_id: int) -> bool:
        """删除知识库"""
        kb = await RAGService.get_knowledge_base(kb_id)
        if not kb:
            return False
        await kb.delete()
        logger.info(f"删除知识库: {kb.name} (ID: {kb.id})")
        return True

    @staticmethod
    async def create_document(data: RAGDocumentCreate) -> RAGDocument:
        """创建文档"""
        doc = await RAGDocument.create(
            knowledge_base_id=data.knowledge_base_id,
            title=data.title,
            file_name=data.file_name,
            file_type=data.file_type,
            file_size=data.file_size,
            file_path=data.file_path,
            content=data.content,
            metadata=data.metadata
        )
        logger.info(f"创建文档: {doc.title} (ID: {doc.id})")
        return doc

    @staticmethod
    async def get_document(doc_id: int) -> Optional[RAGDocument]:
        """获取文档"""
        return await RAGDocument.get_or_none(id=doc_id)

    @staticmethod
    async def list_documents(kb_id: int, skip: int = 0, limit: int = 100, title: str = "", status: str = "") -> List[RAGDocument]:
        """列出文档"""
        query = RAGDocument.filter(knowledge_base_id=kb_id)
        if title:
            query = query.filter(title__icontains=title)
        if status:
            query = query.filter(status=status)
        return await query.offset(skip).limit(limit).order_by("-created_at")

    @staticmethod
    async def count_documents(kb_id: int, title: str = "", status: str = "") -> int:
        """统计文档数量"""
        query = RAGDocument.filter(knowledge_base_id=kb_id)
        if title:
            query = query.filter(title__icontains=title)
        if status:
            query = query.filter(status=status)
        return await query.count()

    @staticmethod
    async def update_document(doc_id: int, data: RAGDocumentUpdate) -> Optional[RAGDocument]:
        """更新文档"""
        doc = await RAGService.get_document(doc_id)
        if not doc:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doc, field, value)
        await doc.save()
        logger.info(f"更新文档: {doc.title} (ID: {doc.id})")
        return doc

    @staticmethod
    async def delete_document(doc_id: int) -> bool:
        """删除文档"""
        doc = await RAGService.get_document(doc_id)
        if not doc:
            return False
        await doc.delete()
        logger.info(f"删除文档: {doc.title} (ID: {doc.id})")
        return True

    @staticmethod
    async def create_chunk(data: RAGDocumentChunkCreate, vector: Optional[List[float]] = None) -> RAGDocumentChunk:
        """创建文档片段"""
        vector_bytes = None
        if vector:
            vector_bytes = VectorService.vector_to_bytes(vector)

        chunk = await RAGDocumentChunk.create(
            document_id=data.document_id,
            chunk_index=data.chunk_index,
            content=data.content,
            vector=vector_bytes,
            metadata=data.metadata
        )
        logger.info(f"创建文档片段: {chunk.id} (文档ID: {chunk.document_id})")
        return chunk

    @staticmethod
    async def get_chunk(chunk_id: int) -> Optional[RAGDocumentChunk]:
        """获取文档片段"""
        return await RAGDocumentChunk.get_or_none(id=chunk_id)

    @staticmethod
    async def list_chunks(doc_id: int, skip: int = 0, limit: int = 100) -> List[RAGDocumentChunk]:
        """列出文档片段"""
        return await RAGDocumentChunk.filter(document_id=doc_id).offset(skip).limit(limit).order_by("chunk_index")

    @staticmethod
    async def delete_chunk(chunk_id: int) -> bool:
        """删除文档片段"""
        chunk = await RAGService.get_chunk(chunk_id)
        if not chunk:
            return False
        await chunk.delete()
        logger.info(f"删除文档片段: {chunk.id}")
        return True

    @staticmethod
    async def _get_embedding_service(knowledge_base: RAGKnowledgeBase):
        """获取Embedding服务"""
        # 获取知识库关联的模型
        if not knowledge_base.embedding_model:
            raise ValueError("请先为知识库配置Embedding模型")
        
        model = await knowledge_base.embedding_model
        
        # 获取该模型的API密钥
        from base.plugins.llm.models.api_key import LLMApiKey
        api_key = await LLMApiKey.filter(model_id=model.id, status="active").first()
        
        if not api_key:
            raise ValueError("未找到该模型的可用API密钥")
        
        # 获取厂商
        provider = await model.provider
        
        # 初始化OpenAI服务
        endpoint = api_key.endpoint_url or model.endpoint_url or "https://api.openai.com/v1"
        from base.plugins.llm.services.localai_service import LocalAIService
        return LocalAIService(api_key=api_key.api_key, endpoint_url=endpoint), model.model_id

    @staticmethod
    async def process_document(
        doc_id: int, 
        chunk_size: int = 500, 
        chunk_overlap: int = 50,
        split_strategy: str = "smart"
    ) -> RAGDocument:
        """处理文档：分块并向量化"""
        doc = await RAGService.get_document(doc_id)
        if not doc:
            raise ValueError("文档不存在")

        if not doc.content:
            raise ValueError("文档内容为空")

        # 获取知识库
        knowledge_base = await doc.knowledge_base
        
        # 获取Embedding服务
        embedding_service, model_id = await RAGService._get_embedding_service(knowledge_base)

        doc.status = "processing"
        await doc.save()

        try:
            content = doc.content
            
            if split_strategy == "smart":
                chunks = RAGService._smart_split_text(content, chunk_size, chunk_overlap)
            elif split_strategy == "paragraph":
                chunks = RAGService._split_by_paragraph(content, chunk_size, chunk_overlap)
            else:
                chunks = RAGService._simple_split_text(content, chunk_size, chunk_overlap)

            await RAGDocumentChunk.filter(document_id=doc_id).delete()

            # 创建片段并向量化
            for idx, chunk_content in enumerate(chunks):
                try:
                    # 生成向量
                    vector = await embedding_service.create_embedding(model_id, chunk_content)
                    
                    await RAGService.create_chunk(
                        RAGDocumentChunkCreate(
                            document_id=doc_id,
                            chunk_index=idx,
                            content=chunk_content
                        ),
                        vector=vector
                    )
                    logger.info(f"片段 {idx} 向量化完成")
                except Exception as e:
                    logger.error(f"片段 {idx} 向量化失败: {str(e)}")
                    # 即使向量化失败，也保存片段（不带向量）
                    await RAGService.create_chunk(
                        RAGDocumentChunkCreate(
                            document_id=doc_id,
                            chunk_index=idx,
                            content=chunk_content
                        )
                    )

            doc.chunk_count = len(chunks)
            doc.status = "completed"
            await doc.save()
            logger.info(f"文档处理完成: {doc.title} (ID: {doc.id}), 分块数: {len(chunks)}")
            return doc
        except Exception as e:
            doc.status = "failed"
            await doc.save()
            logger.error(f"文档处理失败: {doc.title} (ID: {doc.id}), 错误: {str(e)}")
            raise

    @staticmethod
    def _simple_split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """简单的文本分块方法"""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)

            if end < text_length:
                last_space = text.rfind(' ', start, end)
                last_newline = text.rfind('\n', start, end)
                if last_space > start:
                    end = last_space
                elif last_newline > start:
                    end = last_newline

            chunks.append(text[start:end])
            start = end - chunk_overlap

            if start < 0:
                start = 0

        return chunks

    @staticmethod
    def _smart_split_text(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """智能文本分块：优先按段落，然后句子，最后字符"""
        chunks = []
        
        paragraphs = TextSplitter.split_by_paragraph(text)
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                
                if len(paragraph) > chunk_size:
                    sentences = TextSplitter.split_by_sentence(paragraph)
                    current_chunk = ""
                    
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) <= chunk_size:
                            if current_chunk:
                                current_chunk += " "
                            current_chunk += sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            
                            if len(sentence) > chunk_size:
                                sub_chunks = RAGService._simple_split_text(sentence, chunk_size, chunk_overlap)
                                chunks.extend(sub_chunks)
                                current_chunk = ""
                            else:
                                current_chunk = sentence
                    if current_chunk:
                        chunks.append(current_chunk)
                        current_chunk = ""
                else:
                    current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    @staticmethod
    def _split_by_paragraph(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """按段落分块"""
        paragraphs = TextSplitter.split_by_paragraph(text)
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            if len(current_chunk) + len(paragraph) <= chunk_size:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = paragraph
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks

    @staticmethod
    async def search(
        knowledge_base_id: int,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: Optional[float] = None
    ) -> List[dict]:
        """向量搜索"""
        kb = await RAGService.get_knowledge_base(knowledge_base_id)
        if not kb:
            raise ValueError("知识库不存在")

        # 获取Embedding服务并生成查询向量
        embedding_service, model_id = await RAGService._get_embedding_service(kb)
        query_vector = await embedding_service.create_embedding(model_id, query_text)

        chunks = await RAGDocumentChunk.filter(
            document__knowledge_base_id=knowledge_base_id,
            vector__not_isnull=True
        ).prefetch_related('document')

        results = []
        for chunk in chunks:
            try:
                chunk_vector = VectorService.bytes_to_vector(chunk.vector)
                similarity = VectorService.cosine_similarity(query_vector, chunk_vector)

                if similarity_threshold and similarity < similarity_threshold:
                    continue

                results.append({
                    'chunk': chunk,
                    'similarity': similarity
                })
            except Exception as e:
                logger.warning(f"处理片段 {chunk.id} 时出错: {str(e)}")

        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]

    @staticmethod
    async def update_chunk_vector(chunk_id: int, vector: List[float]) -> Optional[RAGDocumentChunk]:
        """更新片段向量"""
        chunk = await RAGService.get_chunk(chunk_id)
        if not chunk:
            return None

        chunk.vector = VectorService.vector_to_bytes(vector)
        await chunk.save()
        return chunk

    @staticmethod
    async def upload_document(
        knowledge_base_id: int,
        file: UploadFile
    ) -> RAGDocument:
        """上传文档"""
        return await DocumentProcessor.upload_document(knowledge_base_id, file)


class DocumentProcessor:
    """文档内容提取器"""
    
    @staticmethod
    async def extract_text(file: UploadFile) -> tuple[str, str, int]:
        """从上传的文件中提取文本内容"""
        filename = file.filename or "unknown"
        content = ""
        file_ext = Path(filename).suffix.lower()
        
        # 读取文件内容
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        if file_ext in ['.txt', '.md', '.markdown', '.py', '.js', '.html', '.css', '.json', '.yaml', '.yml']:
            # 文本文件直接读取
            try:
                content = file_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = file_bytes.decode('gbk')
                except:
                    raise ValueError(f"无法解码文件 {filename}，请使用 UTF-8 或 GBK 编码")
        elif file_ext in ['.pdf']:
            raise ValueError("PDF 文件处理需要安装额外的依赖包，暂时只支持文本文件")
        elif file_ext in ['.docx', '.doc']:
            raise ValueError("Word 文档处理需要安装额外的依赖包，暂时只支持文本文件")
        elif file_ext in ['.xlsx', '.xls', '.csv']:
            raise ValueError("表格文件处理需要安装额外的依赖包，暂时只支持文本文件")
        else:
            raise ValueError(f"不支持的文件类型 {file_ext}，请上传文本文件")
        
        file_type = file_ext[1:] if file_ext else "txt"
        return content, file_type, file_size
    
    @staticmethod
    async def upload_document(
        knowledge_base_id: int,
        file: UploadFile
    ) -> RAGDocument:
        """上传文档并创建记录"""
        filename = file.filename or "unknown"
        title = Path(filename).stem
        
        try:
            content, file_type, file_size = await DocumentProcessor.extract_text(file)
            
            doc = await RAGDocument.create(
                knowledge_base_id=knowledge_base_id,
                title=title,
                file_name=filename,
                file_type=file_type,
                file_size=file_size,
                content=content,
                status="pending",
                metadata={
                    "uploaded": True,
                    "file_type": file_type
                }
            )
            
            logger.info(f"文档上传成功: {filename} (ID: {doc.id})")
            return doc
            
        except Exception as e:
            logger.error(f"文档上传失败: {filename} - {str(e)}")
            raise
