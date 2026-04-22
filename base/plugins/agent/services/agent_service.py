"""
Agent service
"""
from typing import List, Optional
from tortoise.exceptions import DoesNotExist
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate


class AgentService:
    """Agent service class"""

    @staticmethod
    async def create_agent(agent_data: AgentCreate) -> Agent:
        """Create agent"""
        # Create agent
        agent = await Agent.create(
            name=agent_data.name,
            description=agent_data.description,
            status=agent_data.status,
            config=agent_data.config,
            memory_capacity=agent_data.memory_capacity,
            system_prompt=agent_data.system_prompt
        )
        
        return agent

    @staticmethod
    async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = "") -> List[Agent]:
        """Get agent list"""
        query = Agent.all()
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
        agents = await query.offset(skip).limit(limit)
        return agents

    @staticmethod
    async def get_agent_by_id(agent_id: int) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            agent = await Agent.get(id=agent_id)
            return agent
        except DoesNotExist:
            return None

    @staticmethod
    async def update_agent(agent_id: int, agent_data: AgentUpdate) -> Optional[Agent]:
        """Update agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return None

        update_data = agent_data.model_dump(exclude_unset=True)
        
        await agent.update_from_dict(update_data)
        await agent.save()
        
        return agent

    @staticmethod
    async def delete_agent(agent_id: int) -> bool:
        """Delete agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False

        await agent.delete()
        return True



    @staticmethod
    async def execute_agent(agent_id: int, input_data: dict) -> dict:
        """
        执行智能体
        使用结构图（LangGraph的具现化）来实现智能体内部的逻辑控制
        结构图存储在 graph_definition 字段中
        """
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent or agent.status != "active":
            return {"success": False, "message": "Agent not found or inactive"}
        
        try:
            # 使用新的 LangGraph 执行器
            from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
            result = await LangGraphExecutor.execute_agent(agent, input_data)
            return result
        
        except Exception as e:
            import traceback
            return {"success": False, "message": str(e), "traceback": traceback.format_exc()}