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
    from base.plugins.agent.models.skill import Skill
    
    # 先获取数据库中符合条件的总数
    query = Skill.all()
    if name:
        query = query.filter(name__icontains=name)
    if type:
        query = query.filter(type=type)
    if status:
        query = query.filter(status=status)
    db_total = await query.count()
    
    # 获取数据库中的技能
    db_skills = await SkillService.get_skills(skip=skip, limit=limit, name=name, type=type, status=status)
    
    # 获取代码中注册的技能
    from base.plugins.agent.skills.registry import SkillRegistry
    
    code_skill_types = SkillRegistry.get_skill_types()
    
    # 获取所有数据库技能的type，用于检查代码技能是否已存在
    all_db_skill_types = set()
    all_db_skills = await query.all()  # 获取所有符合条件的数据库技能
    for skill in all_db_skills:
        all_db_skill_types.add(skill.type)
    
    code_skills = []
    for skill_type in code_skill_types:
        # 检查该技能是否已在数据库中存在
        if skill_type not in all_db_skill_types:
            # 创建一个代码技能的字典对象
            skill_class = SkillRegistry.get_skill(skill_type)
            if skill_class:
                code_skill = {
                    "id": None,
                    "name": skill_class.get_name() if hasattr(skill_class, 'get_name') else skill_type,
                    "description": f"代码注册技能: {skill_type}",
                    "type": skill_type,
                    "parameters": {},
                    "implementation": None,
                    "status": "active",
                    "created_at": None,
                    "updated_at": None,
                    "agent_count": 0,
                    "source": "code"  # 标识技能来源
                }
                code_skills.append(code_skill)
    
    # 计算代码技能总数
    code_total = len(code_skills)
    
    # 对代码技能进行分页
    paged_code_skills = code_skills[skip:skip+limit]
    
    # 为数据库技能添加来源标识
    for skill in db_skills:
        skill.source = "database"
    
    # 合并数据库技能和代码技能
    all_skills = db_skills + paged_code_skills
    
    # 构建响应
    response = []
    for skill in all_skills:
        if hasattr(skill, 'agents'):
            agent_count = await skill.agents.count()
        else:
            agent_count = skill.get('agent_count', 0)
        
        response.append(SkillResponse(
            id=skill.id if hasattr(skill, 'id') else skill.get('id'),
            name=skill.name if hasattr(skill, 'name') else skill.get('name'),
            description=skill.description if hasattr(skill, 'description') else skill.get('description'),
            type=skill.type if hasattr(skill, 'type') else skill.get('type'),
            parameters=skill.parameters if hasattr(skill, 'parameters') else skill.get('parameters'),
            implementation=skill.implementation if hasattr(skill, 'implementation') else skill.get('implementation'),
            status=skill.status if hasattr(skill, 'status') else skill.get('status'),
            created_at=skill.created_at if hasattr(skill, 'created_at') else skill.get('created_at'),
            updated_at=skill.updated_at if hasattr(skill, 'updated_at') else skill.get('updated_at'),
            agent_count=agent_count,
            source=skill.source if hasattr(skill, 'source') else skill.get('source')
        ).model_dump())
    
    return success_response(data={"items": response, "total": db_total + code_total})


@skill_router.get("/{skill_id}")
async def get_skill(skill_id: int):
    """Get skill by ID"""
    # Validate skill_id is a positive integer
    if skill_id is None or skill_id <= 0:
        return fail_response(msg="无效的技能ID", code=422)
    
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
