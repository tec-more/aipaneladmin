"""
Agent API routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from base.plugins.agent.services.agent_service import AgentService
from base.common.response import success_response, fail_response

agent_router = APIRouter(prefix="/agents", tags=["agents"])


@agent_router.post("/")
async def create_agent(agent: AgentCreate):
    """Create a new agent"""
    try:
        created_agent = await AgentService.create_agent(agent)
        skill_count = await created_agent.skills.all().count()
        memory_count = await created_agent.memories.all().count()
        
        data = AgentResponse(
            id=created_agent.id,
            name=created_agent.name,
            description=created_agent.description,
            status=created_agent.status,
            config=created_agent.config,
            memory_capacity=created_agent.memory_capacity,
            created_at=created_agent.created_at,
            updated_at=created_agent.updated_at,
            skill_count=skill_count,
            memory_count=memory_count
        )
        return success_response(data=data.model_dump(), msg="智能体创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.get("/")
async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = ""):
    """Get all agents"""
    agents = await AgentService.get_agents(skip=skip, limit=limit, name=name, status=status)
    response = []
    for agent in agents:
        skill_count = await agent.skills.all().count()
        memory_count = await agent.memories.all().count()
        response.append(AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            status=agent.status,
            config=agent.config,
            memory_capacity=agent.memory_capacity,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            skill_count=skill_count,
            memory_count=memory_count
        ).model_dump())
    return success_response(data={"items": response, "total": len(response)})


@agent_router.get("/{agent_id}")
async def get_agent(agent_id: int):
    """Get agent by ID"""
    agent = await AgentService.get_agent_by_id(agent_id)
    if not agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = await agent.skills.all().count()
    memory_count = await agent.memories.all().count()
    
    data = AgentResponse(
        id=agent.id,
        name=agent.name,
        description=agent.description,
        status=agent.status,
        config=agent.config,
        memory_capacity=agent.memory_capacity,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        skill_count=skill_count,
        memory_count=memory_count
    )
    return success_response(data=data.model_dump())


@agent_router.put("/{agent_id}")
async def update_agent(agent_id: int, agent: AgentUpdate):
    """Update agent"""
    updated_agent = await AgentService.update_agent(agent_id, agent)
    if not updated_agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = await updated_agent.skills.all().count()
    memory_count = await updated_agent.memories.all().count()
    
    data = AgentResponse(
        id=updated_agent.id,
        name=updated_agent.name,
        description=updated_agent.description,
        status=updated_agent.status,
        config=updated_agent.config,
        memory_capacity=updated_agent.memory_capacity,
        created_at=updated_agent.created_at,
        updated_at=updated_agent.updated_at,
        skill_count=skill_count,
        memory_count=memory_count
    )
    return success_response(data=data.model_dump(), msg="智能体更新成功")


@agent_router.delete("/{agent_id}")
async def delete_agent(agent_id: int):
    """Delete agent"""
    success = await AgentService.delete_agent(agent_id)
    if not success:
        return fail_response(msg="智能体不存在", code=404)
    return success_response(msg="智能体删除成功")


@agent_router.get("/{agent_id}/skills")
async def get_agent_skills(agent_id: int):
    """Get agent skills"""
    agent_data = await AgentService.get_agent_with_skills(agent_id)
    if not agent_data:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_ids = [skill.id for skill in agent_data["skills"]]
    return success_response(data=skill_ids)


@agent_router.put("/{agent_id}/skills")
async def set_agent_skills(agent_id: int, data: dict):
    """Set agent skills"""
    skill_ids = data.get("skill_ids", [])
    success = await AgentService.set_agent_skills(agent_id, skill_ids)
    if not success:
        return fail_response(msg="设置技能失败", code=400)
    return success_response(msg="技能设置成功")


@agent_router.post("/{agent_id}/skills/{skill_id}")
async def add_skill_to_agent(agent_id: int, skill_id: int):
    """Add skill to agent"""
    success = await AgentService.add_skill_to_agent(agent_id, skill_id)
    if not success:
        return fail_response(msg="智能体或技能不存在", code=404)
    return success_response(msg="技能添加成功")


@agent_router.delete("/{agent_id}/skills/{skill_id}")
async def remove_skill_from_agent(agent_id: int, skill_id: int):
    """Remove skill from agent"""
    success = await AgentService.remove_skill_from_agent(agent_id, skill_id)
    if not success:
        return fail_response(msg="智能体或技能不存在", code=404)
    return success_response(msg="技能移除成功")
