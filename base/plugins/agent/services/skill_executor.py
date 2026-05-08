
"""
Skill Executor - 技能执行器
提供标准化的技能处理和工具调用
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from base.plugins.agent.models.skill import Skill
from base.plugins.agent.services.skill_service import SkillService
from base.plugins.agent.tools.registry import ToolRegistry


logger = logging.getLogger(__name__)


class SkillConfig:
    """技能配置类"""
    
    def __init__(self, skill_id: int):
        self.skill_id = skill_id
        self.skill = None
        self.bound_tools = []
        self.prompt = ""
        self.skill_description = ""
        
    async def load(self):
        """加载技能配置"""
        skill = await Skill.get_or_none(id=self.skill_id, status="active")
        if not skill:
            raise ValueError(f"Skill not found: {self.skill_id}")
            
        self.skill = skill
        self.skill_description = skill.description or ""
        self.implementation = skill.implementation or ""
        
        # 解析工具
        self.bound_tools = SkillService.parse_bound_tools(self.implementation)
        
        # 提取提示词（从 Markdown 中解析）
        self.prompt = self._extract_prompt()
        
    def _extract_prompt(self):
        """从 Markdown 中提取提示词部分"""
        if not self.implementation:
            return ""
            
        lines = self.implementation.split("\n")
        prompt_lines = []
        in_prompt_section = False
        
        for line in lines:
            stripped = line.strip()
            
            # 检测提示词部分开始
            if stripped.startswith("##"):
                if "描述" in stripped or "指令" in stripped or "任务" in stripped or "提示" in stripped:
                    in_prompt_section = True
                    continue
                elif "可用工具" in stripped:
                    in_prompt_section = False
                    continue
                    
            if in_prompt_section and stripped:
                prompt_lines.append(line)
                
        # 如果没有找到专门的提示词部分，就用描述
        if not prompt_lines:
            return self.skill_description
            
        return "\n".join(prompt_lines)
    
    def get_tools_schema(self) -&gt; Dict:
        """获取所有绑定工具的 Schema"""
        all_tools = ToolRegistry.get_all_tools_info()
        selected_tools = {}
        
        for tool_name in self.bound_tools:
            if tool_name in all_tools:
                selected_tools[tool_name] = all_tools[tool_name]
                
        return selected_tools


class SkillExecutor:
    """技能执行器"""
    
    @staticmethod
    async def prepare_llm_context(
        skill_ids: List[int], 
        input_text: str = "",
        extra_context: str = ""
    ) -&gt; Dict[str, Any]:
        """
        为 LLM 准备完整的上下文，包括技能和工具
        
        Args:
            skill_ids: 技能 ID 列表
            input_text: 用户输入
            extra_context: 额外的上下文
            
        Returns:
            包含 prompt、tools_schema、bound_tools 的字典
        """
        all_prompts = []
        all_tools = {}
        bound_tools_set = set()
        
        # 加载每个技能
        for skill_id in skill_ids:
            try:
                config = SkillConfig(skill_id)
                await config.load()
                
                # 合并技能的提示词
                if config.prompt:
                    all_prompts.append(f"【技能：{config.skill.name}】\n{config.prompt}")
                    
                # 合并工具
                tools_schema = config.get_tools_schema()
                all_tools.update(tools_schema)
                bound_tools_set.update(config.bound_tools)
                
            except Exception as e:
                logger.warning(f"Failed to load skill {skill_id}: {e}")
                
        # 构建完整的系统提示词
        system_prompt = SkillExecutor._build_system_prompt(all_prompts, extra_context)
        
        # 格式化工具列表
        tools_list = list(all_tools.values())
        
        return {
            "system_prompt": system_prompt,
            "tools_schema": tools_list,
            "bound_tools": list(bound_tools_set),
            "skill_prompts": all_prompts
        }
    
    @staticmethod
    def _build_system_prompt(skill_prompts: List[str], extra_context: str) -&gt; str:
        """构建系统提示词"""
        if not skill_prompts:
            return extra_context or "You are a helpful assistant."
            
        combined_prompt = "\n\n".join(skill_prompts)
        
        if extra_context:
            combined_prompt = f"{extra_context}\n\n{combined_prompt}"
            
        return combined_prompt
        
    @staticmethod
    async def execute_tool_by_name(tool_name: str, params: Dict) -&gt; Any:
        """根据名称执行工具"""
        try:
            tool_class = ToolRegistry.get_tool(tool_name)
            if not tool_class:
                raise ValueError(f"Tool not registered: {tool_name}")
                
            # 执行工具
            result = await tool_class.execute(**params)
            return result
        except Exception as e:
            logger.exception(f"Failed to execute tool {tool_name}")
            raise e

