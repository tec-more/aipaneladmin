"""
Skill API routes
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from base.plugins.agent.schemas.skill import SkillCreate, SkillUpdate, SkillResponse
from base.plugins.agent.services.skill_service import SkillService
from base.common.response import success_response, fail_response

skill_router = APIRouter(prefix="/skills", tags=["skills"])


@skill_router.post("/")
async def create_skill(skill: SkillCreate):
    """Create a new skill"""
    try:
        created_skill = await SkillService.create_skill(skill)
        agent_count = await created_skill.agents.count()
        
        data = SkillResponse(
            id=created_skill.id,
            name=created_skill.name,
            description=created_skill.description,
            type=created_skill.type,
            parameters=created_skill.parameters,
            implementation=created_skill.implementation,
            status=created_skill.status,
            created_at=created_skill.created_at,
            updated_at=created_skill.updated_at,
            agent_count=agent_count
        )
        return success_response(data=data.model_dump(), msg="技能创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@skill_router.get("/")
async def get_skills(skip: int = 0, limit: int = 100, name: str = "", type: str = "", status: str = ""):
    """Get all skills"""
    skills = await SkillService.get_skills(skip=skip, limit=limit, name=name, type=type, status=status)
    response = []
    for skill in skills:
        agent_count = await skill.agents.count()
        response.append(SkillResponse(
            id=skill.id,
            name=skill.name,
            description=skill.description,
            type=skill.type,
            parameters=skill.parameters,
            implementation=skill.implementation,
            status=skill.status,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
            agent_count=agent_count
        ).model_dump())
    return success_response(data={"items": response, "total": len(response)})


@skill_router.get("/{skill_id}")
async def get_skill(skill_id: int):
    """Get skill by ID"""
    skill = await SkillService.get_skill_by_id(skill_id)
    if not skill:
        return fail_response(msg="技能不存在", code=404)
    
    agent_count = await skill.agents.count()
    
    data = SkillResponse(
        id=skill.id,
        name=skill.name,
        description=skill.description,
        type=skill.type,
        parameters=skill.parameters,
        implementation=skill.implementation,
        status=skill.status,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
        agent_count=agent_count
    )
    return success_response(data=data.model_dump())


@skill_router.put("/{skill_id}")
async def update_skill(skill_id: int, skill: SkillUpdate):
    """Update skill"""
    updated_skill = await SkillService.update_skill(skill_id, skill)
    if not updated_skill:
        return fail_response(msg="技能不存在", code=404)
    
    agent_count = await updated_skill.agents.count()
    
    data = SkillResponse(
        id=updated_skill.id,
        name=updated_skill.name,
        description=updated_skill.description,
        type=updated_skill.type,
        parameters=updated_skill.parameters,
        implementation=updated_skill.implementation,
        status=updated_skill.status,
        created_at=updated_skill.created_at,
        updated_at=updated_skill.updated_at,
        agent_count=agent_count
    )
    return success_response(data=data.model_dump(), msg="技能更新成功")


@skill_router.delete("/{skill_id}")
async def delete_skill(skill_id: int):
    """Delete skill"""
    success = await SkillService.delete_skill(skill_id)
    if not success:
        return fail_response(msg="技能不存在", code=404)
    return success_response(msg="技能删除成功")


@skill_router.get("/type/{skill_type}")
async def get_skills_by_type(skill_type: str):
    """Get skills by type"""
    skills = await SkillService.get_skills_by_type(skill_type)
    return success_response(data=skills)


@skill_router.get("/active/list")
async def get_active_skills():
    """Get active skills"""
    skills = await SkillService.get_active_skills()
    return success_response(data=skills)


@skill_router.post("/{skill_id}/execute")
async def execute_skill(skill_id: int, parameters: dict):
    """Execute skill"""
    result = await SkillService.execute_skill(skill_id, parameters)
    return success_response(data=result, msg="技能执行成功")


@skill_router.get("/{skill_id}/usage")
async def get_skill_usage(skill_id: int):
    """Get skill usage information"""
    usage = await SkillService.get_skill_usage(skill_id)
    if "error" in usage:
        return fail_response(msg=usage["error"], code=404)
    return success_response(data=usage)
