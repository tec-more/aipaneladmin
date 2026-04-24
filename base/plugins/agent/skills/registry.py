"""
技能注册表
"""
from typing import Dict, Type, Optional
import importlib
import os
import pkgutil

class SkillRegistry:
    """技能注册表"""
    _skills: Dict[str, Type] = {}
    
    @classmethod
    def register(cls, skill_type: str, skill_class: Type) -> None:
        """
        注册技能
        
        Args:
            skill_type: 技能类型
            skill_class: 技能类
        """
        cls._skills[skill_type] = skill_class
    
    @classmethod
    def get_skill(cls, skill_type: str) -> Optional[Type]:
        """
        获取技能类
        
        Args:
            skill_type: 技能类型
            
        Returns:
            技能类
        """
        return cls._skills.get(skill_type)
    
    @classmethod
    def get_skill_types(cls) -> list:
        """
        获取所有技能类型
        
        Returns:
            技能类型列表
        """
        return list(cls._skills.keys())
    
    @classmethod
    def is_skill_registered(cls, skill_type: str) -> bool:
        """
        检查技能是否已注册
        
        Args:
            skill_type: 技能类型
            
        Returns:
            是否已注册
        """
        return skill_type in cls._skills
    
    @classmethod
    async def auto_register_from_database(cls) -> None:
        """
        从数据库自动注册技能
        从数据库中读取技能配置，注册到注册表
        """
        try:
            from base.plugins.agent.models.skill import Skill
            from base.plugins.agent.skills.base import BaseSkill
            
            # 获取所有活跃的技能
            skills = await Skill.filter(status="active").all()
            
            # 注册技能
            for skill in skills:
                # 检查技能是否已经注册
                if not cls.is_skill_registered(skill.type):
                    # 创建一个动态技能类
                    class DynamicSkill(BaseSkill):
                        @staticmethod
                        def execute(params: dict):
                            # 这里可以根据skill.implementation执行自定义逻辑
                            # 目前返回默认响应
                            return {
                                "success": True,
                                "skill_id": skill.id,
                                "skill_name": skill.name,
                                "parameters": params,
                                "result": "Skill executed successfully"
                            }
                    
                    # 注册技能
                    cls.register(skill.type, DynamicSkill)
        except Exception as e:
            print(f"Error auto-registering skills from database: {e}")
    
    @classmethod
    async def auto_register_all(cls) -> None:
        """
        自动注册所有技能
        包括从代码和数据库注册
        """
        # 延迟导入避免循环导入
        import importlib
        import os
        import pkgutil
        
        # 从代码自动注册技能
        current_dir = os.path.dirname(__file__)
        for _, module_name, _ in pkgutil.iter_modules([current_dir]):
            if module_name in ['base', 'registry']:
                continue
            try:
                module = importlib.import_module(f'base.plugins.agent.skills.{module_name}')
            except Exception as e:
                print(f"Error importing skill module {module_name}: {e}")
        
        await cls.auto_register_from_database()
