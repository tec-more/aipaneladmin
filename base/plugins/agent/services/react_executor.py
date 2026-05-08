
"""
ReAct Executor - ReAct 执行器
实现思考-行动-观察的完整循环
"""
import logging
import json
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator


logger = logging.getLogger(__name__)


class ReActStep:
    """单个 ReAct 步骤"""
    
    def __init__(self, step_type: str, content: str, tool_name: str = None, tool_args: Dict = None, tool_result: Any = None):
        self.step_type = step_type  # 'thought', 'action', 'observation'
        self.content = content
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.tool_result = tool_result
        self.timestamp = None


class ReActExecutor:
    """ReAct 执行器"""
    
    def __init__(
        self,
        llm_func: Callable,  # 大模型调用函数
        tool_registry,  # 工具注册表
        max_iterations: int = 5,
        sse_callback: Callable = None
    ):
        self.llm_func = llm_func
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.sse_callback = sse_callback
        self.steps = []
        self.messages = []
        self.iteration = 0
        
    async def execute(
        self,
        input_text: str,
        system_prompt: str,
        tools_schema: List[Dict],
        extra_context: Dict = None
    ) -&gt; Dict[str, Any]:
        """
        执行完整的 ReAct 循环
        
        Args:
            input_text: 用户输入
            system_prompt: 系统提示词
            tools_schema: 工具 schema 列表
            extra_context: 额外的上下文
            
        Returns:
            执行结果
        """
        self.messages = []
        self.steps = []
        self.iteration = 0
        
        # 初始化消息
        self.messages.append({"role": "system", "content": system_prompt})
        
        if extra_context and extra_context.get("memories"):
            for mem in extra_context["memories"]:
                self.messages.append({"role": "user", "content": f"【记忆】{mem}"})
                
        self.messages.append({"role": "user", "content": input_text})
        
        final_answer = ""
        
        while self.iteration &lt; self.max_iterations:
            self.iteration += 1
            
            # Step 1: 思考
            thought = await self._think(tools_schema)
            self.steps.append(thought)
            
            # 检查是否应该结束
            if self._should_finish(thought.content):
                final_answer = self._extract_final_answer(thought.content)
                if self.sse_callback:
                    await self.sse_callback({
                        "type": "thinking",
                        "content": final_answer
                    })
                break
                
            # Step 2: 行动（工具调用）
            action = await self._action(thought.content)
            if action:
                self.steps.append(action)
                
                # Step 3: 观察（工具执行）
                observation = await self._observe(action)
                self.steps.append(observation)
                
                # 记录观察结果
                if self.sse_callback:
                    await self.sse_callback({
                        "type": "observation",
                        "tool_name": action.tool_name,
                        "result": observation.content
                    })
                
                # 继续循环
                continue
            
            # 如果没有行动，提取答案
            final_answer = thought.content
            break
            
        return {
            "final_answer": final_answer,
            "steps": self._serialize_steps(),
            "messages": self.messages,
            "iterations": self.iteration
        }
        
    async def _think(self, tools_schema: List[Dict]) -&gt; ReActStep:
        """思考步骤"""
        if self.sse_callback:
            await self.sse_callback({
                "type": "thinking",
                "content": "正在分析..."
            })
            
        try:
            response = await self.llm_func(
                messages=self.messages,
                functions=tools_schema,
                function_call="auto"
            )
            
            content = response.get("content", "")
            thought = ReActStep("thought", content)
            return thought
        except Exception as e:
            logger.exception("Thinking failed")
            return ReActStep("thought", f"思考过程出错: {str(e)}")
            
    async def _action(self, thought_content: str) -&gt; Optional[ReActStep]:
        """行动步骤 - 解析思考结果，决定是否调用工具"""
        # 从思考结果中解析工具调用
        tool_name, tool_args = self._parse_tool_call(thought_content)
        
        if not tool_name:
            return None
            
        if self.sse_callback:
            await self.sse_callback({
                "type": "action",
                "tool_name": tool_name
            })
            
        return ReActStep("action", f"调用工具: {tool_name}", tool_name=tool_name, tool_args=tool_args)
        
    async def _observe(self, action: ReActStep) -&gt; ReActStep:
        """观察步骤 - 执行工具"""
        try:
            tool_class = self.tool_registry.get_tool(action.tool_name)
            if not tool_class:
                return ReActStep("observation", f"工具不存在: {action.tool_name}")
                
            result = await tool_class.execute(**(action.tool_args or {}))
            
            result_str = self._format_tool_result(result)
            
            # 添加到消息历史
            self.messages.append({
                "role": "assistant",
                "content": f"使用工具: {action.tool_name}\n参数: {json.dumps(action.tool_args, ensure_ascii=False)}"
            })
            
            self.messages.append({
                "role": "function",
                "name": action.tool_name,
                "content": result_str
            })
            
            return ReActStep("observation", result_str, tool_name=action.tool_name, tool_result=result)
        except Exception as e:
            logger.exception(f"Tool execution failed: {action.tool_name}")
            return ReActStep("observation", f"工具执行失败: {str(e)}")
            
    def _parse_tool_call(self, content: str) -&gt; tuple:
        """从思考内容中解析工具调用"""
        # 检查是否包含工具调用标记
        if "TOOL_CALL" in content or "调用工具" in content:
            # 尝试解析 JSON
            try:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start &gt;= 0 and json_end &gt; json_start:
                    json_str = content[json_start:json_end]
                    parsed = json.loads(json_str)
                    tool_name = parsed.get("name", parsed.get("tool", ""))
                    tool_args = parsed.get("args", parsed.get("params", {}))
                    return tool_name, tool_args
            except Exception:
                pass
                    
        # 尝试从 OpenAI 风格的函数调用中解析
        try:
            if "function_call" in content:
                # 这是 OpenAI API 的返回格式
                pass
        except Exception:
            pass
            
        return None, None
        
    def _should_finish(self, thought: str) -&gt; bool:
        """判断是否应该结束"""
        finish_indicators = ["FINAL_ANSWER", "最终答案", "回答:", "完成:", "答案:"]
        for indicator in finish_indicators:
            if indicator in thought:
                return True
        return False
        
    def _extract_final_answer(self, thought: str) -&gt; str:
        """提取最终答案"""
        finish_indicators = ["FINAL_ANSWER:", "最终答案:", "回答:", "完成:", "答案:"]
        
        for indicator in finish_indicators:
            if indicator in thought:
                idx = thought.index(indicator)
                return thought[idx + len(indicator):].strip()
                
        return thought
        
    def _format_tool_result(self, result: Any) -&gt; str:
        """格式化工具结果"""
        if isinstance(result, str):
            return result
        elif isinstance(result, (dict, list)):
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            return str(result)
            
    def _serialize_steps(self) -&gt; List[Dict]:
        """序列化步骤"""
        return [
            {
                "type": step.step_type,
                "content": step.content,
                "tool_name": step.tool_name,
                "tool_args": step.tool_args
            }
            for step in self.steps
        ]

