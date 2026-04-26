"""
软件开发任务分解技能
"""
from typing import Dict, Any
import json

try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from base.plugins.agent.skills.base import BaseSkill
from base.plugins.agent.skills.registry import SkillRegistry


class TaskDecomposerSkill(BaseSkill):
    """软件开发任务分解技能"""

    @staticmethod
    def create_decompose_prompt():
        """创建任务分解提示词模板"""
        if not LANGCHAIN_AVAILABLE:
            return None

        template = """你是一个资深的软件项目经理和架构师。

请将以下软件开发需求分解为具体的、可执行的子任务。

需求：{input_text}

请输出JSON格式，包含以下字段：
{{
    "project_type": "web/mobile/desktop/api/other",
    "subtasks": [
        {{
            "id": "1",
            "name": "任务名称",
            "description": "详细描述",
            "priority": "high/medium/low",
            "estimated_hours": 8,
            "dependencies": [],
            "assignee": "",
            "status": "pending"
        }}
    ],
    "total_estimated_hours": 0,
    "critical_path": []
}}

要求：
1. 任务粒度适中，每个任务4-40小时
2. 考虑技术栈、测试、部署等环节
3. 合理设置依赖关系
4. 优先级划分清晰
"""
        return ChatPromptTemplate.from_template(template)

    @staticmethod
    def create_refine_prompt():
        """创建优化提示词模板"""
        if not LANGCHAIN_AVAILABLE:
            return None

        template = """请根据反馈优化任务分解。

当前任务分解：
{current_tasks}

反馈意见：
{feedback}

请输出优化后的完整JSON。
"""
        return ChatPromptTemplate.from_template(template)

    @staticmethod
    def decompose_task(input_text: str, model_name: str = "gpt-3.5-turbo") -> Dict[str, Any]:
        """
        分解任务

        Args:
            input_text: 需求描述
            model_name: 大模型名称

        Returns:
            分解结果
        """
        if not LANGCHAIN_AVAILABLE:
            return {
                "success": False,
                "message": "LangChain 未安装，请安装 langchain-openai 包",
                "fallback": {
                    "project_type": "unknown",
                    "subtasks": [
                        {
                            "id": "1",
                            "name": "需求分析",
                            "description": "分析用户需求",
                            "priority": "high",
                            "estimated_hours": 8,
                            "dependencies": []
                        }
                    ]
                }
            }

        try:
            prompt = TaskDecomposerSkill.create_decompose_prompt()
            model = ChatOpenAI(model=model_name)
            chain = prompt | model
            result = chain.invoke({"input_text": input_text})

            content = result.content
            json_start = content.find("{")
            json_end = content.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                parsed = json.loads(json_str)
                return {
                    "success": True,
                    "result": parsed
                }
            else:
                return {
                    "success": False,
                    "message": "无法解析JSON",
                    "raw_output": content
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"任务分解失败: {str(e)}"
            }

    @staticmethod
    def execute(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务分解技能

        Args:
            params: 输入参数，包含 input_text 和 model_name 字段

        Returns:
            执行结果
        """
        try:
            input_text = params.get("input_text", "")
            model_name = params.get("model_name", "gpt-3.5-turbo")

            result = TaskDecomposerSkill.decompose_task(input_text, model_name)

            if result.get("success"):
                return {
                    "success": True,
                    "task_decomposition": result.get("result")
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message"),
                    "fallback": result.get("fallback")
                }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }


SkillRegistry.register("task_decomposer", TaskDecomposerSkill)
