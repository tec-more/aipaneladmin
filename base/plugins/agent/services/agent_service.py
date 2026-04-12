"""
Agent service
"""
from typing import List, Optional
from tortoise.exceptions import DoesNotExist
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.models.skill import Skill
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate


class AgentService:
    """Agent service class"""

    @staticmethod
    async def create_agent(agent_data: AgentCreate) -> Agent:
        """Create agent"""
        agent = await Agent.create(
            name=agent_data.name,
            description=agent_data.description,
            status=agent_data.status,
            config=agent_data.config,
            memory_capacity=agent_data.memory_capacity
        )
        
        # Associate skills
        if agent_data.skill_ids:
            skills = await Skill.filter(id__in=agent_data.skill_ids).all()
            await agent.skills.add(*skills)
        
        return agent

    @staticmethod
    async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = "") -> List[Agent]:
        """Get agent list"""
        query = Agent.all()
        if name:
            query = query.filter(name__icontains=name)
        if status:
            query = query.filter(status=status)
        agents = await query.offset(skip).limit(limit).prefetch_related('skills')
        return agents

    @staticmethod
    async def get_agent_by_id(agent_id: int) -> Optional[Agent]:
        """Get agent by ID"""
        try:
            agent = await Agent.get(id=agent_id).prefetch_related('skills', 'memories')
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
        skill_ids = update_data.pop('skill_ids', None)
        
        await agent.update_from_dict(update_data)
        await agent.save()
        
        # Update skills
        if skill_ids is not None:
            await agent.skills.clear()
            if skill_ids:
                skills = await Skill.filter(id__in=skill_ids).all()
                await agent.skills.add(*skills)
        
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
    async def get_agent_with_skills(agent_id: int) -> Optional[dict]:
        """Get agent with skills"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return None
        
        skills = await agent.skills.all()
        return {
            "agent": agent,
            "skills": skills
        }

    @staticmethod
    async def add_skill_to_agent(agent_id: int, skill_id: int) -> bool:
        """Add skill to agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False
        
        try:
            skill = await Skill.get(id=skill_id)
            await agent.skills.add(skill)
            return True
        except DoesNotExist:
            return False

    @staticmethod
    async def remove_skill_from_agent(agent_id: int, skill_id: int) -> bool:
        """Remove skill from agent"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False
        
        try:
            skill = await Skill.get(id=skill_id)
            await agent.skills.remove(skill)
            return True
        except DoesNotExist:
            return False

    @staticmethod
    async def set_agent_skills(agent_id: int, skill_ids: List[int]) -> bool:
        """Set agent skills (replace all)"""
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return False
        
        await agent.skills.clear()
        if skill_ids:
            skills = await Skill.filter(id__in=skill_ids).all()
            await agent.skills.add(*skills)
        return True