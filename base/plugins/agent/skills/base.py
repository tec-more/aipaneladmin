"""
技能基类
"""
from typing import Dict, Any

class BaseSkill:
    """
    技能基类
    所有技能都应该继承自这个类
    """
    
    @staticmethod
    def execute(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            params: 输入参数
            
        Returns:
            执行结果
        """
        raise NotImplementedError("子类必须实现execute方法")
    
    @classmethod
    def get_name(cls) -> str:
        """
        获取技能名称
        
        Returns:
            技能名称
        """
        return cls.__name__
