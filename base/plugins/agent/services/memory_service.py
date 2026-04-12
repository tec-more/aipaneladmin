"""
Memory service
"""
from typing import List, Optional
from tortoise.exceptions import DoesNotExist
from datetime import datetime
from base.plugins.agent.models.memory import Memory
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.schemas.memory import MemoryCreate, MemoryUpdate


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