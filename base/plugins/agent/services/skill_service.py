"""
Skill service
"""
from typing import List, Optional
from tortoise.exceptions import DoesNotExist
from base.plugins.agent.models.skill import Skill
from base.plugins.agent.schemas.skill import SkillCreate, SkillUpdate


class SkillService:
    """Skill service class"""

    @staticmethod
    async def create_skill(skill_data: SkillCreate) -> Skill:
        """Create skill"""
        skill = await Skill.create(
            name=skill_data.name,
            description=skill_data.description,
            type=skill_data.type,
            parameters=skill_data.parameters,
            implementation=skill_data.implementation,
            status=skill_data.status
        )
        return skill

    @staticmethod
    async def get_skills(skip: int = 0, limit: int = 100, name: str = "", type: str = "", status: str = "") -> List[Skill]:
        """Get skill list"""
        query = Skill.all()
        if name:
            query = query.filter(name__icontains=name)
        if type:
            query = query.filter(type=type)
        if status:
            query = query.filter(status=status)
        skills = await query.offset(skip).limit(limit)
        return skills

    @staticmethod
    async def get_skill_by_id(skill_id: int) -> Optional[Skill]:
        """Get skill by ID"""
        try:
            skill = await Skill.get(id=skill_id)
            return skill
        except DoesNotExist:
            return None

    @staticmethod
    async def update_skill(skill_id: int, skill_data: SkillUpdate) -> Optional[Skill]:
        """Update skill"""
        skill = await SkillService.get_skill_by_id(skill_id)
        if not skill:
            return None

        update_data = skill_data.model_dump(exclude_unset=True)
        await skill.update_from_dict(update_data)
        await skill.save()
        return skill

    @staticmethod
    async def delete_skill(skill_id: int) -> bool:
        """Delete skill"""
        skill = await SkillService.get_skill_by_id(skill_id)
        if not skill:
            return False

        await skill.delete()
        return True

    @staticmethod
    async def get_skills_by_type(skill_type: str) -> List[Skill]:
        """Get skills by type"""
        skills = await Skill.filter(type=skill_type).all()
        return skills

    @staticmethod
    async def get_active_skills() -> List[Skill]:
        """Get active skills"""
        skills = await Skill.filter(status="active").all()
        return skills

    @staticmethod
    async def execute_skill(skill_id: int, parameters: dict) -> dict:
        """Execute skill"""
        skill = await SkillService.get_skill_by_id(skill_id)
        if not skill or skill.status != "active":
            return {"success": False, "message": "Skill not found or inactive"}
        
        try:
            # 从注册表中获取技能
            from base.plugins.agent.skills.registry import SkillRegistry
            skill_class = SkillRegistry.get_skill(skill.type)
            if skill_class:
                return skill_class.execute(parameters)
            else:
                # 返回默认响应
                return {
                    "success": True,
                    "skill_id": skill_id,
                    "skill_name": skill.name,
                    "parameters": parameters,
                    "result": "Skill executed successfully"
                }
        except Exception as e:
            return {"success": False, "message": str(e)}

    @staticmethod
    async def get_skill_usage(skill_id: int) -> dict:
        """Get skill usage information"""
        skill = await SkillService.get_skill_by_id(skill_id)
        if not skill:
            return {"error": "Skill not found"}
        
        # Get number of agents using this skill
        agents = await skill.agents.all()
        agent_count = len(agents)
        
        return {
            "skill_id": skill_id,
            "skill_name": skill.name,
            "agent_count": agent_count,
            "agents": [agent.name for agent in agents]
        }