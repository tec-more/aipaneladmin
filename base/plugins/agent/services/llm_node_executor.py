
"""
LLM Node Executor - 专门的 LLM 节点执行器
集成技能和 ReAct 逻辑
"""
import logging
from typing import Dict, Any


logger = logging.getLogger(__name__)


async def execute_llm_node(
    current_node: Dict, 
    state: Dict,
    node_label: str = None
) -&gt; Dict:
    """
    执行 LLM 节点
    
    流程：
    1. 加载技能配置
    2. 解析技能绑定的工具
    3. 准备系统提示词
    4. 调用大模型（带 ReAct）
    5. 返回结果
    
    Args:
        current_node: 节点数据
        state: 当前状态
        node_label: 节点标签
        
    Returns:
        更新后的状态
    """
    node_data = current_node.get("data", {})
    prompt = node_data.get("prompt", "")
    skill_ids = node_data.get("skill_ids", []) or node_data.get("skillIds", [])
    model_id = node_data.get("model_id") or node_data.get("modelId")
    enable_react = node_data.get("enable_react", True)
    max_iterations = node_data.get("max_iterations", 5)
    
    # 步骤1: 加载技能和工具
    llm_context = await _load_skill_context(skill_ids, prompt)
    
    system_prompt = llm_context["system_prompt"]
    tools_schema = llm_context["tools_schema"]
    
    # 步骤2: 处理变量替换
    final_prompt = _replace_variables(prompt, state.get("variables", {}))
    input_text = _get_input_text(state)
    
    # 准备用户输入
    if final_prompt and input_text:
        user_input = final_prompt.replace("{{input}}", input_text) if "{{input}}" in final_prompt else f"{final_prompt}\n\n用户输入：{input_text}"
    elif final_prompt:
        user_input = final_prompt
    else:
        user_input = input_text
        
    # 步骤3: 获取模型
    from base.plugins.llm.models.model import LLMModel
    target_model = None
    if model_id:
        target_model = await LLMModel.filter(id=model_id, status="active").first()
    if not target_model:
        target_model = await LLMModel.filter(status="active").first()
        
    if not target_model:
        state["variables"]["llm_output"] = {
            "response": "没有可用的大模型",
            "model": "none"
        }
        return state
        
    actual_model = target_model.model_name
    logger.info(f"Using model: {actual_model} with {len(tools_schema)} tools")
    
    # 步骤4: 调用 LLM（带 ReAct）
    if enable_react and tools_schema:
        result = await _execute_with_react(
            target_model=target_model,
            user_input=user_input,
            system_prompt=system_prompt,
            tools_schema=tools_schema,
            state=state,
            max_iterations=max_iterations
        )
    else:
        result = await _execute_simple(
            target_model=target_model,
            user_input=user_input,
            system_prompt=system_prompt
        )
        
    # 步骤5: 更新状态
    output_variable = node_data.get("output_variable", "llm_output")
    state["variables"][output_variable] = {
        "prompt": prompt,
        "model": actual_model,
        "response": result.get("final_answer", ""),
        "react_steps": result.get("steps", [])
    }
    
    return state


async def _load_skill_context(skill_ids: list, base_prompt: str) -&gt; Dict:
    """加载技能上下文"""
    from base.plugins.agent.models.skill import Skill
    from base.plugins.agent.services.skill_service import SkillService
    from base.plugins.agent.tools.registry import ToolRegistry
    
    all_prompts = []
    all_tools = {}
    bound_tools_set = set()
    
    # 加载每个技能
    for skill_id in skill_ids:
        try:
            skill = await Skill.get_or_none(id=skill_id, status="active")
            if skill:
                # 提取技能的提示词部分
                prompt = _extract_skill_prompt(skill)
                if prompt:
                    all_prompts.append(f"【技能：{skill.name}】\n{prompt}")
                    
                # 解析工具
                bound_tools = SkillService.parse_bound_tools(skill.implementation)
                bound_tools_set.update(bound_tools)
                
        except Exception as e:
            logger.exception(f"Failed to load skill {skill_id}")
            
    # 构建完整系统提示词
    system_prompt = "\n\n".join(all_prompts)
    if base_prompt:
        system_prompt = f"{base_prompt}\n\n{system_prompt}"
    if not system_prompt:
        system_prompt = "You are a helpful assistant."
        
    # 获取工具 Schema
    tool_list = []
    all_tools_info = ToolRegistry.get_all_tools_info()
    for tool_name in bound_tools_set:
        if tool_name in all_tools_info:
            tool_list.append(all_tools_info[tool_name])
            
    return {
        "system_prompt": system_prompt,
        "tools_schema": tool_list,
        "bound_tools": list(bound_tools_set)
    }


def _extract_skill_prompt(skill) -&gt; str:
    """从技能中提取提示词部分"""
    if not skill.implementation:
        return skill.description or ""
        
    lines = skill.implementation.split("\n")
    prompt_lines = []
    in_prompt = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("##"):
            if "描述" in stripped or "指令" in stripped or "任务" in stripped or "提示" in stripped:
                in_prompt = True
                continue
            elif "可用工具" in stripped:
                in_prompt = False
                continue
        if in_prompt and stripped:
            prompt_lines.append(line)
            
    if prompt_lines:
        return "\n".join(prompt_lines)
    return skill.description or ""


def _replace_variables(text: str, variables: Dict) -&gt; str:
    """替换变量"""
    if not text:
        return text
    result = text
    for key, value in variables.items():
        try:
            result = result.replace(f"{{{{{key}}}}}", str(value))
        except Exception:
            pass
    return result


def _get_input_text(state: Dict) -&gt; str:
    """获取输入文本"""
    variables = state.get("variables", {})
    input_data = variables.get("input", {})
    return input_data.get("text", "")


async def _execute_with_react(
    target_model,
    user_input: str,
    system_prompt: str,
    tools_schema: list,
    state: Dict,
    max_iterations: int
) -&gt; Dict:
    """使用 ReAct 执行"""
    from base.plugins.agent.services.react_executor import ReActExecutor
    from base.plugins.agent.tools.registry import ToolRegistry
    
    # 创建 LLM 函数
    async def llm_func(messages, functions=None, function_call="auto"):
        return await _call_llm(
            target_model=target_model,
            messages=messages,
            functions=functions,
            function_call=function_call
        )
        
    # 准备额外上下文
    extra_context = {"memories": []}
    variables = state.get("variables", {})
    for memory_source in ["recent_memories", "important_memories"]:
        if variables.get(memory_source):
            for m in variables[memory_source]:
                content = m.get("content", m) if isinstance(m, dict) else str(m)
                extra_context["memories"].append(content)
    
    # 执行 ReAct
    executor = ReActExecutor(
        llm_func=llm_func,
        tool_registry=ToolRegistry,
        max_iterations=max_iterations
    )
    
    result = await executor.execute(
        input_text=user_input,
        system_prompt=system_prompt,
        tools_schema=tools_schema,
        extra_context=extra_context
    )
    
    return result


async def _execute_simple(target_model, user_input: str, system_prompt: str) -&gt; Dict:
    """简单执行，不使用 ReAct"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    
    response = await _call_llm(target_model, messages)
    
    return {
        "final_answer": response.get("content", ""),
        "steps": []
    }


async def _call_llm(target_model, messages: list, functions=None, function_call="auto"):
    """调用大模型"""
    from base.plugins.llm.services.chat_service import ChatService
    from base.plugins.llm.models.provider import LLMProvider
    from base.plugins.llm.models.api_key import LLMApiKey
    
    try:
        provider = await LLMProvider.get_or_none(id=target_model.provider_id)
        api_key = await LLMApiKey.filter(model_id=target_model.id).first()
        
        if not provider or not api_key:
            return {"content": "无法获取 LLM 配置"}
            
        endpoint_url = target_model.endpoint_url or provider.api_endpoint
        if endpoint_url:
            endpoint_url = endpoint_url.rstrip('/')
            
        service = await ChatService.get_provider_service(
            provider_name_en=provider.name_en,
            api_key=api_key.api_key,
            endpoint_url=endpoint_url,
            api_secret=api_key.api_secret
        )
        
        actual_model_for_call = target_model.model_id if target_model.model_id else target_model.model_name
        
        chat_kwargs = {
            "model": actual_model_for_call,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        if functions:
            chat_kwargs["functions"] = functions
            chat_kwargs["function_call"] = function_call
            
        response = await service.chat(**chat_kwargs)
        
        if isinstance(response, dict) and response.get("choices"):
            return response["choices"][0].get("message", {})
        return {"content": str(response)}
            
    except Exception as e:
        logger.exception(f"Failed to call LLM")
        return {"content": f"调用大模型失败: {str(e)}"}

