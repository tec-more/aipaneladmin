"""
LangGraph 执行器 - 使用真正的 LangGraph 执行智能体结构图
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
from operator import add

from tortoise.exceptions import DoesNotExist

# LangGraph 和 LangChain 相关导入
try:
    from langchain_core.runnables import RunnableConfig
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    from langgraph.graph import StateGraph, END, START
    from langgraph.checkpoint.memory import MemorySaver
    from langchain.memory import ConversationSummaryBufferMemory
    from langchain.llms import OpenAI
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

# HTTP 客户端
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

from base.plugins.agent.models.agent import Agent
from base.plugins.agent.models.skill import Skill
from base.plugins.llm.models.model import LLMModel


class AgentState(TypedDict):
    """智能体状态类型定义"""
    input: Dict[str, Any]
    output: Dict[str, Any]
    messages: Annotated[List[BaseMessage], add]
    variables: Dict[str, Any]
    node_results: Dict[str, Any]
    execution_trace: List[Dict[str, Any]]
    current_node: Optional[str]
    error: Optional[str]
    agent: Optional[Agent]


class LangGraphExecutor:
    """
    LangGraph 执行器
    
    使用真正的 LangGraph 来执行智能体结构图
    集成 LangChain Memory (ConversationSummaryBufferMemory)
    """
    
    # 记忆缓存：agent_id -> memory_instance
    _memory_cache: Dict[int, Any] = {}

    @staticmethod
    def _get_agent_memory(agent: Agent):
        """
        获取或创建智能体的记忆实例
        
        Args:
            agent: 智能体对象
            
        Returns:
            LangChain Memory 实例
        """
        if agent.id in LangGraphExecutor._memory_cache:
            return LangGraphExecutor._memory_cache[agent.id]
        
        if LANGGRAPH_AVAILABLE:
            try:
                memory = ConversationSummaryBufferMemory(
                    llm=OpenAI(temperature=0),
                    max_token_limit=1000,
                    return_messages=True
                )
                LangGraphExecutor._memory_cache[agent.id] = memory
                return memory
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"创建 LangChain Memory 失败: {e}")
        
        return None

    @staticmethod
    async def execute_agent(
        agent: Agent,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行智能体
        
        Args:
            agent: 智能体对象
            input_data: 输入数据
            
        Returns:
            执行结果
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"执行智能体 (LangGraph): {agent.name}")
        
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph 不可用，使用简化执行方式")
            return await LangGraphExecutor._execute_simple(agent, input_data)
        
        try:
            # 检查是否有结构图配置
            flow_data = None
            if agent.graph_definition:
                flow_data = agent.graph_definition
            
            if flow_data and flow_data.get("nodes"):
                # 使用 LangGraph 执行
                logger.info("使用 LangGraph 执行结构图")
                return await LangGraphExecutor._execute_with_langgraph(
                    agent=agent,
                    flow_data=flow_data,
                    input_data=input_data
                )
            else:
                # 没有结构图，使用简化的直接执行方式
                logger.info("没有配置结构图，使用简化执行方式")
                return await LangGraphExecutor._execute_simple(agent, input_data)
            
        except Exception as e:
            logger.exception(f"执行智能体失败: {str(e)}")
            import traceback
            return {
                "success": False,
                "message": str(e),
                "traceback": traceback.format_exc()
            }

    @staticmethod
    async def _execute_with_langgraph(
        agent: Agent,
        flow_data: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用 LangGraph 执行智能体结构图
        
        Args:
            agent: 智能体对象
            flow_data: 结构图数据
            input_data: 输入数据
            
        Returns:
            执行结果
        """
        import logging
        logger = logging.getLogger(__name__)
        
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])
        
        if not nodes:
            logger.warning("结构图没有节点，使用简化执行方式")
            return await LangGraphExecutor._execute_simple(agent, input_data)
        
        # 获取或创建 LangChain 记忆
        memory = LangGraphExecutor._get_agent_memory(agent)
        
        # 从记忆中加载历史消息
        messages = []
        if memory:
            try:
                memory_vars = memory.load_memory_variables({})
                messages = memory_vars.get("history", [])
                logger.info(f"从记忆加载了 {len(messages)} 条历史消息")
            except Exception as e:
                logger.warning(f"加载记忆失败: {e}")
        
        # 构建 LangGraph
        graph = await LangGraphExecutor._build_langgraph(nodes, edges, agent)
        
        if not graph:
            logger.error("构建 LangGraph 失败")
            return {
                "success": False,
                "message": "构建 LangGraph 失败"
            }
        
        # 初始化状态
        initial_state: AgentState = {
            "input": input_data,
            "output": {},
            "messages": messages,
            "variables": {},
            "node_results": {},
            "execution_trace": [],
            "current_node": None,
            "error": None,
            "agent": agent
        }
        
        # 执行图
        config = RunnableConfig(recursion_limit=100)
        result = await graph.ainvoke(initial_state, config)
        
        # 保存到记忆
        if memory:
            try:
                input_text = input_data.get("text", "")
                output_text = result.get("output", {}).get("result", "") or str(result.get("output", {}))
                
                memory.save_context(
                    {"input": input_text},
                    {"output": output_text}
                )
                logger.info("对话已保存到记忆")
            except Exception as e:
                logger.warning(f"保存记忆失败: {e}")
        
        if result.get("error"):
            return {
                "success": False,
                "message": result["error"],
                "input": input_data,
                "output": result.get("output", {}),
                "trace": result.get("execution_trace", [])
            }
        
        return {
            "success": True,
            "message": "执行成功",
            "input": input_data,
            "output": result.get("output", {}),
            "variables": result.get("variables", {}),
            "trace": result.get("execution_trace", [])
        }

    @staticmethod
    async def _build_langgraph(
        nodes: List[Dict],
        edges: List[Dict],
        agent: Agent
    ):
        """
        从 JSON 数据构建 LangGraph
        
        Args:
            nodes: 节点列表
            edges: 边列表
            agent: 智能体对象
            
        Returns:
            编译后的 LangGraph
        """
        graph = StateGraph(AgentState)
        
        # 节点映射
        node_map = {node.get("id"): node for node in nodes}
        
        # 添加所有节点
        for node in nodes:
            node_id = node.get("id")
            node_type = node.get("type", "unknown")
            node_data = node.get("data", {})
            
            # 创建节点函数
            node_func = LangGraphExecutor._create_node_function(
                node_type, node_data, node_id, agent
            )
            graph.add_node(node_id, node_func)
        
        # 找到开始节点
        start_node = LangGraphExecutor._find_start_node(nodes)
        if not start_node:
            return None
        
        # 设置入口点
        graph.set_entry_point(start_node.get("id"))
        
        # 添加边
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            edge_data = edge.get("data", {})
            
            if source and target and source in node_map and target in node_map:
                # 检查是否是条件边
                source_node = node_map.get(source)
                if source_node and source_node.get("type") == "condition":
                    # 条件边 - 使用 add_conditional_edges
                    condition_func = LangGraphExecutor._create_condition_function(
                        source_node, edges, node_map
                    )
                    
                    # 构建边映射
                    edge_mapping = {}
                    for e in edges:
                        if e.get("source") == source:
                            t = e.get("target")
                            edge_mapping[t] = t
                    
                    graph.add_conditional_edges(source, condition_func, edge_mapping)
                else:
                    # 普通边
                    graph.add_edge(source, target)
        
        # 编译图
        checkpointer = MemorySaver()
        return graph.compile(checkpointer=checkpointer)

    @staticmethod
    def _find_start_node(nodes: List[Dict]) -> Optional[Dict]:
        """找到开始节点"""
        for node in nodes:
            if node.get("type") == "start":
                return node
        
        # 如果没有 start 类型节点，找第一个节点
        return nodes[0] if nodes else None

    @staticmethod
    def _create_node_function(
        node_type: str,
        node_data: Dict,
        node_id: str,
        agent: Agent
    ):
        """
        创建节点执行函数
        
        Args:
            node_type: 节点类型
            node_data: 节点数据
            node_id: 节点 ID
            agent: 智能体对象
            
        Returns:
            节点执行函数
        """
        async def node_func(state: AgentState) -> AgentState:
            import logging
            logger = logging.getLogger(__name__)
            
            label = node_data.get("label", node_id)
            
            # 记录执行轨迹
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": node_type,
                "label": label,
                "timestamp": datetime.now().isoformat()
            })
            
            state["current_node"] = node_id
            
            try:
                if node_type == "start":
                    return await LangGraphExecutor._execute_start_node(node_data, state)
                elif node_type == "end":
                    return await LangGraphExecutor._execute_end_node(node_data, state)
                elif node_type == "input":
                    return await LangGraphExecutor._execute_input_node(node_data, state)
                elif node_type == "output":
                    return await LangGraphExecutor._execute_output_node(node_data, state)
                elif node_type == "agent":
                    return await LangGraphExecutor._execute_agent_node(node_data, state)
                elif node_type == "llm":
                    return await LangGraphExecutor._execute_llm_node(node_data, state)
                elif node_type == "skill":
                    return await LangGraphExecutor._execute_skill_node(node_data, state)
                elif node_type == "condition":
                    return await LangGraphExecutor._execute_condition_node(node_data, state)
                elif node_type == "loop":
                    return await LangGraphExecutor._execute_loop_node(node_data, state)
                elif node_type == "iteration":
                    return await LangGraphExecutor._execute_iteration_node(node_data, state)
                elif node_type == "http":
                    return await LangGraphExecutor._execute_http_node(node_data, state)
                elif node_type == "code":
                    return await LangGraphExecutor._execute_code_node(node_data, state)
                elif node_type == "template":
                    return await LangGraphExecutor._execute_template_node(node_data, state)
                elif node_type == "variable_aggregator":
                    return await LangGraphExecutor._execute_variable_aggregator_node(node_data, state)
                elif node_type == "document_extractor":
                    return await LangGraphExecutor._execute_document_extractor_node(node_data, state)
                elif node_type == "variable_assigner":
                    return await LangGraphExecutor._execute_variable_assigner_node(node_data, state)
                elif node_type == "parameter_extractor":
                    return await LangGraphExecutor._execute_parameter_extractor_node(node_data, state)
                else:
                    return await LangGraphExecutor._execute_default_node(node_data, state)
                    
            except Exception as e:
                logger.exception(f"执行节点失败: {label}")
                state["error"] = str(e)
                state["output"]["error"] = str(e)
                return state
        
        return node_func

    @staticmethod
    def _create_condition_function(
        source_node: Dict,
        edges: List[Dict],
        node_map: Dict[str, Dict]
    ):
        """
        创建条件判断函数
        
        Args:
            source_node: 源节点
            edges: 边列表
            node_map: 节点映射
            
        Returns:
            条件判断函数
        """
        def condition_func(state: AgentState) -> str:
            """条件判断函数"""
            variables = state.get("variables", {})
            condition_result = variables.get("condition_result", {}).get("result", False)
            
            # 找到从源节点出发的边
            outgoing_edges = [e for e in edges if e.get("source") == source_node.get("id")]
            
            if len(outgoing_edges) >= 2:
                # 根据条件结果返回对应的目标节点
                target_index = 0 if condition_result else 1
                if target_index < len(outgoing_edges):
                    return outgoing_edges[target_index].get("target")
            
            # 默认返回第一条边
            if outgoing_edges:
                return outgoing_edges[0].get("target")
            
            return END
        
        return condition_func

    @staticmethod
    async def _execute_start_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行开始节点"""
        state["variables"]["start_time"] = datetime.now().isoformat()
        return state

    @staticmethod
    async def _execute_end_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行结束节点"""
        state["output"]["end_time"] = datetime.now().isoformat()
        return state

    @staticmethod
    async def _execute_input_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行输入节点"""
        state["variables"]["input"] = state["input"]
        return state

    @staticmethod
    async def _execute_output_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行输出节点"""
        output_var = node_data.get("output_var", "result")
        output_content = node_data.get("output_content", "")
        
        variables = state.get("variables", {})
        
        if output_content:
            rendered = LangGraphExecutor._render_template(output_content, variables)
            state["output"][output_var] = rendered
        else:
            state["output"][output_var] = variables
        
        return state

    @staticmethod
    async def _execute_agent_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行智能体节点"""
        agent_id = node_data.get("agent_id")
        prompt = node_data.get("prompt", "")
        label = node_data.get("label", "agent")
        
        variables = state.get("variables", {})
        
        try:
            if agent_id:
                other_agent = await Agent.get_or_none(id=agent_id)
                if other_agent:
                    rendered_prompt = LangGraphExecutor._render_template(prompt, variables)
                    
                    result = await LangGraphExecutor.execute_agent(
                        agent=other_agent,
                        input_data={
                            "text": rendered_prompt,
                            **variables
                        }
                    )
                    
                    state["node_results"][label] = result
                    variables[f"agent_{agent_id}_result"] = result
                else:
                    variables[f"agent_{agent_id}_result"] = {"error": "Agent not found"}
        except Exception as e:
            variables[f"agent_{agent_id}_result"] = {"error": str(e)}
        
        return state

    @staticmethod
    async def _execute_llm_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行LLM节点"""
        model_id = node_data.get("model_id")
        prompt = node_data.get("prompt", "")
        temperature = node_data.get("temperature", 0.7)
        label = node_data.get("label", "llm")
        
        variables = state.get("variables", {})
        
        try:
            if model_id:
                model = await LLMModel.get_or_none(id=model_id)
                if model:
                    rendered_prompt = LangGraphExecutor._render_template(prompt, variables)
                    
                    result = {
                        "model": model.model_name,
                        "provider": model.provider_name,
                        "prompt": rendered_prompt,
                        "temperature": temperature,
                        "response": f"Simulated LLM response from {model.model_name}"
                    }
                else:
                    result = {"error": f"Model {model_id} not found"}
            else:
                result = {"error": "No model selected"}
        except Exception as e:
            result = {"error": str(e)}
        
        variables[f"llm_{model_id}_result"] = result
        state["node_results"][label] = result
        
        return state

    @staticmethod
    async def _execute_skill_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行技能节点"""
        skill_id = node_data.get("skill_id")
        label = node_data.get("label", "skill")
        
        variables = state.get("variables", {})
        
        try:
            if skill_id:
                skill = await Skill.get_or_none(id=skill_id)
                if skill:
                    from base.plugins.agent.services.skill_service import SkillService
                    result = await SkillService.execute_skill(skill_id, variables)
                else:
                    result = {"error": f"Skill {skill_id} not found"}
            else:
                result = {"error": "No skill selected"}
        except Exception as e:
            result = {"error": str(e)}
        
        variables[f"skill_{skill_id}_result"] = result
        state["node_results"][label] = result
        
        return state

    @staticmethod
    async def _execute_condition_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行条件节点"""
        condition = node_data.get("condition", "")
        label = node_data.get("label", "condition")
        
        variables = state.get("variables", {})
        
        try:
            condition_result = LangGraphExecutor._evaluate_condition(condition, variables)
            result = {"condition": condition, "result": condition_result}
        except Exception as e:
            result = {"error": str(e), "result": False}
            condition_result = False
        
        variables["condition_result"] = result
        state["node_results"][label] = result
        
        return state

    @staticmethod
    async def _execute_loop_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行循环节点"""
        loop_condition = node_data.get("loop_condition", "i < 5")
        loop_max = node_data.get("loop_max", 10)
        loop_variable = node_data.get("loop_variable", "i")
        label = node_data.get("label", "loop")
        
        variables = state.get("variables", {})
        loop_states = variables.get("_loop_states", {})
        
        loop_key = f"loop_{label}"
        loop_state = loop_states.get(loop_key, {
            "count": 0,
            "in_progress": False
        })
        
        if not loop_state.get("in_progress", False):
            loop_state["in_progress"] = True
            loop_state["count"] = 0
            variables[loop_variable] = 0
        
        current_count = loop_state.get("count", 0)
        variables[loop_variable] = current_count
        
        condition_result = LangGraphExecutor._evaluate_condition(loop_condition, variables)
        should_continue = condition_result and current_count < loop_max
        
        if should_continue:
            loop_state["count"] = current_count + 1
            loop_states[loop_key] = loop_state
            variables["_loop_states"] = loop_states
        else:
            loop_state["in_progress"] = False
            loop_states[loop_key] = loop_state
            variables["_loop_states"] = loop_states
        
        return state

    @staticmethod
    async def _execute_iteration_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行迭代节点"""
        iteration_list = node_data.get("iteration_list", "")
        iteration_variable = node_data.get("iteration_variable", "item")
        label = node_data.get("label", "iteration")
        
        variables = state.get("variables", {})
        loop_states = variables.get("_loop_states", {})
        
        iteration_key = f"iteration_{label}"
        iteration_state = loop_states.get(iteration_key, {
            "index": 0,
            "in_progress": False,
            "items": []
        })
        
        if not iteration_state.get("in_progress", False):
            try:
                if iteration_list in variables:
                    items = variables.get(iteration_list, [])
                else:
                    items = json.loads(iteration_list)
                
                if not isinstance(items, list):
                    items = [items]
                
                iteration_state["items"] = items
                iteration_state["index"] = 0
                iteration_state["in_progress"] = True
            except:
                iteration_state["items"] = []
                iteration_state["in_progress"] = False
        
        items = iteration_state.get("items", [])
        current_index = iteration_state.get("index", 0)
        
        if current_index < len(items) and iteration_state.get("in_progress", False):
            variables[iteration_variable] = items[current_index]
            iteration_state["index"] = current_index + 1
            loop_states[iteration_key] = iteration_state
            variables["_loop_states"] = loop_states
        else:
            iteration_state["in_progress"] = False
            loop_states[iteration_key] = iteration_state
            variables["_loop_states"] = loop_states
        
        return state

    @staticmethod
    async def _execute_http_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行HTTP节点"""
        method = node_data.get("method", "GET")
        url = node_data.get("url", "")
        headers = node_data.get("headers", "{}")
        body = node_data.get("body", "{}")
        label = node_data.get("label", "http")
        
        variables = state.get("variables", {})
        
        try:
            rendered_url = LangGraphExecutor._render_template(url, variables)
            rendered_headers = LangGraphExecutor._render_template(headers, variables)
            rendered_body = LangGraphExecutor._render_template(body, variables)
            
            try:
                if HTTPX_AVAILABLE:
                    async with httpx.AsyncClient(timeout=30) as client:
                        request_headers = json.loads(rendered_headers) if rendered_headers else {}
                        request_body = json.loads(rendered_body) if rendered_body else {}
                        
                        if method == "GET":
                            response = await client.get(rendered_url, headers=request_headers)
                        elif method == "POST":
                            response = await client.post(rendered_url, headers=request_headers, json=request_body)
                        elif method == "PUT":
                            response = await client.put(rendered_url, headers=request_headers, json=request_body)
                        elif method == "DELETE":
                            response = await client.delete(rendered_url, headers=request_headers)
                        else:
                            response = None
                        
                        if response:
                            result = {
                                "status_code": response.status_code,
                                "headers": dict(response.headers),
                                "content": response.text
                            }
                        else:
                            result = {"error": f"Unsupported method: {method}"}
                else:
                    result = {
                        "status_code": 200,
                        "content": "httpx not available",
                        "url": rendered_url
                    }
            except ImportError:
                result = {
                    "status_code": 200,
                    "content": "httpx not available",
                    "url": rendered_url
                }
        except Exception as e:
            result = {"error": str(e)}
        
        variables["http_result"] = result
        state["node_results"][label] = result
        
        return state

    @staticmethod
    async def _execute_code_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行代码节点"""
        language = node_data.get("language", "python")
        code = node_data.get("code", "")
        label = node_data.get("label", "code")
        
        variables = state.get("variables", {})
        
        try:
            if language == "python":
                exec_globals = {
                    "state": state,
                    "variables": variables,
                    "json": json,
                    "asyncio": asyncio
                }
                
                exec(code, exec_globals)
                result = exec_globals.get("result", "Code executed successfully")
            else:
                result = f"Unsupported language: {language}"
        except Exception as e:
            result = {"error": str(e)}
        
        variables["code_result"] = result
        state["node_results"][label] = result
        
        return state

    @staticmethod
    async def _execute_default_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行默认节点"""
        return state

    @staticmethod
    async def _execute_simple(
        agent: Agent,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        简化的执行方式（当没有配置结构图时使用）
        
        Args:
            agent: 智能体对象
            input_data: 输入数据
            
        Returns:
            执行结果
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info("使用简化执行方式")
        
        try:
            input_text = input_data.get("text", "")
            
            config = agent.config or {}
            skills_config = config.get("skills", [])
            model_config = config.get("model", {})
            
            if not skills_config:
                return {
                    "success": False,
                    "message": "No skills configured for agent"
                }
            
            model_name = model_config.get("model_name", "gpt-3.5-turbo")
            skill_id = skills_config[0] if skills_config else None
            
            if not skill_id:
                return {
                    "success": False,
                    "message": "No skill configured for agent"
                }
            
            from base.plugins.agent.services.skill_service import SkillService
            result = await SkillService.execute_skill(
                skill_id,
                {
                    "input_text": input_text,
                    "model_name": model_name,
                    **input_data
                }
            )
            
            return result
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "message": str(e),
                "traceback": traceback.format_exc()
            }

    @staticmethod
    def _render_template(template: str, variables: Dict) -> str:
        """渲染模板字符串"""
        if not template:
            return ""
        
        result = template
        
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value))
        
        return result

    @staticmethod
    def _evaluate_condition(condition: str, variables: Dict) -> bool:
        """评估条件表达式"""
        from base.plugins.agent.utils.safe_eval import safe_eval_condition
        return safe_eval_condition(condition, variables)
    
    @staticmethod
    async def _execute_template_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行模板转换节点"""
        template = node_data.get("template", "")
        output_var = node_data.get("output_var", "template_output")
        label = node_data.get("label", "template")
        
        variables = state.get("variables", {})
        
        try:
            rendered = LangGraphExecutor._render_template(template, variables)
            result = {
                "success": True,
                "template": template,
                "output": rendered
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        variables[output_var] = result
        state["node_results"][label] = result
        
        return state
    
    @staticmethod
    async def _execute_variable_aggregator_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行变量聚合器节点"""
        input_vars = node_data.get("input_vars", "")
        output_var = node_data.get("output_var", "aggregated_output")
        label = node_data.get("label", "variable_aggregator")
        
        variables = state.get("variables", {})
        
        try:
            var_list = [v.strip() for v in input_vars.split("\n") if v.strip()]
            
            aggregated = {}
            for var_name in var_list:
                if var_name in variables:
                    aggregated[var_name] = variables[var_name]
            
            result = {
                "success": True,
                "input_vars": var_list,
                "aggregated": aggregated
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        variables[output_var] = aggregated
        state["node_results"][label] = result
        
        return state
    
    @staticmethod
    async def _execute_document_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行文档提取节点"""
        document_var = node_data.get("document_var", "")
        extract_rules = node_data.get("extract_rules", "")
        output_var = node_data.get("output_var", "extracted_content")
        label = node_data.get("label", "document_extractor")
        
        variables = state.get("variables", {})
        
        try:
            document = variables.get(document_var, "")
            
            extracted = {
                "document_var": document_var,
                "extract_rules": extract_rules,
                "document": document,
                "extracted_content": f"Extracted content from document"
            }
            
            result = {
                "success": True,
                "extracted": extracted
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        variables[output_var] = extracted
        state["node_results"][label] = result
        
        return state
    
    @staticmethod
    async def _execute_variable_assigner_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行变量赋值节点"""
        var_name = node_data.get("var_name", "")
        var_value = node_data.get("var_value", "")
        output_var = node_data.get("output_var", "assigned_var")
        label = node_data.get("label", "variable_assigner")
        
        variables = state.get("variables", {})
        
        try:
            rendered_value = LangGraphExecutor._render_template(var_value, variables)
            variables[var_name] = rendered_value
            
            result = {
                "success": True,
                "var_name": var_name,
                "var_value": rendered_value
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        state["node_results"][label] = result
        
        return state
    
    @staticmethod
    async def _execute_parameter_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行参数提取节点"""
        input_text = node_data.get("input_text", "")
        parameters = node_data.get("parameters", "")
        output_var = node_data.get("output_var", "extracted_params")
        label = node_data.get("label", "parameter_extractor")
        
        variables = state.get("variables", {})
        
        try:
            input_content = variables.get(input_text, "")
            param_list = [p.strip() for p in parameters.split("\n") if p.strip()]
            
            extracted_params = {}
            for param_name in param_list:
                extracted_params[param_name] = f"Extracted {param_name}"
            
            result = {
                "success": True,
                "input_text": input_content,
                "parameters": param_list,
                "extracted": extracted_params
            }
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        variables[output_var] = extracted_params
        state["node_results"][label] = result
        
        return state
