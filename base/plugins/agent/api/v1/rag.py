"""
RAG (Retrieval-Augmented Generation) API Routes
"""
from typing import List
from fastapi import APIRouter, Query, UploadFile, File
from base.common.response import success_response, fail_response
from base.plugins.agent.schemas.rag import (
    RAGKnowledgeBaseCreate,
    RAGKnowledgeBaseUpdate,
    RAGKnowledgeBaseResponse,
    RAGDocumentCreate,
    RAGDocumentUpdate,
    RAGDocumentResponse,
    RAGDocumentChunkResponse,
    RAGSearchRequest,
    RAGSearchResponse
)
from base.plugins.agent.services.rag_service import RAGService

rag_router = APIRouter(prefix="/rag", tags=["rag"])


@rag_router.post("/knowledge-bases", response_model=RAGKnowledgeBaseResponse)
async def create_knowledge_base(data: RAGKnowledgeBaseCreate):
    """创建知识库"""
    try:
        kb = await RAGService.create_knowledge_base(data)
        return success_response(data=RAGKnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            status=kb.status,
            vector_dimension=kb.vector_dimension,
            config=kb.config,
            embedding_model_id=kb.embedding_model_id,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            document_count=0
        ), msg="知识库创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.get("/knowledge-bases")
async def list_knowledge_bases(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    name: str = "",
    status: str = ""
):
    """列出知识库"""
    try:
        kbs = await RAGService.list_knowledge_bases(skip, limit, name, status)
        total = await RAGService.count_knowledge_bases(name, status)
        
        results = []
        for kb in kbs:
            doc_count = await RAGService.count_documents(kb.id)
            results.append(RAGKnowledgeBaseResponse(
                id=kb.id,
                name=kb.name,
                description=kb.description,
                status=kb.status,
                vector_dimension=kb.vector_dimension,
                config=kb.config,
                created_at=kb.created_at,
                updated_at=kb.updated_at,
                document_count=doc_count
            ))
        
        return success_response(data={"items": results, "total": total})
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.get("/knowledge-bases/{kb_id}", response_model=RAGKnowledgeBaseResponse)
async def get_knowledge_base(kb_id: int):
    """获取知识库详情"""
    try:
        kb = await RAGService.get_knowledge_base(kb_id)
        if not kb:
            return fail_response(msg="知识库不存在", code=404)
        
        doc_count = await RAGService.count_documents(kb.id)
        return success_response(data=RAGKnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            status=kb.status,
            vector_dimension=kb.vector_dimension,
            config=kb.config,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            document_count=doc_count
        ))
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.put("/knowledge-bases/{kb_id}", response_model=RAGKnowledgeBaseResponse)
async def update_knowledge_base(kb_id: int, data: RAGKnowledgeBaseUpdate):
    """更新知识库"""
    try:
        kb = await RAGService.update_knowledge_base(kb_id, data)
        if not kb:
            return fail_response(msg="知识库不存在", code=404)
        
        doc_count = await RAGService.count_documents(kb.id)
        return success_response(data=RAGKnowledgeBaseResponse(
            id=kb.id,
            name=kb.name,
            description=kb.description,
            status=kb.status,
            vector_dimension=kb.vector_dimension,
            config=kb.config,
            created_at=kb.created_at,
            updated_at=kb.updated_at,
            document_count=doc_count
        ), msg="知识库更新成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.delete("/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: int):
    """删除知识库"""
    try:
        success = await RAGService.delete_knowledge_base(kb_id)
        if not success:
            return fail_response(msg="知识库不存在", code=404)
        return success_response(msg="知识库删除成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.post("/documents", response_model=RAGDocumentResponse)
async def create_document(data: RAGDocumentCreate):
    """创建文档"""
    try:
        doc = await RAGService.create_document(data)
        return success_response(data=RAGDocumentResponse(
            id=doc.id,
            knowledge_base_id=doc.knowledge_base_id,
            title=doc.title,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            file_path=doc.file_path,
            content=doc.content,
            metadata=doc.metadata,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        ), msg="文档创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.get("/documents")
async def list_documents(
    knowledge_base_id: int = Query(..., gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    title: str = "",
    status: str = ""
):
    """列出文档"""
    try:
        docs = await RAGService.list_documents(knowledge_base_id, skip, limit, title, status)
        total = await RAGService.count_documents(knowledge_base_id, title, status)
        
        results = []
        for doc in docs:
            results.append(RAGDocumentResponse(
                id=doc.id,
                knowledge_base_id=doc.knowledge_base_id,
                title=doc.title,
                file_name=doc.file_name,
                file_type=doc.file_type,
                file_size=doc.file_size,
                file_path=doc.file_path,
                content=doc.content,
                metadata=doc.metadata,
                status=doc.status,
                chunk_count=doc.chunk_count,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            ))
        
        return success_response(data={"items": results, "total": total})
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.get("/documents/{doc_id}", response_model=RAGDocumentResponse)
async def get_document(doc_id: int):
    """获取文档详情"""
    try:
        doc = await RAGService.get_document(doc_id)
        if not doc:
            return fail_response(msg="文档不存在", code=404)
        
        return success_response(data=RAGDocumentResponse(
            id=doc.id,
            knowledge_base_id=doc.knowledge_base_id,
            title=doc.title,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            file_path=doc.file_path,
            content=doc.content,
            metadata=doc.metadata,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        ))
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.put("/documents/{doc_id}", response_model=RAGDocumentResponse)
async def update_document(doc_id: int, data: RAGDocumentUpdate):
    """更新文档"""
    try:
        doc = await RAGService.update_document(doc_id, data)
        if not doc:
            return fail_response(msg="文档不存在", code=404)
        
        return success_response(data=RAGDocumentResponse(
            id=doc.id,
            knowledge_base_id=doc.knowledge_base_id,
            title=doc.title,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            file_path=doc.file_path,
            content=doc.content,
            metadata=doc.metadata,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        ), msg="文档更新成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int):
    """删除文档"""
    try:
        success = await RAGService.delete_document(doc_id)
        if not success:
            return fail_response(msg="文档不存在", code=404)
        return success_response(msg="文档删除成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.post("/documents/{doc_id}/process", response_model=RAGDocumentResponse)
async def process_document(
    doc_id: int, 
    chunk_size: int = 500, 
    chunk_overlap: int = 50,
    split_strategy: str = "smart"
):
    """处理文档：分块并向量化"""
    try:
        doc = await RAGService.process_document(doc_id, chunk_size, chunk_overlap, split_strategy)
        return success_response(data=RAGDocumentResponse(
            id=doc.id,
            knowledge_base_id=doc.knowledge_base_id,
            title=doc.title,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            file_path=doc.file_path,
            content=doc.content,
            metadata=doc.metadata,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        ), msg="文档处理成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.get("/documents/{doc_id}/chunks")
async def list_chunks(
    doc_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """列出文档片段"""
    try:
        chunks = await RAGService.list_chunks(doc_id, skip, limit)
        results = []
        for chunk in chunks:
            results.append(RAGDocumentChunkResponse(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                metadata=chunk.metadata,
                created_at=chunk.created_at,
                updated_at=chunk.updated_at
            ))
        return success_response(data={"items": results, "total": len(results)})
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.delete("/chunks/{chunk_id}")
async def delete_chunk(chunk_id: int):
    """删除文档片段"""
    try:
        success = await RAGService.delete_chunk(chunk_id)
        if not success:
            return fail_response(msg="片段不存在", code=404)
        return success_response(msg="片段删除成功")
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.post("/search")
async def search(request: RAGSearchRequest):
    """向量搜索"""
    try:
        results = await RAGService.search(
            request.knowledge_base_id,
            request.query,
            request.top_k,
            request.similarity_threshold
        )
        
        chunk_responses = []
        for result in results:
            chunk = result['chunk']
            chunk_responses.append(RAGDocumentChunkResponse(
                id=chunk.id,
                document_id=chunk.document_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                metadata=chunk.metadata,
                created_at=chunk.created_at,
                updated_at=chunk.updated_at,
                similarity=result['similarity']
            ))
        
        return success_response(data=RAGSearchResponse(
            query=request.query,
            results=chunk_responses,
            total=len(chunk_responses)
        ))
    except Exception as e:
        return fail_response(msg=str(e))


@rag_router.post("/documents/upload")
async def upload_document(
    knowledge_base_id: int = Query(...),
    file: UploadFile = File(...)
):
    """上传文档并提取内容"""
    try:
        doc = await RAGService.upload_document(knowledge_base_id, file)
        return success_response(data=RAGDocumentResponse(
            id=doc.id,
            knowledge_base_id=doc.knowledge_base_id,
            title=doc.title,
            file_name=doc.file_name,
            file_type=doc.file_type,
            file_size=doc.file_size,
            file_path=doc.file_path,
            content=doc.content,
            metadata=doc.metadata,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        ), msg="文档上传成功")
    except Exception as e:
        return fail_response(msg=str(e))
