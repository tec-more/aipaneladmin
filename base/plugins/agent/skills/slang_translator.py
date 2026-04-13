"""
黑话翻译技能
"""
from typing import Dict, Any

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from base.plugins.agent.skills.base import BaseSkill
from base.plugins.agent.skills.registry import SkillRegistry

class SlangTranslatorSkill(BaseSkill):
    """黑话翻译技能"""
    
    @staticmethod
    def create_prompt():
        """创建提示词模板"""
        if not LANGCHAIN_AVAILABLE:
            return None
        template = """
        你是一个专业的黑话翻译专家，能够将各种网络黑话、行业术语、流行语等翻译成通俗易懂的中文。
        
        请将以下黑话翻译成标准中文，并解释其含义和使用场景：
        
        {input_text}
        
        翻译要求：
        1. 准确理解黑话的含义
        2. 翻译后的内容要通俗易懂
        3. 解释黑话的来源和使用场景
        4. 保持语言的自然流畅
        """
        return ChatPromptTemplate.from_template(template)
    
    @staticmethod
    def translate_slang(input_text: str, model_name: str = "gpt-3.5-turbo") -> str:
        """
        翻译黑话
        
        Args:
            input_text: 要翻译的黑话
            model_name: 大模型名称
            
        Returns:
            翻译结果
        """
        if not LANGCHAIN_AVAILABLE:
            return "翻译失败: LangChain 未安装，请安装 langchain-openai 包"
        
        try:
            # 创建提示词模板
            prompt = SlangTranslatorSkill.create_prompt()
            
            # 创建模型
            model = ChatOpenAI(model=model_name)
            
            # 创建链
            chain = prompt | model
            
            # 执行翻译
            result = chain.invoke({"input_text": input_text})
            
            return result.content
        except Exception as e:
            return f"翻译失败: {str(e)}"
    
    @staticmethod
    def execute(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行黑话翻译技能
        
        Args:
            params: 输入参数，包含 input_text 和 model_name 字段
            
        Returns:
            执行结果，包含 translation 字段
        """
        try:
            input_text = params.get("input_text", "")
            model_name = params.get("model_name", "gpt-3.5-turbo")
            translation = SlangTranslatorSkill.translate_slang(input_text, model_name)
            return {
                "success": True,
                "translation": translation
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

# 注册技能
SkillRegistry.register("slang_translation", SlangTranslatorSkill)
