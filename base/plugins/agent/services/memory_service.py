"""
Memory service
"""
from typing import List, Optional, Dict, Any
from tortoise.exceptions import DoesNotExist
from datetime import datetime
from base.plugins.agent.models.memory import Memory
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.schemas.memory import MemoryCreate, MemoryUpdate

# 添加向量检索相关依赖
try:
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.docstore.document import Document
    VECTOR_SUPPORT = True
except ImportError:
    VECTOR_SUPPORT = False

# 向量存储目录
VECTOR_STORE_DIR = "./vector_stores"


class MemoryService:
    """Memory service class"""

    @staticmethod
    async def create_memory(memory_data: MemoryCreate) -> Memory:
        """Create memory"""
        # Check if agent exists
        try:
            agent = await Agent.get(id=memory_data.agent_id)
        except DoesNotExist:
            raise ValueError("Agent not found")
        
        # Check memory capacity
        memory_count = await Memory.filter(agent_id=memory_data.agent_id).count()
        if memory_count >= agent.memory_capacity:
            # Remove oldest memories if capacity exceeded
            oldest_memories = await Memory.filter(agent_id=memory_data.agent_id)\
                .order_by("created_at")\
                .limit(memory_count - agent.memory_capacity + 1)
            for old_memory in oldest_memories:
                await old_memory.delete()
        
        memory = await Memory.create(
            agent_id=memory_data.agent_id,
            content=memory_data.content,
            type=memory_data.type,
            importance=memory_data.importance
        )
        
        # 将记忆添加到向量存储
        await MemoryService.add_memory_to_vector_store(memory_data.agent_id, memory)
        
        return memory

    @staticmethod
    async def get_memories(skip: int = 0, limit: int = 100) -> List[Memory]:
        """Get memory list"""
        memories = await Memory.all().offset(skip).limit(limit).prefetch_related('agent')
        return memories

    @staticmethod
    async def get_memory_by_id(memory_id: int) -> Optional[Memory]:
        """Get memory by ID"""
        try:
            memory = await Memory.get(id=memory_id).prefetch_related('agent')
            return memory
        except DoesNotExist:
            return None

    @staticmethod
    async def update_memory(memory_id: int, memory_data: MemoryUpdate) -> Optional[Memory]:
        """Update memory"""
        memory = await MemoryService.get_memory_by_id(memory_id)
        if not memory:
            return None

        update_data = memory_data.model_dump(exclude_unset=True)
        await memory.update_from_dict(update_data)
        await memory.save()
        
        # 更新向量存储中的记忆
        await MemoryService.update_memory_in_vector_store(memory.agent_id, memory)
        
        return memory

    @staticmethod
    async def delete_memory(memory_id: int) -> bool:
        """Delete memory"""
        memory = await MemoryService.get_memory_by_id(memory_id)
        if not memory:
            return False

        await memory.delete()
        return True

    @staticmethod
    async def get_memories_by_agent(agent_id: int) -> List[Memory]:
        """Get memories by agent"""
        memories = await Memory.filter(agent_id=agent_id).order_by("-created_at").all()
        return memories

    @staticmethod
    async def get_memories_by_type(agent_id: int, memory_type: str) -> List[Memory]:
        """Get memories by type"""
        memories = await Memory.filter(agent_id=agent_id, type=memory_type).order_by("-created_at").all()
        return memories

    @staticmethod
    async def recall_memory(memory_id: int) -> Optional[Memory]:
        """Recall memory (increment recall count and update last recalled time)"""
        memory = await MemoryService.get_memory_by_id(memory_id)
        if not memory:
            return None
        
        memory.recall_count += 1
        memory.last_recalled_at = datetime.utcnow()
        await memory.save()
        return memory

    @staticmethod
    async def get_recent_memories(agent_id: int, limit: int = 10) -> List[Memory]:
        """Get recent memories"""
        memories = await Memory.filter(agent_id=agent_id)\
            .order_by("-created_at")\
            .limit(limit)\
            .all()
        return memories

    @staticmethod
    async def get_important_memories(agent_id: int, limit: int = 10) -> List[Memory]:
        """Get important memories"""
        memories = await Memory.filter(agent_id=agent_id)\
            .order_by("-importance", "-created_at")\
            .limit(limit)\
            .all()
        return memories

    @staticmethod
    async def search_memories(agent_id: int, query: str) -> List[Memory]:
        """Search memories by content"""
        # This is a simple search implementation
        # In a real system, you might want to use more sophisticated search techniques
        memories = await Memory.filter(agent_id=agent_id).all()
        filtered_memories = [
            memory for memory in memories 
            if query.lower() in memory.content.lower()
        ]
        return filtered_memories

    @staticmethod
    async def get_memory_stats(agent_id: int) -> dict:
        """Get memory statistics"""
        total_memories = await Memory.filter(agent_id=agent_id).count()
        short_term_memories = await Memory.filter(agent_id=agent_id, type="short_term").count()
        long_term_memories = await Memory.filter(agent_id=agent_id, type="long_term").count()
        
        return {
            "total_memories": total_memories,
            "short_term_memories": short_term_memories,
            "long_term_memories": long_term_memories,
            "memory_capacity": (await Agent.get(id=agent_id)).memory_capacity
        }

    @staticmethod
    def get_vector_store(agent_id: int):
        """获取智能体的向量存储"""
        if not VECTOR_SUPPORT:
            return None
        
        try:
            embeddings = OpenAIEmbeddings()
            vector_store = Chroma(
                persist_directory=f"{VECTOR_STORE_DIR}/agent_{agent_id}",
                embedding_function=embeddings
            )
            return vector_store
        except Exception as e:
            print(f"Error getting vector store: {e}")
            return None

    @staticmethod
    async def add_memory_to_vector_store(agent_id: int, memory: Memory):
        """将记忆添加到向量存储"""
        if not VECTOR_SUPPORT:
            return False
        
        try:
            vector_store = MemoryService.get_vector_store(agent_id)
            if not vector_store:
                return False
            
            # 创建文档对象
            document = Document(
                page_content=memory.content,
                metadata={
                    "memory_id": memory.id,
                    "agent_id": agent_id,
                    "type": memory.type,
                    "importance": memory.importance,
                    "created_at": memory.created_at.isoformat()
                }
            )
            
            # 添加到向量存储
            vector_store.add_documents([document])
            vector_store.persist()
            return True
        except Exception as e:
            print(f"Error adding memory to vector store: {e}")
            return False

    @staticmethod
    async def retrieve_relevant_memories(agent_id: int, query: str, k: int = 5) -> List[Memory]:
        """根据查询检索相关记忆"""
        if not VECTOR_SUPPORT:
            # 如果不支持向量检索，使用传统搜索
            return await MemoryService.search_memories(agent_id, query)
        
        try:
            vector_store = MemoryService.get_vector_store(agent_id)
            if not vector_store:
                return await MemoryService.search_memories(agent_id, query)
            
            # 向量检索
            results = vector_store.similarity_search(query, k=k)
            
            # 获取记忆对象
            memory_ids = [int(doc.metadata.get("memory_id")) for doc in results if doc.metadata.get("memory_id")]
            if not memory_ids:
                return []
            
            memories = await Memory.filter(id__in=memory_ids).all()
            return memories
        except Exception as e:
            print(f"Error retrieving relevant memories: {e}")
            return await MemoryService.search_memories(agent_id, query)

    @staticmethod
    async def update_memory_in_vector_store(agent_id: int, memory: Memory):
        """更新向量存储中的记忆"""
        if not VECTOR_SUPPORT:
            return False
        
        try:
            # 先删除旧记忆
            vector_store = MemoryService.get_vector_store(agent_id)
            if not vector_store:
                return False
            
            # 删除旧记忆
            vector_store.delete([str(memory.id)])
            
            # 添加更新后的记忆
            return await MemoryService.add_memory_to_vector_store(agent_id, memory)
        except Exception as e:
            print(f"Error updating memory in vector store: {e}")
            return False

    @staticmethod
    async def clear_vector_store(agent_id: int):
        """清空智能体的向量存储"""
        if not VECTOR_SUPPORT:
            return False
        
        try:
            vector_store = MemoryService.get_vector_store(agent_id)
            if not vector_store:
                return False
            
            vector_store.delete([])  # 清空所有向量
            vector_store.persist()
            return True
        except Exception as e:
            print(f"Error clearing vector store: {e}")
            return False