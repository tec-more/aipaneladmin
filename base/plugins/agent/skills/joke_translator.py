"""
笑话翻译技能
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

class JokeTranslatorSkill(BaseSkill):
    """笑话翻译技能"""
    
    @staticmethod
    def create_prompt(source_lang: str = "auto", target_lang: str = "en"):
        """创建提示词模板"""
        if not LANGCHAIN_AVAILABLE:
            return None
        
        if source_lang == "auto":
            template = f"""
你是一个专业的笑话翻译专家，擅长将笑话翻译成{target_lang}，同时保持其幽默感和文化适应性。

请将以下笑话翻译成{target_lang}：

{{input_text}}

翻译要求：
1. 准确理解笑话的幽默点和笑点
2. 翻译时要考虑目标语言的文化背景
3. 如果某些文化元素无法直接翻译，请用目标文化中相似的元素替代
4. 保持笑话的节奏和时机
5. 确保翻译后的笑话在目标语言中同样有趣
6. 如果是双关语或文字游戏，请尝试在目标语言中找到类似的表达方式
7. 在翻译后，简要说明翻译策略和任何文化适应的调整

请提供：
1. 翻译后的笑话
2. 翻译说明（解释如何保持幽默感）
3. 文化适应说明（如果有）
"""
        else:
            template = f"""
你是一个专业的笑话翻译专家，擅长将{source_lang}笑话翻译成{target_lang}，同时保持其幽默感和文化适应性。

请将以下{source_lang}笑话翻译成{target_lang}：

{{input_text}}

翻译要求：
1. 准确理解笑话的幽默点和笑点
2. 翻译时要考虑目标语言的文化背景
3. 如果某些文化元素无法直接翻译，请用目标文化中相似的元素替代
4. 保持笑话的节奏和时机
5. 确保翻译后的笑话在目标语言中同样有趣
6. 如果是双关语或文字游戏，请尝试在目标语言中找到类似的表达方式
7. 在翻译后，简要说明翻译策略和任何文化适应的调整

请提供：
1. 翻译后的笑话
2. 翻译说明（解释如何保持幽默感）
3. 文化适应说明（如果有）
"""
        return ChatPromptTemplate.from_template(template)
    
    @staticmethod
    def translate_joke(
        input_text: str, 
        model_name: str = "gpt-3.5-turbo",
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> Dict[str, str]:
        """
        翻译笑话
        
        Args:
            input_text: 要翻译的笑话
            model_name: 大模型名称
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            翻译结果字典
        """
        if not LANGCHAIN_AVAILABLE:
            return {
                "success": False,
                "error": "LangChain 未安装，请安装 langchain-openai 包"
            }
        
        try:
            prompt = JokeTranslatorSkill.create_prompt(source_lang, target_lang)
            
            model = ChatOpenAI(model=model_name)
            
            chain = prompt | model
            
            result = chain.invoke({"input_text": input_text})
            
            return {
                "success": True,
                "translation": result.content,
                "source_lang": source_lang,
                "target_lang": target_lang
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def execute(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行笑话翻译技能
        
        Args:
            params: 输入参数，包含：
                - input_text: 要翻译的笑话
                - model_name: 大模型名称（可选）
                - source_lang: 源语言（可选，默认auto）
                - target_lang: 目标语言（可选，默认en）
            
        Returns:
            执行结果
        """
        try:
            input_text = params.get("input_text", "")
            model_name = params.get("model_name", "gpt-3.5-turbo")
            source_lang = params.get("source_lang", "auto")
            target_lang = params.get("target_lang", "en")
            
            if not input_text:
                return {
                    "success": False,
                    "message": "输入文本不能为空"
                }
            
            result = JokeTranslatorSkill.translate_joke(
                input_text, 
                model_name, 
                source_lang, 
                target_lang
            )
            
            return result
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

SkillRegistry.register("joke_translation", JokeTranslatorSkill)
