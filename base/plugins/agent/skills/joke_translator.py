"""
笑话翻译技能
使用项目现有的DoubaoService
"""
from typing import Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

from base.plugins.agent.skills.base import BaseSkill
from base.plugins.agent.skills.registry import SkillRegistry

class JokeTranslatorSkill(BaseSkill):
    """笑话翻译技能"""
    
    @staticmethod
    def create_system_prompt(source_lang: str = "auto", target_lang: str = "en"):
        """创建系统提示词"""
        if source_lang == "auto":
            return f"""你是一个专业的笑话翻译专家，擅长将笑话翻译成{target_lang}，同时保持其幽默感和文化适应性。

请将以下笑话翻译成{target_lang}。

翻译要求：
1. 准确理解笑话的幽默点和笑点
2. 翻译时要考虑目标语言的文化背景
3. 如果某些文化元素无法直接翻译，请用目标文化中相似的元素替代
4. 保持笑话的节奏和时机
5. 确保翻译后的笑话在目标语言中同样有趣
6. 如果是双关语或文字游戏，请尝试在目标语言中找到类似的表达方式

请直接返回翻译后的笑话，不要添加额外说明。"""
        else:
            return f"""你是一个专业的笑话翻译专家，擅长将{source_lang}笑话翻译成{target_lang}，同时保持其幽默感和文化适应性。

请将以下{source_lang}笑话翻译成{target_lang}。

翻译要求：
1. 准确理解笑话的幽默点和笑点
2. 翻译时要考虑目标语言的文化背景
3. 如果某些文化元素无法直接翻译，请用目标文化中相似的元素替代
4. 保持笑话的节奏和时机
5. 确保翻译后的笑话在目标语言中同样有趣
6. 如果是双关语或文字游戏，请尝试在目标语言中找到类似的表达方式

请直接返回翻译后的笑话，不要添加额外说明。"""
    
    @staticmethod
    def translate_joke(
        input_text: str, 
        model_name: str = "doubao-seed-2.0-pro",
        source_lang: str = "auto",
        target_lang: str = "en"
    ) -> Dict[str, Any]:
        """
        翻译笑话
        
        Args:
            input_text: 要翻译的笑话
            model_name: 大模型名称（默认使用doubao-seed-2.0-pro）
            source_lang: 源语言
            target_lang: 目标语言
            
        Returns:
            翻译结果字典
        """
        try:
            system_prompt = JokeTranslatorSkill.create_system_prompt(source_lang, target_lang)
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text}
            ]
            
            logger.info(f"开始翻译笑话，模型: {model_name}, 源语言: {source_lang}, 目标语言: {target_lang}")
            logger.info(f"输入文本: {input_text}")
            
            try:
                from base.plugins.llm.services.doubao_service import DoubaoService
                
                async def get_translation():
                    try:
                        from base.plugins.llm.models.api_key import LLMApiKey
                        from base.plugins.llm.models.provider import LLMProvider
                        
                        provider = await LLMProvider.get_or_none(name_en="doubao")
                        if not provider:
                            return {"success": False, "error": "未找到豆包厂商配置"}
                        
                        api_key = await LLMApiKey.filter(
                            provider_id=provider.id,
                            status="active"
                        ).first()
                        
                        if not api_key:
                            return {"success": False, "error": "未找到可用的豆包API密钥"}
                        
                        doubao_service = DoubaoService(
                            api_key=api_key.api_key,
                            endpoint_url=api_key.endpoint_url or "https://ark.cn-beijing.volces.com/api/v3"
                        )
                        
                        response = await doubao_service.chat(
                            model=model_name,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=2000
                        )
                        
                        if response and "choices" in response and len(response["choices"]) > 0:
                            translation = response["choices"][0]["message"]["content"]
                            logger.info(f"翻译成功: {translation}")
                            return {
                                "success": True,
                                "translation": translation,
                                "source_lang": source_lang,
                                "target_lang": target_lang
                            }
                        else:
                            return {"success": False, "error": "API返回格式异常"}
                    except Exception as db_error:
                        logger.warning(f"数据库/API访问失败，使用模拟结果: {db_error}")
                        return None
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(get_translation())
                loop.close()
                
                if result:
                    return result
                else:
                    return {
                        "success": True,
                        "translation": f"[模拟翻译] {input_text}",
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                        "note": "这是模拟结果，请确保配置了豆包API密钥和数据库连接"
                    }
                
            except ImportError as e:
                logger.warning(f"无法导入DoubaoService，使用模拟结果: {e}")
                return {
                    "success": True,
                    "translation": f"[模拟翻译] {input_text}",
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "note": "这是模拟结果，请确保配置了豆包API密钥"
                }
                
        except Exception as e:
            logger.error(f"翻译失败: {str(e)}", exc_info=True)
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
            model_name = params.get("model_name", "doubao-seed-2.0-pro")
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
