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
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

# 本地导入
from base.plugins.agent.models.agent import Agent
from base.plugins.agent.utils.safe_eval import safe_eval
from base.plugins.agent.services.memory_service import MemoryService


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
    """
    LangGraph 执行器
    使用真正的 LangGraph 执行智能体结构图
    """
    
    # 内存缓存，避免重复创建
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
        print(f"=== LangGraphExecutor.execute_agent 开始 ===")
        print(f"agent_id: {agent.id}, name: {agent.name}")
        print(f"input_data: {input_data}")
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info(f"[开始执行智能体] agent_id={agent.id}, name={agent.name}")
        logger.info(f"输入参数: {input_data}")
        logger.info("=" * 80)
        
        try:
            # 检查是否有结构图配置
            print(f"1. 读取流程图数据")
            logger.info("[1/6] 读取流程图数据...")
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
                logger.info("[2/6] 使用 LangGraph 执行结构图")
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
            print(f"=== 异常: {e} ===")
            import traceback
            print(traceback.format_exc())
            logger.exception(f"执行智能体失败: {str(e)}")
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
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 🔧 加载记忆
            logger.info("[加载长期记忆]")
            recent_memories = await MemoryService.get_recent_memories(agent.id, limit=10, customer_id=customer_id, user_id=user_id)
            important_memories = await MemoryService.get_important_memories(agent.id, limit=5, customer_id=customer_id, user_id=user_id)
            
            # 将记忆转换为可用的变量格式
            memory_list = []
            for m in recent_memories:
                memory_list.append({
                    "content": m.content,
                    "type": m.type,
                    "importance": m.importance,
                    "recall_count": m.recall_count
                })
            
            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])
            logger.info(f"节点数: {len(nodes)}, 边数: {len(edges)}")
            logger.info(f"节点ID列表: {[n.get('id') for n in nodes]}")
            
            if not nodes:
                logger.warning("结构图没有节点")
                return await LangGraphExecutor._execute_simple(agent, input_data)
            
            # 如果 LangGraph 不可用，回退到内置执行器
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
            
            # ===== 使用真正的 LangGraph =====
            logger.info("[构建 LangGraph]")
            
            # 创建状态图
            workflow = StateGraph(AgentState)
            
            # 构建节点映射
            node_map = {node.get("id"): node for node in nodes}
            
            # 找到开始节点
            start_node = LangGraphExecutor._find_start_node(nodes)
            start_node_id = start_node.get("id", "start") if start_node else "start"
            logger.info(f"开始节点: {start_node_id}")
            
            # 创建节点执行器
            for node in nodes:
                node_id = node.get("id", "")
                node_type = node.get("type", "")
                if not node_id:
                    continue
                
                logger.info(f"创建节点: {node_id} (类型: {node_type})")
                
                # 创建节点处理函数
                def create_node_executor(current_node):
                    async def node_executor(state: AgentState):
                        return await LangGraphExecutor._execute_node_with_logging(
                            current_node,
                            state,
                            sse_yield_func=sse_yield_func
                        )
                    return node_executor
                
                # 添加节点到工作流
                workflow.add_node(node_id, create_node_executor(node))
            
            # 添加边
            logger.info("[添加边连接]")
            edge_map = {}
            for edge in edges:
                source = edge.get("source", "")
                target = edge.get("target", "")
                if source and target:
                    edge_map[source] = target
                    logger.info(f"添加边: {source} -> {target}")
            
            # 设置入口点
            if start_node_id in node_map:
                workflow.add_edge(START, start_node_id)
                logger.info(f"设置入口点: {START} -> {start_node_id}")
            
            # 连接边
            condition_edges = {}
            for edge in edges:
                source = edge.get("source", "")
                target = edge.get("target", "")
                if source and target:
                    source_node = node_map.get(source)
                    if source_node and source_node.get("type") == "condition":
                        # 条件节点，收集条件分支
                        if source not in condition_edges:
                            condition_edges[source] = []
                        condition_edges[source].append(target)
                    else:
                        # 普通节点，直接连接
                        workflow.add_edge(source, target)
            
            # 处理条件边
            for condition_node_id, targets in condition_edges.items():
                # 创建条件路由函数
                def create_condition_router(node_id, target_list):
                    async def condition_router(state: AgentState):
                        variables = state.get("variables", {})
                        condition_result = variables.get("condition_result", {}).get("result", False)
                        logger.info(f"条件路由节点 {node_id} 结果: {condition_result}")
                        # 根据结果选择路由
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
            
            # 找到结束节点，连接到 END
            for node in nodes:
                if node.get("type") == "end":
                    node_id = node.get("id", "")
                    if node_id:
                        logger.info(f"连接结束节点 {node_id} -> {END}")
                        workflow.add_edge(node_id, END)
            
            # 编译图，带 checkpoint
            logger.info("[编译 LangGraph]")
            memory = MemorySaver()
            graph = workflow.compile(checkpointer=memory)
            
            # 初始化状态 - 不要在状态中放不可序列化的对象
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
            
            # ===== 使用 graph.ainvoke 执行 =====
            logger.info("[使用 LangGraph 执行]")
            
            # 配置参数
            config = {
                "configurable": {
                    "thread_id": str(agent.id) + "_" + datetime.now().isoformat()
                }
            }
            
            # 执行图
            final_state = await graph.ainvoke(initial_state, config)
            
            logger.info("[LangGraph 执行完成]")
            
            # 保存结果到长期记忆
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
        
        保持和原内置执行器一样的逻辑
        """
        import logging
        logger = logging.getLogger(__name__)
        
        nodes = flow_data.get("nodes", [])
        edges = flow_data.get("edges", [])
        
        # 构建节点映射
        node_map = {node.get("id"): node for node in nodes}
        
        # 找到开始节点
        start_node = LangGraphExecutor._find_start_node(nodes)
        if not start_node:
            logger.error("找不到开始节点")
            return {
                "success": False,
                "message": "找不到开始节点"
            }
        
        # 初始化状态
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
        
        # 执行图
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
            
            # 记录执行轨迹
            state["execution_trace"].append({
                "node_id": current_node_id,
                "node_type": node_type,
                "label": node_data.get("label", node_type),
                "timestamp": datetime.now().isoformat()
            })
            
            # 推送 SSE 事件
            if sse_yield_func:
                try:
                    node_label = node_data.get("label", node_type)
                    async for _ in sse_yield_func({
                        'type': 'node_start',
                        'node_id': current_node_id,
                        'node_type': node_type,
                        'node_label': node_label,
                        'step': step_count
                    }):
                        pass
                except Exception as e:
                    logger.warning(f"推送 SSE 失败: {e}")
            
            # 执行节点
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
            
            # 找到下一个节点
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
        
        # 保存结果到记忆
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
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"执行节点 [{node_id}]: {node_type}")
        
        state["current_node"] = node_label
        
        # 记录执行轨迹
        if "execution_trace" not in state:
            state["execution_trace"] = []
        step_count = len(state["execution_trace"]) + 1
        
        # 推送节点开始事件
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
        
        # 执行节点
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
                    await sse_yield_func({'type': 'thinking', 'label': node_label, 'message': f'正在调用大模型...'})
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
        
            # 记录执行轨迹
            state["execution_trace"].append({
                "node_id": node_id,
                "node_type": node_type,
                "label": node_label,
                "timestamp": datetime.now().isoformat()
            })
            
            # 推送节点完成事件
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
        import logging
        logger = logging.getLogger(__name__)
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
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            from base.plugins.agent.schemas.memory import MemoryCreate
            
            variables = state.get("variables", {}) if isinstance(state, dict) else {}
            
            # 使用智能体的默认记忆模式
            memory_mode = getattr(agent, "default_memory_mode", "public")
            
            # 1. 保存输入
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
                logger.info(f"[保存记忆] 输入内容已保存")
            
            # 2. 保存关键的结果变量
            key_variables = ["wbs_result", "task_plan", "task_decomposition", "thinking_result",
                             "final_output", "output", "structured_output"]
            
            for var_name in key_variables:
                if var_name in variables:
                    value = variables[var_name]
                    
                    content_str = ""
                    if isinstance(value, dict):
                        import json
                        content_str = json.dumps(value, ensure_ascii=False)
                    elif isinstance(value, list):
                        import json
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
                            logger.info(f"[保存记忆] {var_name} 已保存")
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
        # 直接从变量中获取 agent 信息，不需要完整对象
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
        model_id = node_data.get("model_id")
        model_name = node_data.get("model", "gpt-3.5-turbo")
        node_label = node_data.get("label", "")
        
        import logging
        logger = logging.getLogger(__name__)
        
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
                        # 清理端点 URL，移除错误的路径
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
                        response = await service.chat(
                            model=actual_model_for_call,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=1000
                        )
                        
                        if isinstance(response, dict) and response.get("choices"):
                            llm_response = response["choices"][0].get("message", {}).get("content", "")
                        else:
                            llm_response = str(response)
        except Exception as e:
            logger.exception(f"调用大模型失败: {e}")
        
        if not llm_response:
            logger.warning(f"使用模拟响应")
            llm_response = await LangGraphExecutor._generate_mock_response(input_text, prompt, node_label)
        
        output_variable = node_data.get("output_variable", "llm_output")
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
        model_id = node_data.get("model_id")
        model_name = node_data.get("model", "gpt-3.5-turbo")
        node_label = node_data.get("label", "")
        
        import logging
        logger = logging.getLogger(__name__)
        
        variables = state.get("variables", {})
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
        
        input_text = variables.get("input", {}).get("text", "")
        system_prompt = node_data.get("system_prompt", "")
        
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
        
        full_response = ""
        try:
            if target_model and sse_yield_func:
                async def stream_callback_wrapper(content):
                    logger.info(f"[langgraph_executor] stream_callback_wrapper 收到 content: {content}")
                    nonlocal full_response
                    full_response += content
                    try:
                        logger.info(f"[langgraph_executor] 准备推送SSE: content={content}, full_response={full_response}")
                        await sse_yield_func({
                            'type': 'thinking_stream',
                            'label': node_label,
                            'content': content,
                            'full_content': full_response
                        })
                        logger.info(f"[langgraph_executor] SSE推送成功")
                    except Exception as e:
                        logger.warning(f"推送流式内容失败: {e}")
                
                from base.plugins.llm.services.chat_service import ChatService
                async for _ in ChatService.chat_stream(
                    model_id=target_model.id,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000,
                    stream_callback=stream_callback_wrapper
                ):
                    pass
            elif target_model:
                from base.plugins.llm.services.chat_service import ChatService
                from base.plugins.llm.models.provider import LLMProvider
                from base.plugins.llm.models.api_key import LLMApiKey
                provider = await LLMProvider.get_or_none(id=target_model.provider_id)
                if provider:
                    api_key = await LLMApiKey.filter(model_id=target_model.id).first()
                    if api_key:
                        # 清理端点 URL，移除错误的路径
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
                        response = await service.chat(
                            model=actual_model_for_call,
                            messages=messages,
                            temperature=0.7,
                            max_tokens=2000
                        )
                        
                        if isinstance(response, dict) and response.get("choices"):
                            full_response = response["choices"][0].get("message", {}).get("content", "")
                        else:
                            full_response = str(response)
                        
                        # 推送完整内容
                        if sse_yield_func and full_response:
                            try:
                                await sse_yield_func({
                                    'type': 'thinking_stream',
                                    'label': node_label,
                                    'content': full_response,
                                    'full_content': full_response
                                })
                            except Exception as e:
                                logger.warning(f"推送流式内容失败: {e}")
        except Exception as e:
            logger.exception(f"流式调用失败: {e}")
        
        if not full_response:
            full_response = await LangGraphExecutor._generate_mock_response(input_text, prompt, node_label)
            if sse_yield_func and full_response:
                try:
                    await sse_yield_func({
                        'type': 'thinking_stream',
                        'label': node_label,
                        'content': full_response,
                        'full_content': full_response
                    })
                except Exception as e:
                    logger.warning(f"推送流式内容失败: {e}")
        
        output_variable = node_data.get("output_variable", "llm_output")
        state["variables"][output_variable] = {
            "prompt": prompt,
            "model": actual_model,
            "response": full_response
        }
        # 保持兼容性
        state["variables"]["llm_output"] = {
            "prompt": prompt,
            "model": actual_model,
            "response": full_response
        }
        
        return state
    
    @staticmethod
    async def _generate_mock_response(input_text: str, prompt: str = "", node_label: str = "") -> str:
        """生成模拟响应"""
        if node_label and "思考" in node_label:
            import json
            mock_response = {
                "original_task": input_text,
                "subtasks": [
                    {"id": "1", "name": "理解任务需求", "description": "深入理解需求", "tool": "none"}
                ],
                "reasoning": "根据任务分析"
            }
            return json.dumps(mock_response, ensure_ascii=False)
        
        return f"模拟响应: {input_text}"
    
    @staticmethod
    async def _execute_skill_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行技能节点"""
        skill_id = node_data.get("skill_id", "")
        parameters = node_data.get("parameters", {})
        
        variables = state.get("variables", {})
        for key, value in variables.items():
            for param_key, param_value in parameters.items():
                if isinstance(param_value, str):
                    parameters[param_key] = param_value.replace(f"{{{{{key}}}}}", str(value))
        
        state["variables"]["skill_output"] = {
            "skill_id": skill_id,
            "parameters": parameters,
            "result": "技能执行结果"
        }
        
        return state
    
    @staticmethod
    async def _execute_condition_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行条件节点"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        condition = node_config.get("condition", "True")
        variables = state.get("variables", {})
        
        safe_variables = {}
        safe_variables.update(variables)
        safe_variables.setdefault("should_continue", True)
        safe_variables.setdefault("loop_count", 0)
        safe_variables.setdefault("i", 0)
        
        processed_condition = condition
        processed_condition = processed_condition.replace("true", "True")
        processed_condition = processed_condition.replace("false", "False")
        
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            result = safe_eval(processed_condition, safe_variables)
            state["variables"]["condition_result"] = {
                "condition": condition,
                "result": bool(result)
            }
        except Exception as e:
            logger.warning(f"条件节点执行失败: {e}")
            state["variables"]["condition_result"] = {
                "condition": condition,
                "result": False
            }
        
        return state
    
    @staticmethod
    async def _execute_loop_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行循环节点"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        loop_variable = node_config.get("loop_variable", "i")
        
        variables = state.get("variables", {})
        current_value = variables.get(loop_variable, 0)
        variables[loop_variable] = current_value + 1
        
        state["variables"]["loop_result"] = {
            "variable": loop_variable,
            "current_value": variables[loop_variable]
        }
        
        return state
    
    @staticmethod
    async def _execute_iteration_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行迭代节点"""
        iteration_list = node_data.get("iteration_list", "")
        iteration_variable = node_data.get("iteration_variable", "item")
        
        try:
            if isinstance(iteration_list, str):
                items = json.loads(iteration_list)
            else:
                items = iteration_list
            
            if isinstance(items, list):
                state["variables"][iteration_variable] = items[0]
        except Exception as e:
            pass
        
        return state
    
    @staticmethod
    async def _execute_http_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行HTTP节点"""
        url = node_data.get("url", "")
        method = node_data.get("method", "GET")
        
        variables = state.get("variables", {})
        for key, value in variables.items():
            if isinstance(url, str):
                url = url.replace(f"{{{{{key}}}}}", str(value))
        
        state["variables"]["http_result"] = {
            "url": url,
            "method": method,
            "response": "HTTP 响应模拟"
        }
        
        return state
    
    @staticmethod
    async def _execute_code_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行代码节点"""
        code = node_data.get("code", "")
        
        state["variables"]["code_result"] = {
            "code": code,
            "output": "代码执行结果模拟"
        }
        
        return state
    
    @staticmethod
    async def _execute_template_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行模板节点"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        template = node_config.get("template", "")
        output_variable = node_config.get("output_variable", "template_output")
        
        variables = state.get("variables", {})
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        state["variables"][output_variable] = template
        return state
    
    @staticmethod
    async def _execute_variable_aggregator_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行变量聚合节点"""
        variables_to_aggregate = node_data.get("variables", [])
        output_variable = node_data.get("output_variable", "aggregated")
        
        variables = state.get("variables", {})
        aggregated = {}
        
        for var_name in variables_to_aggregate:
            if var_name in variables:
                aggregated[var_name] = variables[var_name]
        
        state["variables"][output_variable] = aggregated
        return state
    
    @staticmethod
    async def _execute_document_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行文档提取节点"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        output_variable = node_config.get("output_variable", "document_extract")
        
        state["variables"][output_variable] = {
            "content": "文档内容提取模拟"
        }
        
        return state
    
    @staticmethod
    async def _execute_variable_assigner_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行变量赋值节点"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        variable_name = node_config.get("var_name", node_config.get("variable_name", ""))
        variable_value = node_config.get("var_value", node_config.get("variable_value", ""))
        
        variables = state.get("variables", {})
        for key, value in variables.items():
            if isinstance(variable_value, str):
                variable_value = variable_value.replace(f"{{{{{key}}}}}", str(value))
        
        state["variables"][variable_name] = variable_value
        return state
    
    @staticmethod
    async def _execute_parameter_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行参数提取节点"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        parameters = node_config.get("parameters", [])
        
        extracted = {}
        if isinstance(parameters, list):
            for param in parameters:
                if isinstance(param, dict):
                    param_name = param.get("name", "")
                    extracted[param_name] = None
        
        state["variables"]["extracted_params"] = extracted
        return state
    
    @staticmethod
    async def _execute_json_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行JSON提取节点"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        input_variable = node_config.get("input_variable", "llm_output")
        output_variable = node_config.get("output_variable", "structured_output")
        
        input_data = state.get("variables", {}).get(input_variable, "")
        extracted_json = None
        
        if isinstance(input_data, dict) and "response" in input_data:
            text_to_parse = str(input_data["response"])
        elif isinstance(input_data, str):
            text_to_parse = input_data
        else:
            text_to_parse = str(input_data)
        
        try:
            import json
            extracted_json = json.loads(text_to_parse)
        except Exception:
            pass
        
        state["variables"][output_variable] = extracted_json
        return state
    
    @staticmethod
    async def _execute_default_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行默认节点"""
        return state
