"""
LangGraph 执行器 - 使用真正的 LangGraph 执行智能体结构图
"""
import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from operator import add
from typing import Dict, Any, List, Optional, TypedDict

from tortoise.exceptions import DoesNotExist

# LangGraph 和 LangChain 相关导入
try:
    from langchain_core.runnables import RunnableConfig
    from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
    from langgraph.graph import StateGraph, END, START
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

# 本地导入
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.utils.safe_eval import safe_eval
from base.plugins.agent.services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """智能体状态类型定义"""
    input: Dict[str, Any]
    output: Dict[str, Any]
    messages: List[Dict[str, Any]]
    variables: Dict[str, Any]
    node_results: Dict[str, Any]
    execution_trace: List[Dict[str, Any]]
    current_node: Optional[str]
    error: Optional[str]
    agent: Optional[Agent]


class LangGraphExecutor:
    """LangGraph 执行器 - 使用真正的 LangGraph 执行智能体结构图"""

    _memory_cache = {}

    @staticmethod
    async def execute_agent(
        agent: Agent,
        input_data: Dict[str, Any],
        customer_id: Optional[int] = None,
        user_id: Optional[int] = None,
        sse_yield_func=None
    ) -> Dict[str, Any]:
        """
        执行智能体
        
        Args:
            agent: 智能体对象
            input_data: 输入数据
            customer_id: 客户ID（用于私有记忆）
            user_id: 用户ID（用于私有记忆）
            sse_yield_func: SSE推送回调函数
            
        Returns:
            执行结果
        """
        logger.info(f"开始执行智能体: agent_id={agent.id}, name={agent.name}")
        logger.debug(f"输入参数: {input_data}")

        try:
            flow_data = None
            if agent.graph_definition:
                if isinstance(agent.graph_definition, str):
                    try:
                        flow_data = json.loads(agent.graph_definition)
                    except json.JSONDecodeError:
                        logger.error("结构图字符串解析失败")
                        flow_data = None
                else:
                    flow_data = agent.graph_definition

            if flow_data and isinstance(flow_data, dict) and flow_data.get("nodes"):
                logger.info("使用 LangGraph 执行结构图")
                return await LangGraphExecutor._execute_with_langgraph(
                    agent=agent,
                    flow_data=flow_data,
                    input_data=input_data,
                    customer_id=customer_id,
                    user_id=user_id,
                    sse_yield_func=sse_yield_func
                )
            else:
                logger.warning("没有配置流程图，使用简化执行方式")
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
        input_data: Dict[str, Any],
        customer_id: Optional[int] = None,
        user_id: Optional[int] = None,
        sse_yield_func=None
    ) -> Dict[str, Any]:
        """
        使用真正的 LangGraph 执行智能体结构图
        
        Args:
            agent: 智能体对象
            flow_data: 结构图数据
            input_data: 输入数据
            customer_id: 客户ID（用于私有记忆）
            user_id: 用户ID（用于私有记忆）
            sse_yield_func: SSE推送回调函数
            
        Returns:
            执行结果
        """
        try:
            memory_list = []
            recent_memories = []
            important_memories = []
            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])

            if not nodes:
                logger.warning("结构图没有节点，回退到简单执行")
                return await LangGraphExecutor._execute_simple(agent, input_data)

            if not LANGGRAPH_AVAILABLE:
                logger.warning("LangGraph 不可用，使用内置执行器")
                return await LangGraphExecutor._execute_with_builtin_fallback(
                    agent=agent,
                    flow_data=flow_data,
                    input_data=input_data,
                    customer_id=customer_id,
                    user_id=user_id,
                    recent_memories=recent_memories,
                    important_memories=important_memories,
                    memory_list=memory_list,
                    sse_yield_func=sse_yield_func
                )

            workflow = StateGraph(AgentState)
            node_map = {node.get("id"): node for node in nodes}
            start_node = LangGraphExecutor._find_start_node(nodes)
            start_node_id = start_node.get("id", "start") if start_node else "start"

            logger.info(f"开始构建 LangGraph，节点数: {len(nodes)}, 边数: {len(edges)}")
            logger.info(f"开始节点: {start_node_id}")

            for node in nodes:
                node_id = node.get("id", "")
                node_type = node.get("type", "")
                if not node_id:
                    continue

                logger.debug(f"创建节点: {node_id} (类型: {node_type})")

                def node_executor(state: AgentState):
                    result = asyncio.run(LangGraphExecutor._execute_node_with_logging(
                        node, state, sse_yield_func=sse_yield_func
                    ))
                    return result

                workflow.add_node(node_id, node_executor)

            edge_map = {}
            for edge in edges:
                source = edge.get("source", "")
                target = edge.get("target", "")
                if source and target:
                    edge_map[source] = target

            if start_node_id in node_map:
                workflow.add_edge(START, start_node_id)

            condition_edges = {}
            for edge in edges:
                source = edge.get("source", "")
                target = edge.get("target", "")
                if source and target:
                    source_node = node_map.get(source)
                    if source_node and source_node.get("type") == "condition":
                        if source not in condition_edges:
                            condition_edges[source] = []
                        condition_edges[source].append(target)
                    else:
                        workflow.add_edge(source, target)

            for condition_node_id, targets in condition_edges.items():
                def create_condition_router(node_id, target_list):
                    async def condition_router(state: AgentState):
                        variables = state.get("variables", {})
                        condition_result = variables.get("condition_result", {}).get("result", False)
                        logger.debug(f"条件路由节点 {node_id} 结果: {condition_result}")
                        if condition_result and len(target_list) > 0:
                            return target_list[0]
                        elif len(target_list) > 1:
                            return target_list[1]
                        elif len(target_list) > 0:
                            return target_list[0]
                        else:
                            return END
                    return condition_router

                if len(targets) > 0:
                    workflow.add_conditional_edges(
                        condition_node_id,
                        create_condition_router(condition_node_id, targets),
                        targets
                    )

            for node in nodes:
                if node.get("type") == "end":
                    node_id = node.get("id", "")
                    if node_id:
                        workflow.add_edge(node_id, END)

            try:
                if start_node_id not in node_map:
                    logger.warning(f"开始节点 {start_node_id} 不在节点映射中，回退到内置执行器")
                    return await LangGraphExecutor._execute_with_builtin_fallback(
                        agent=agent,
                        flow_data=flow_data,
                        input_data=input_data,
                        customer_id=customer_id,
                        user_id=user_id,
                        recent_memories=recent_memories,
                        important_memories=important_memories,
                        memory_list=memory_list,
                        sse_yield_func=sse_yield_func
                    )

                graph = workflow.compile()
                logger.info("LangGraph 编译完成")
            except Exception as e:
                logger.warning(f"LangGraph 编译失败: {e}, 回退到内置执行器")
                return await LangGraphExecutor._execute_with_builtin_fallback(
                    agent=agent,
                    flow_data=flow_data,
                    input_data=input_data,
                    customer_id=customer_id,
                    user_id=user_id,
                    recent_memories=recent_memories,
                    important_memories=important_memories,
                    memory_list=memory_list,
                    sse_yield_func=sse_yield_func
                )

            initial_state: AgentState = {
                "input": input_data,
                "output": {},
                "messages": [],
                "variables": {
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "recent_memories": memory_list,
                    "important_memories": [{"content": m.content, "importance": m.importance} for m in important_memories]
                },
                "node_results": {},
                "execution_trace": [],
                "current_node": None,
                "error": None
            }

            logger.info("使用 LangGraph 执行")
            logger.debug(f"初始状态: {json.dumps(initial_state, ensure_ascii=False, default=str)[:500]}...")

            config = {}
            logger.debug(f"配置: {json.dumps(config, ensure_ascii=False)}")

            try:
                logger.info("调用 graph.ainvoke...")
                start_time = time.time()
                final_state = await graph.ainvoke(initial_state, config, debug=True)
                elapsed = time.time() - start_time
                logger.info(f"LangGraph 执行完成，耗时: {elapsed:.2f}秒")
                logger.debug(f"最终状态: {json.dumps(final_state, ensure_ascii=False, default=str)[:500]}...")
            except asyncio.TimeoutError:
                logger.error("LangGraph 执行超时，回退到内置执行器")
                return await LangGraphExecutor._execute_with_builtin_fallback(
                    agent=agent,
                    flow_data=flow_data,
                    input_data=input_data,
                    customer_id=customer_id,
                    user_id=user_id,
                    recent_memories=recent_memories,
                    important_memories=important_memories,
                    memory_list=memory_list,
                    sse_yield_func=sse_yield_func
                )

            await LangGraphExecutor._save_result_to_memory(
                agent=agent,
                state=final_state,
                input_data=input_data,
                customer_id=customer_id,
                user_id=user_id
            )

            if final_state.get("error"):
                return {
                    "success": False,
                    "message": final_state["error"],
                    "input": input_data,
                    "output": final_state.get("output", {}),
                    "variables": final_state.get("variables", {}),
                    "trace": final_state.get("execution_trace", [])
                }

            return {
                "success": True,
                "message": "执行成功",
                "input": input_data,
                "output": final_state.get("output", {}),
                "variables": final_state.get("variables", {}),
                "trace": final_state.get("execution_trace", [])
            }

        except Exception as e:
            logger.exception(f"LangGraph 执行失败: {e}")
            import traceback
            return {
                "success": False,
                "message": str(e),
                "traceback": traceback.format_exc()
            }

    @staticmethod
    async def _execute_with_builtin_fallback(
        agent: Agent,
        flow_data: Dict[str, Any],
        input_data: Dict[str, Any],
        customer_id: Optional[int],
        user_id: Optional[int],
        recent_memories,
        important_memories,
        memory_list: List,
        sse_yield_func=None
    ) -> Dict[str, Any]:
        """
        降级的内置执行器（当 LangGraph 不可用时使用）
        """
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])

        node_map = {node.get("id"): node for node in nodes}

        start_node = LangGraphExecutor._find_start_node(nodes)
        if not start_node:
            logger.error("找不到开始节点")
            return {
                "success": False,
                "message": "找不到开始节点"
            }

        state = {
            "input": input_data,
            "output": {},
            "messages": [],
            "variables": {
                "recent_memories": memory_list,
                "important_memories": [{"content": m.content, "importance": m.importance} for m in important_memories]
            },
            "node_results": {},
            "execution_trace": [],
            "current_node": None,
            "error": None,
            "agent": agent
        }

        current_node_id = start_node.get("id")
        visited_nodes = set()
        max_steps = 100
        step_count = 0

        while current_node_id and step_count < max_steps:
            step_count += 1

            visited_nodes.add(current_node_id)

            current_node = node_map.get(current_node_id)
            if not current_node:
                logger.error(f"找不到节点: {current_node_id}")
                break

            node_type = current_node.get("type")
            node_data = current_node.get("data", {})

            state["execution_trace"].append({
                "node_id": current_node_id,
                "node_type": node_type,
                "label": node_data.get("label", node_type),
                "timestamp": datetime.now().isoformat()
            })

            if sse_yield_func:
                try:
                    node_label = node_data.get("label", node_type)
                    await sse_yield_func({
                        'type': 'node_start',
                        'node_id': current_node_id,
                        'node_type': node_type,
                        'node_label': node_label,
                        'step': step_count
                    })
                except Exception as e:
                    logger.warning(f"推送 SSE 失败: {e}")

            try:
                state = await LangGraphExecutor._execute_node_with_logging(
                    current_node,
                    state,
                    sse_yield_func=sse_yield_func
                )

                if node_type == "end":
                    break

            except Exception as e:
                logger.exception(f"节点 {current_node_id} 执行失败: {e}")
                state["error"] = str(e)
                state["output"]["error"] = str(e)
                break

            if node_type == "condition":
                condition_result = state.get("variables", {}).get("condition_result", {}).get("result", False)
                outgoing_edges = [e for e in edges if e.get("source") == current_node_id]

                if len(outgoing_edges) >= 2:
                    target_index = 0 if condition_result else 1
                    if target_index < len(outgoing_edges):
                        current_node_id = outgoing_edges[target_index].get("target")
                    else:
                        current_node_id = None
                elif outgoing_edges:
                    current_node_id = outgoing_edges[0].get("target")
                else:
                    current_node_id = None
            else:
                outgoing_edges = [e for e in edges if e.get("source") == current_node_id]
                if outgoing_edges:
                    current_node_id = outgoing_edges[0].get("target")
                else:
                    current_node_id = None

        await LangGraphExecutor._save_result_to_memory(
            agent=agent,
            state=state,
            input_data=input_data,
            customer_id=customer_id,
            user_id=user_id
        )

        if state.get("error"):
            return {
                "success": False,
                "message": state["error"],
                "input": input_data,
                "output": state.get("output", {}),
                "variables": state.get("variables", {}),
                "trace": state.get("execution_trace", [])
            }

        return {
            "success": True,
            "message": "执行成功",
            "input": input_data,
            "output": state.get("output", {}),
            "variables": state.get("variables", {}),
            "trace": state.get("execution_trace", [])
        }

    @staticmethod
    async def _execute_node_with_logging(current_node, state, sse_yield_func=None):
        """执行节点，带日志记录和 SSE 推送"""
        node_id = current_node.get("id", "")
        node_type = current_node.get("type")
        node_data = current_node.get("data", {})
        node_label = node_data.get("label", node_type)

        logger.info(f"执行节点 [{node_id}]: {node_type}")

        state["current_node"] = node_label

        if "execution_trace" not in state:
            state["execution_trace"] = []
        step_count = len(state["execution_trace"]) + 1

        if sse_yield_func:
            try:
                await sse_yield_func({
                    'type': 'node_start',
                    'node_id': node_id,
                    'node_type': node_type,
                    'node_label': node_label,
                    'step': step_count
                })
            except Exception as e:
                logger.warning(f"推送节点开始事件失败: {e}")

        try:
            if node_type == "start":
                if sse_yield_func:
                    await sse_yield_func({'type': 'info', 'label': '开始节点', 'message': '开始执行...'})
                state = await LangGraphExecutor._execute_start_node(node_data, state)
            elif node_type == "end":
                if sse_yield_func:
                    await sse_yield_func({'type': 'info', 'label': '结束节点', 'message': '执行结束'})
                state = await LangGraphExecutor._execute_end_node(node_data, state)
            elif node_type == "input":
                state = await LangGraphExecutor._execute_input_node(node_data, state)
            elif node_type == "output":
                state = await LangGraphExecutor._execute_output_node(node_data, state)
            elif node_type == "agent":
                state = await LangGraphExecutor._execute_agent_node(node_data, state)
            elif node_type == "llm":
                node_data = current_node.get("data", {})
                is_streaming = node_data.get("stream", False)
                if sse_yield_func:
                    await sse_yield_func({'type': 'thinking', 'label': node_label, 'message': '正在调用大模型...'})
                if is_streaming and sse_yield_func:
                    state = await LangGraphExecutor._execute_llm_node_streaming(
                        current_node,
                        state,
                        sse_yield_func=sse_yield_func
                    )
                else:
                    state = await LangGraphExecutor._execute_llm_node(current_node, state)
            elif node_type == "skill":
                if sse_yield_func:
                    await sse_yield_func({'type': 'action', 'label': node_label, 'message': f'执行技能: {node_data.get("skill_id", "unknown")}'})
                state = await LangGraphExecutor._execute_skill_node(node_data, state)
            elif node_type == "tool":
                if sse_yield_func:
                    await sse_yield_func({'type': 'action', 'label': node_label, 'message': f'执行工具: {node_data.get("tool_name", "unknown")}'})
                state = await LangGraphExecutor._execute_tool_node(node_data, state)
            elif node_type == "condition":
                if sse_yield_func:
                    await sse_yield_func({'type': 'thinking', 'label': node_label, 'message': '条件判断中...'})
                state = await LangGraphExecutor._execute_condition_node(node_data, state)
                if sse_yield_func:
                    condition_result = state.get("variables", {}).get("condition_result", {}).get("result", False)
                    await sse_yield_func({'type': 'observation', 'label': '条件判断结果', 'content': f'结果: {condition_result}'})
            elif node_type == "loop":
                state = await LangGraphExecutor._execute_loop_node(node_data, state)
            elif node_type == "iteration":
                state = await LangGraphExecutor._execute_iteration_node(node_data, state)
            elif node_type == "http":
                if sse_yield_func:
                    await sse_yield_func({'type': 'action', 'label': node_label, 'message': '发送HTTP请求'})
                state = await LangGraphExecutor._execute_http_node(node_data, state)
            elif node_type == "code":
                state = await LangGraphExecutor._execute_code_node(node_data, state)
            elif node_type == "template":
                state = await LangGraphExecutor._execute_template_node(node_data, state)
            elif node_type == "variable_aggregator":
                state = await LangGraphExecutor._execute_variable_aggregator_node(node_data, state)
            elif node_type == "document_extractor":
                state = await LangGraphExecutor._execute_document_extractor_node(node_data, state)
            elif node_type == "variable_assigner":
                state = await LangGraphExecutor._execute_variable_assigner_node(node_data, state)
            elif node_type == "parameter_extractor":
                state = await LangGraphExecutor._execute_parameter_extractor_node(node_data, state)
            elif node_type == "json_extractor":
                state = await LangGraphExecutor._execute_json_extractor_node(node_data, state)
            else:
                state = await LangGraphExecutor._execute_default_node(node_data, state)

            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": node_type,
                "label": node_label,
                "timestamp": datetime.now().isoformat()
            })

            if sse_yield_func:
                try:
                    await sse_yield_func({
                        'type': 'node_complete',
                        'node_id': node_id,
                        'node_type': node_type,
                        'node_label': node_label
                    })
                except Exception as e:
                    logger.warning(f"推送节点完成事件失败: {e}")

        except Exception as e:
            logger.exception(f"节点执行失败: {e}")
            state["error"] = str(e)
            if sse_yield_func:
                await sse_yield_func({'type': 'error', 'node_id': node_id, 'message': str(e)})

        return state

    @staticmethod
    async def _execute_simple(agent: Agent, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """简化的执行方式"""
        logger.info("使用简化执行方式")

        try:
            input_text = input_data.get("text", "")

            return {
                "success": True,
                "message": "执行成功",
                "input": input_data,
                "output": {
                    "text": f"已处理: {input_text}"
                }
            }

        except Exception as e:
            logger.exception(f"简化执行失败: {e}")
            return {
                "success": False,
                "message": str(e)
            }

    @staticmethod
    def _find_start_node(nodes: List[Dict]) -> Optional[Dict]:
        """找到开始节点"""
        for node in nodes:
            if node.get("type") == "start":
                return node

        if nodes:
            return nodes[0]
        return None

    @staticmethod
    async def _execute_start_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行开始节点"""
        state["variables"]["start_time"] = datetime.now().isoformat()
        return state

    @staticmethod
    async def _save_result_to_memory(agent, state, input_data, customer_id=None, user_id=None):
        """保存执行结果到长期记忆"""
        try:
            from base.plugins.agent.schemas.memory import MemoryCreate

            variables = state.get("variables", {}) if isinstance(state, dict) else {}

            memory_mode = getattr(agent, "default_memory_mode", "public")

            input_text = input_data.get("text", "")
            if input_text:
                input_memory_data = MemoryCreate(
                    agent_id=agent.id,
                    content=f"用户输入: {input_text}",
                    type="short_term",
                    importance=0.8,
                    memory_mode=memory_mode,
                    customer_id=customer_id if memory_mode == "private" else None,
                    user_id=user_id if memory_mode == "private" else None
                )
                await MemoryService.create_memory(input_memory_data)
                logger.info("保存记忆: 输入内容已保存")

            key_variables = ["wbs_result", "task_plan", "task_decomposition", "thinking_result",
                             "final_output", "output", "structured_output"]

            for var_name in key_variables:
                if var_name in variables:
                    value = variables[var_name]

                    content_str = ""
                    if isinstance(value, dict):
                        content_str = json.dumps(value, ensure_ascii=False)
                    elif isinstance(value, list):
                        content_str = json.dumps(value, ensure_ascii=False)
                    else:
                        content_str = str(value)

                    if content_str and len(content_str.strip()) > 0:
                        try:
                            importance = 0.9 if var_name in ["final_output", "wbs_result", "task_plan"] else 0.7
                            memory_data = MemoryCreate(
                                agent_id=agent.id,
                                content=f"{var_name}: {content_str}",
                                type="long_term",
                                importance=importance,
                                memory_mode=memory_mode,
                                customer_id=customer_id if memory_mode == "private" else None,
                                user_id=user_id if memory_mode == "private" else None
                            )
                            await MemoryService.create_memory(memory_data)
                            logger.info(f"保存记忆: {var_name} 已保存")
                        except Exception as e:
                            logger.warning(f"保存记忆失败: {e}")

        except Exception as e:
            logger.warning(f"保存记忆时出错: {e}")

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
            for key, value in variables.items():
                output_content = output_content.replace(f"{{{{{key}}}}}", str(value))
            state["output"][output_var] = output_content
        else:
            state["output"][output_var] = variables

        return state

    @staticmethod
    async def _execute_agent_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行智能体节点"""
        variables = state.get("variables", {})
        state["variables"]["agent_info"] = {
            "id": variables.get("agent_id"),
            "name": variables.get("agent_name"),
            "description": ""
        }
        return state

    @staticmethod
    async def _execute_llm_node(current_node: Dict, state: AgentState) -> AgentState:
        """执行LLM节点（非流式）"""
        node_id = current_node.get("id", "")
        node_data = current_node.get("data", {})
        prompt = node_data.get("prompt", "")
        model_id = node_data.get("model_id") or node_data.get("modelId")
        model_name = node_data.get("model", "gpt-3.5-turbo")
        node_label = node_data.get("label", "")
        skill_ids = node_data.get("skill_ids", []) or node_data.get("skillIds", [])

        skills_data = []
        bound_tools_set = set()
        if skill_ids:
            try:
                from base.plugins.agent.models.skill import Skill
                from base.plugins.agent.services.skill_service import SkillService
                for skill_id in skill_ids:
                    skill = await Skill.get_or_none(id=skill_id, status="active")
                    if skill:
                        skills_data.append({
                            "id": skill.id,
                            "name": skill.name,
                            "description": skill.description,
                            "implementation": skill.implementation
                        })
                        bound_tools = SkillService.parse_bound_tools(skill.implementation)
                        if bound_tools:
                            for tool in bound_tools:
                                bound_tools_set.add(tool)
            except Exception as e:
                logger.exception(f"获取技能信息失败: {e}")

        if skills_data:
            skill_context = "\n【可用技能】:\n"
            for skill in skills_data:
                skill_context += f"技能名称: {skill['name']}\n"
                skill_context += f"技能描述: {skill['description']}\n"
                skill_context += f"技能实现: {skill['implementation']}\n\n"

            if prompt:
                prompt = skill_context + "\n" + prompt
            else:
                prompt = skill_context

        tools = []
        functions = []
        if bound_tools_set:
            try:
                from base.plugins.agent.tools.registry import ToolRegistry
                all_tools_info = ToolRegistry.get_all_tools_info()
                for tool_name in bound_tools_set:
                    if tool_name in all_tools_info:
                        tools.append(all_tools_info[tool_name])
                        functions.append(all_tools_info[tool_name])
                logger.info(f"获取到 {len(tools)} 个可用工具")
            except Exception as e:
                logger.exception(f"获取工具信息失败: {e}")

        variables = state.get("variables", {})
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        input_text = variables.get("input", {}).get("text", "")
        system_prompt = node_data.get("system_prompt", "You are a helpful assistant.")

        messages = [{"role": "system", "content": system_prompt}]

        recent_memories = variables.get("recent_memories", [])
        important_memories = variables.get("important_memories", [])

        if recent_memories or important_memories:
            memory_context = "\n"
            if important_memories:
                memory_context += "【重要历史记忆】:\n"
                for idx, m in enumerate(important_memories):
                    memory_content = m.get("content", m) if isinstance(m, dict) else str(m)
                    memory_context += f"{idx+1}. {memory_content}\n"
                memory_context += "\n"
            if recent_memories:
                memory_context += "【最近记忆】:\n"
                for idx, m in enumerate(recent_memories):
                    memory_content = m.get("content", m) if isinstance(m, dict) else str(m)
                    memory_context += f"{idx+1}. {memory_content}\n"

            if memory_context.strip():
                messages.append({"role": "user", "content": f"历史记忆和上下文信息：\n{memory_context}\n"})

        if prompt and input_text:
            combined_content = prompt.replace("{{input}}", input_text) if "{{input}}" in prompt else f"{prompt}\n\n用户输入：{input_text}"
            messages.append({"role": "user", "content": combined_content})
        elif prompt:
            messages.append({"role": "user", "content": prompt})
        else:
            messages.append({"role": "user", "content": input_text})

        target_model = None
        actual_model = model_name

        try:
            from base.plugins.llm.models.model import LLMModel
            if model_id:
                target_model = await LLMModel.filter(id=model_id, status="active").first()
                if target_model:
                    actual_model = target_model.model_name
            if not target_model and model_name != "gpt-3.5-turbo":
                target_model = await LLMModel.filter(model_name=model_name, status="active").first()
                if target_model:
                    actual_model = target_model.model_name
            if not target_model:
                target_model = await LLMModel.filter(status="active").first()
                if target_model:
                    actual_model = target_model.model_name
        except Exception as e:
            logger.exception(f"获取模型信息失败: {e}")

        llm_response = ""
        try:
            if target_model:
                from base.plugins.llm.services.chat_service import ChatService
                from base.plugins.llm.models.provider import LLMProvider
                from base.plugins.llm.models.api_key import LLMApiKey
                from base.plugins.agent.tools.registry import ToolRegistry

                provider = await LLMProvider.get_or_none(id=target_model.provider_id)
                if provider:
                    api_key = await LLMApiKey.filter(model_id=target_model.id).first()
                    if api_key:
                        endpoint_url = target_model.endpoint_url or provider.api_endpoint
                        if endpoint_url:
                            endpoint_url = endpoint_url.rstrip('/')
                            if '/responses' in endpoint_url:
                                endpoint_url = endpoint_url.split('/responses')[0]
                            if endpoint_url.endswith('/chat/completions'):
                                endpoint_url = endpoint_url[:-len('/chat/completions')]

                        service = await ChatService.get_provider_service(
                            provider_name_en=provider.name_en,
                            api_key=api_key.api_key,
                            endpoint_url=endpoint_url,
                            api_secret=api_key.api_secret
                        )

                        actual_model_for_call = target_model.model_id if target_model.model_id else actual_model

                        chat_kwargs = {
                            "model": actual_model_for_call,
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }

                        if functions:
                            chat_kwargs["functions"] = functions
                            chat_kwargs["function_call"] = "auto"

                        response = await service.chat(**chat_kwargs)

                        if isinstance(response, dict) and response.get("choices"):
                            message = response["choices"][0].get("message", {})

                            if message.get("function_call"):
                                function_call = message.get("function_call")
                                function_name = function_call.get("name")
                                function_args = function_call.get("arguments", {})

                                logger.info(f"大模型请求调用工具: {function_name}")

                                try:
                                    tool_class = ToolRegistry.get_tool(function_name)
                                    if tool_class:
                                        tool_result = await tool_class.execute(**function_args)
                                        logger.info(f"工具执行成功: {function_name}")

                                        messages.append(message)
                                        messages.append({
                                            "role": "function",
                                            "name": function_name,
                                            "content": str(tool_result)
                                        })

                                        second_response = await service.chat(**chat_kwargs)
                                        if isinstance(second_response, dict) and second_response.get("choices"):
                                            llm_response = second_response["choices"][0].get("message", {}).get("content", "")
                                        else:
                                            llm_response = str(second_response)
                                    else:
                                        llm_response = f"工具 {function_name} 未找到"
                                except Exception as tool_e:
                                    logger.exception(f"工具执行失败: {tool_e}")
                                    llm_response = f"工具执行失败: {str(tool_e)}"
                            else:
                                llm_response = message.get("content", "")
                        else:
                            llm_response = str(response)
        except Exception as e:
            logger.exception(f"调用大模型失败: {e}")

        if not llm_response:
            logger.warning("使用模拟响应")
            llm_response = await LangGraphExecutor._generate_mock_response(input_text, prompt, node_label)

        parsed_response = None
        if llm_response:
            try:
                json_start = llm_response.find("{")
                json_end = llm_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                    parsed_response = json.loads(json_str)
                    logger.debug(f"成功解析 LLM 输出 JSON")
            except Exception as e:
                logger.warning(f"解析 JSON 失败: {e}")

        output_variable = node_data.get("output_variable", "llm_output")
        if parsed_response:
            state["variables"][output_variable] = parsed_response
        else:
            state["variables"][output_variable] = {
                "prompt": prompt,
                "model": actual_model,
                "response": llm_response
            }

        return state

    @staticmethod
    async def _execute_llm_node_streaming(
        current_node: Dict,
        state: AgentState,
        sse_yield_func=None
    ) -> AgentState:
        """执行LLM节点（流式）"""
        node_id = current_node.get("id", "")
        node_data = current_node.get("data", {})
        prompt = node_data.get("prompt", "")
        model_id = node_data.get("model_id") or node_data.get("modelId")
        model_name = node_data.get("model", "gpt-3.5-turbo")
        node_label = node_data.get("label", "")
        skill_ids = node_data.get("skill_ids", []) or node_data.get("skillIds", [])

        skills_data = []
        bound_tools_set = set()
        if skill_ids:
            try:
                from base.plugins.agent.models.skill import Skill
                from base.plugins.agent.services.skill_service import SkillService
                for skill_id in skill_ids:
                    skill = await Skill.get_or_none(id=skill_id, status="active")
                    if skill:
                        skills_data.append({
                            "id": skill.id,
                            "name": skill.name,
                            "description": skill.description,
                            "implementation": skill.implementation
                        })
                        bound_tools = SkillService.parse_bound_tools(skill.implementation)
                        if bound_tools:
                            for tool in bound_tools:
                                bound_tools_set.add(tool)
            except Exception as e:
                logger.exception(f"获取技能信息失败: {e}")

        if skills_data:
            skill_context = "\n【可用技能】:\n"
            for skill in skills_data:
                skill_context += f"技能名称: {skill['name']}\n"
                skill_context += f"技能描述: {skill['description']}\n"
                skill_context += f"技能实现: {skill['implementation']}\n\n"

            if prompt:
                prompt = skill_context + "\n" + prompt
            else:
                prompt = skill_context

        variables = state.get("variables", {})
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))

        input_text = variables.get("input", {}).get("text", "")
        system_prompt = node_data.get("system_prompt", "You are a helpful assistant.")

        messages = [{"role": "system", "content": system_prompt}]

        recent_memories = variables.get("recent_memories", [])
        important_memories = variables.get("important_memories", [])

        if recent_memories or important_memories:
            memory_context = "\n"
            if important_memories:
                memory_context += "【重要历史记忆】:\n"
                for idx, m in enumerate(important_memories):
                    memory_content = m.get("content", m) if isinstance(m, dict) else str(m)
                    memory_context += f"{idx+1}. {memory_content}\n"
                memory_context += "\n"
            if recent_memories:
                memory_context += "【最近记忆】:\n"
                for idx, m in enumerate(recent_memories):
                    memory_content = m.get("content", m) if isinstance(m, dict) else str(m)
                    memory_context += f"{idx+1}. {memory_content}\n"

            if memory_context.strip():
                messages.append({"role": "user", "content": f"历史记忆和上下文信息：\n{memory_context}\n"})

        if prompt and input_text:
            combined_content = prompt.replace("{{input}}", input_text) if "{{input}}" in prompt else f"{prompt}\n\n用户输入：{input_text}"
            messages.append({"role": "user", "content": combined_content})
        elif prompt:
            messages.append({"role": "user", "content": prompt})
        else:
            messages.append({"role": "user", "content": input_text})

        target_model = None
        actual_model = model_name

        try:
            from base.plugins.llm.models.model import LLMModel
            if model_id:
                target_model = await LLMModel.filter(id=model_id, status="active").first()
                if target_model:
                    actual_model = target_model.model_name
            if not target_model and model_name != "gpt-3.5-turbo":
                target_model = await LLMModel.filter(model_name=model_name, status="active").first()
                if target_model:
                    actual_model = target_model.model_name
            if not target_model:
                target_model = await LLMModel.filter(status="active").first()
                if target_model:
                    actual_model = target_model.model_name
        except Exception as e:
            logger.exception(f"获取模型信息失败: {e}")

        llm_response = ""
        try:
            if target_model:
                from base.plugins.llm.services.chat_service import ChatService
                from base.plugins.llm.models.provider import LLMProvider
                from base.plugins.llm.models.api_key import LLMApiKey

                provider = await LLMProvider.get_or_none(id=target_model.provider_id)
                if provider:
                    api_key = await LLMApiKey.filter(model_id=target_model.id).first()
                    if api_key:
                        endpoint_url = target_model.endpoint_url or provider.api_endpoint
                        if endpoint_url:
                            endpoint_url = endpoint_url.rstrip('/')
                            if '/responses' in endpoint_url:
                                endpoint_url = endpoint_url.split('/responses')[0]
                            if endpoint_url.endswith('/chat/completions'):
                                endpoint_url = endpoint_url[:-len('/chat/completions')]

                        service = await ChatService.get_provider_service(
                            provider_name_en=provider.name_en,
                            api_key=api_key.api_key,
                            endpoint_url=endpoint_url,
                            api_secret=api_key.api_secret
                        )

                        actual_model_for_call = target_model.model_id if target_model.model_id else actual_model

                        chat_kwargs = {
                            "model": actual_model_for_call,
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 1000,
                            "stream": True
                        }

                        full_response = ""
                        async for chunk in service.chat_stream(**chat_kwargs):
                            if isinstance(chunk, dict) and chunk.get("choices"):
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                full_response += content
                                if content and sse_yield_func:
                                    await sse_yield_func({
                                        'type': 'stream',
                                        'content': content,
                                        'node_id': node_id
                                    })
                        llm_response = full_response
        except Exception as e:
            logger.exception(f"调用大模型失败: {e}")

        if not llm_response:
            logger.warning("使用模拟响应")
            llm_response = await LangGraphExecutor._generate_mock_response(input_text, prompt, node_label)

        parsed_response = None
        if llm_response:
            try:
                json_start = llm_response.find("{")
                json_end = llm_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                    parsed_response = json.loads(json_str)
                    logger.debug(f"成功解析 LLM 输出 JSON")
            except Exception as e:
                logger.warning(f"解析 JSON 失败: {e}")

        output_variable = node_data.get("output_variable", "llm_output")
        if parsed_response:
            state["variables"][output_variable] = parsed_response
        else:
            state["variables"][output_variable] = {
                "prompt": prompt,
                "model": actual_model,
                "response": llm_response
            }

        return state

    @staticmethod
    async def _generate_mock_response(input_text: str, prompt: str, node_label: str) -> str:
        """生成模拟响应（当大模型不可用时）"""
        return f"模拟响应: {node_label} - 处理输入: {input_text[:50]}..."

    @staticmethod
    async def _execute_skill_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行技能节点"""
        skill_id = node_data.get("skill_id", "")
        variables = state.get("variables", {})

        try:
            from base.plugins.agent.models.skill import Skill
            from base.plugins.agent.services.skill_service import SkillService

            skill = await Skill.get_or_none(id=skill_id, status="active")
            if skill:
                result = await SkillService.execute_skill(skill, variables)
                state["variables"]["skill_result"] = result
            else:
                logger.error(f"技能不存在或未激活: {skill_id}")
                state["variables"]["skill_result"] = {"error": f"技能不存在或未激活: {skill_id}"}
        except Exception as e:
            logger.exception(f"执行技能失败: {e}")
            state["variables"]["skill_result"] = {"error": str(e)}

        return state

    @staticmethod
    async def _execute_tool_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行工具节点"""
        tool_name = node_data.get("tool_name", "")
        tool_params = node_data.get("tool_params", {})

        try:
            from base.plugins.agent.tools.registry import ToolRegistry

            variables = state.get("variables", {})
            params = {}
            for key, value in tool_params.items():
                if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                    var_name = value[2:-2]
                    params[key] = variables.get(var_name, value)
                else:
                    params[key] = value

            tool_class = ToolRegistry.get_tool(tool_name)
            if tool_class:
                result = await tool_class.execute(**params)
                state["variables"]["tool_result"] = result
            else:
                logger.error(f"工具不存在: {tool_name}")
                state["variables"]["tool_result"] = {"error": f"工具不存在: {tool_name}"}
        except Exception as e:
            logger.exception(f"执行工具失败: {e}")
            state["variables"]["tool_result"] = {"error": str(e)}

        return state

    @staticmethod
    async def _execute_condition_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行条件节点"""
        condition = node_data.get("condition", "")
        variables = state.get("variables", {})

        try:
            result = safe_eval(condition, variables)
            state["variables"]["condition_result"] = {
                "condition": condition,
                "result": bool(result)
            }
        except Exception as e:
            logger.exception(f"条件表达式执行失败: {e}")
            state["variables"]["condition_result"] = {
                "condition": condition,
                "result": False,
                "error": str(e)
            }

        return state

    @staticmethod
    async def _execute_loop_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行循环节点"""
        loop_count = node_data.get("loop_count", 3)
        loop_var = node_data.get("loop_var", "loop_index")

        state["variables"]["loop_iterations"] = []
        for i in range(loop_count):
            state["variables"][loop_var] = i
            state["variables"]["loop_iterations"].append(i)

        return state

    @staticmethod
    async def _execute_iteration_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行迭代节点"""
        iteration_var = node_data.get("iteration_var", "item")
        collection_var = node_data.get("collection_var", "items")

        collection = state.get("variables", {}).get(collection_var, [])
        if not isinstance(collection, list):
            collection = []

        state["variables"]["iteration_index"] = 0
        state["variables"]["iteration_count"] = len(collection)
        state["variables"]["iteration_total"] = len(collection)

        if collection:
            state["variables"][iteration_var] = collection[0]

        return state

    @staticmethod
    async def _execute_http_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行HTTP请求节点"""
        url = node_data.get("url", "")
        method = node_data.get("method", "GET")
        headers = node_data.get("headers", {})
        body = node_data.get("body", "")

        try:
            import aiohttp

            variables = state.get("variables", {})
            for key, value in variables.items():
                url = url.replace(f"{{{{{key}}}}}", str(value))
                if isinstance(body, str):
                    body = body.replace(f"{{{{{key}}}}}", str(value))
                if isinstance(headers, dict):
                    for h_key, h_value in headers.items():
                        if isinstance(h_value, str):
                            headers[h_key] = h_value.replace(f"{{{{{key}}}}}", str(value))

            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, headers=headers, data=body) as response:
                    response_data = await response.json()
                    state["variables"]["http_response"] = {
                        "status": response.status,
                        "data": response_data
                    }
        except Exception as e:
            logger.exception(f"HTTP请求失败: {e}")
            state["variables"]["http_response"] = {"error": str(e)}

        return state

    @staticmethod
    async def _execute_code_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行代码节点"""
        code = node_data.get("code", "")

        try:
            variables = state.get("variables", {})
            local_vars = variables.copy()
            exec(code, {}, local_vars)
            state["variables"].update(local_vars)
        except Exception as e:
            logger.exception(f"代码执行失败: {e}")
            state["variables"]["code_error"] = str(e)

        return state

    @staticmethod
    async def _execute_template_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行模板节点"""
        template = node_data.get("template", "")
        output_var = node_data.get("output_var", "template_output")

        variables = state.get("variables", {})
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

        state["variables"][output_var] = template
        return state

    @staticmethod
    async def _execute_variable_aggregator_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行变量聚合器节点"""
        input_vars = node_data.get("input_vars", [])
        output_var = node_data.get("output_var", "aggregated")

        aggregated = {}
        variables = state.get("variables", {})
        for var_name in input_vars:
            if var_name in variables:
                aggregated[var_name] = variables[var_name]

        state["variables"][output_var] = aggregated
        return state

    @staticmethod
    async def _execute_document_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行文档提取节点"""
        document_var = node_data.get("document_var", "document")
        extract_fields = node_data.get("extract_fields", [])

        document = state.get("variables", {}).get(document_var, "")
        extracted = {}

        for field in extract_fields:
            extracted[field] = document[:100]

        state["variables"]["extracted_data"] = extracted
        return state

    @staticmethod
    async def _execute_variable_assigner_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行变量赋值节点"""
        variable_name = node_data.get("variable_name", "")
        value = node_data.get("value", "")

        variables = state.get("variables", {})
        if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
            var_name = value[2:-2]
            value = variables.get(var_name, value)

        state["variables"][variable_name] = value
        return state

    @staticmethod
    async def _execute_parameter_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行参数提取节点"""
        source_var = node_data.get("source_var", "")
        parameter_name = node_data.get("parameter_name", "")

        source = state.get("variables", {}).get(source_var, "")
        if isinstance(source, dict):
            state["variables"][parameter_name] = source.get(parameter_name, "")
        else:
            state["variables"][parameter_name] = ""

        return state

    @staticmethod
    async def _execute_json_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行JSON提取节点"""
        source_var = node_data.get("source_var", "")
        json_path = node_data.get("json_path", "")
        output_var = node_data.get("output_var", "extracted_json")

        source = state.get("variables", {}).get(source_var, "")

        try:
            if isinstance(source, str):
                source = json.loads(source)

            if isinstance(source, dict):
                keys = json_path.split(".")
                result = source
                for key in keys:
                    if isinstance(result, dict) and key in result:
                        result = result[key]
                    else:
                        result = None
                        break
            else:
                result = None

            state["variables"][output_var] = result
        except Exception as e:
            logger.exception(f"JSON提取失败: {e}")
            state["variables"][output_var] = None

        return state

    @staticmethod
    async def _execute_default_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行默认节点"""
        logger.warning(f"未知节点类型，跳过执行")
        return state