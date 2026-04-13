"""
技能注册表
"""
from typing import Dict, Type

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
    def get_skill(cls, skill_type: str) -> Type:
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
