"""
LangGraph 执行器 - 使用真正的 LangGraph 执行智能体结构图
"""
import asyncio
import json
import threading
import time
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
            print(f"[1/6] 读取流程图数据...")
            print(f"[DEBUG] graph_definition 类型: {type(agent.graph_definition)}")
            if isinstance(agent.graph_definition, str):
                print(f"[DEBUG] graph_definition 长度: {len(agent.graph_definition)}")
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
                print(f"2. 使用 LangGraph 执行结构图")
                print(f"[DEBUG] 节点数量: {len(flow_data.get('nodes', []))}, 边数量: {len(flow_data.get('edges', []))}")
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
            print(f"3. 进入 _execute_with_langgraph")
            # 🔧 加载记忆
            print(f"[DEBUG] 开始加载长期记忆...")
            logger.info("[加载长期记忆]")
            import asyncio
            
            # 将记忆转换为可用的变量格式
            memory_list = []
            recent_memories = []
            important_memories = []
            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])
            print(f"4. 准备执行流程，节点数: {len(nodes)}, 边数: {len(edges)}")
            print(f"[DEBUG] LANGGRAPH_AVAILABLE: {LANGGRAPH_AVAILABLE}")
            
            if not nodes:
                print(f"[DEBUG] 结构图没有节点，回退到简单执行")
                return await LangGraphExecutor._execute_simple(agent, input_data)
            
            # 如果 LangGraph 不可用，回退到内置执行器
            if not LANGGRAPH_AVAILABLE:
                print(f"[DEBUG] LangGraph 不可用，使用内置执行器")
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
            print(f"5. 开始构建 LangGraph")
            logger.info("[构建 LangGraph]")
            
            # 创建状态图
            print(f"[DEBUG] 创建 StateGraph...")
            workflow = StateGraph(AgentState)
            print(f"[DEBUG] StateGraph 创建完成")
            
            # 构建节点映射
            node_map = {node.get("id"): node for node in nodes}
            
            # 找到开始节点
            print(f"[DEBUG] 查找开始节点...")
            start_node = LangGraphExecutor._find_start_node(nodes)
            start_node_id = start_node.get("id", "start") if start_node else "start"
            print(f"[DEBUG] 开始节点: {start_node_id}")
            logger.info(f"开始节点: {start_node_id}")
            
            # 创建节点执行器
            print(f"[DEBUG] 开始创建节点执行器，节点数: {len(nodes)}")
            for node in nodes:
                node_id = node.get("id", "")
                node_type = node.get("type", "")
                if not node_id:
                    continue
                
                print(f"[DEBUG] 创建节点: {node_id} (类型: {node_type})")
                logger.info(f"创建节点: {node_id} (类型: {node_type})")
                
                # 创建节点处理函数 - 使用同步函数
                def node_executor(state: AgentState):
                    node_id = node.get("id", "")
                    print(f"[DEBUG] 开始执行节点: {node_id}")
                    logger.info(f"[执行节点] {node_id}")
                    # 使用 asyncio.run 执行异步函数
                    import asyncio
                    result = asyncio.run(LangGraphExecutor._execute_node_with_logging(
                        node,
                        state,
                        sse_yield_func=sse_yield_func
                    ))
                    print(f"[DEBUG] 节点完成: {node_id}, 结果类型: {type(result)}")
                    logger.info(f"[节点完成] {node_id}")
                    return result
                
                # 添加节点到工作流 - 使用函数作为节点
                print(f"[DEBUG] 添加节点到工作流: {node_id}")
                workflow.add_node(node_id, node_executor)
                print(f"[DEBUG] 节点 {node_id} 添加成功")
            
            # 添加边
            print(f"6. 添加边连接")
            print(f"[DEBUG] 边列表长度: {len(edges)}")
            print(f"[DEBUG] 所有边: {edges}")
            edge_map = {}
            for edge in edges:
                source = edge.get("source", "")
                target = edge.get("target", "")
                print(f"[DEBUG] 处理边: source={source}, target={target}")
                if source and target:
                    edge_map[source] = target
                    print(f"[DEBUG] 添加边: {source} -> {target}")
            
            # 设置入口点
            print(f"[DEBUG] 设置入口点...")
            if start_node_id in node_map:
                workflow.add_edge(START, start_node_id)
                print(f"[DEBUG] 设置入口点: {START} -> {start_node_id}")
            
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
            print(f"[DEBUG] 查找结束节点...")
            for node in nodes:
                if node.get("type") == "end":
                    node_id = node.get("id", "")
                    if node_id:
                        print(f"[DEBUG] 连接结束节点 {node_id} -> {END}")
                        logger.info(f"连接结束节点 {node_id} -> {END}")
                        workflow.add_edge(node_id, END)
            
            # 编译图，不带 checkpoint（简化测试）
            print(f"7. 编译 LangGraph")
            
            try:
                # 验证图结构
                print(f"[DEBUG] 验证图结构...")
                if start_node_id not in node_map:
                    print(f"[DEBUG] 开始节点 {start_node_id} 不在节点映射中")
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
                
                print(f"[DEBUG] 开始编译图...")
                graph = workflow.compile()  # 移除 checkpointer
                print(f"[DEBUG] LangGraph 编译完成")
                print(f"[DEBUG] graph 类型: {type(graph)}")
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
            logger.info(f"初始状态: {json.dumps(initial_state, ensure_ascii=False, default=str)[:500]}...")
            
            # 配置参数 - 简化，不使用 configurable
            config = {}
            logger.info(f"配置: {json.dumps(config, ensure_ascii=False)}")
            
            # 执行图
            print(f"8. 开始执行图")
            try:
                print(f"[DEBUG] 准备调用 graph.ainvoke...")
                print(f"[DEBUG] 初始状态键: {list(initial_state.keys())}")
                logger.info("[开始调用 graph.ainvoke...]")
                start_time = time.time()
                logger.info(f"[执行中] 正在调用 graph.ainvoke，当前线程: {threading.current_thread().name}")
                print(f"[DEBUG] 开始 await graph.ainvoke...")
                final_state = await graph.ainvoke(initial_state, config,debug=True)
                print(f"[DEBUG] graph.ainvoke 返回")
                elapsed = time.time() - start_time
                logger.info(f"[LangGraph 执行完成] 耗时: {elapsed:.2f}秒")
                logger.info(f"最终状态: {json.dumps(final_state, ensure_ascii=False, default=str)[:500]}...")
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
        model_id = node_data.get("model_id") or node_data.get("modelId")
        model_name = node_data.get("model", "gpt-3.5-turbo")
        node_label = node_data.get("label", "")
        skill_ids = node_data.get("skill_ids", []) or node_data.get("skillIds", [])
        
        import logging
        logger = logging.getLogger(__name__)
        
        # 加载关联的技能和解析绑定的工具
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
                        # 解析技能绑定的工具
                        bound_tools = SkillService.parse_bound_tools(skill.implementation)
                        if bound_tools:
                            for tool in bound_tools:
                                bound_tools_set.add(tool)
            except Exception as e:
                logger.exception(f"获取技能信息失败: {e}")
        
        # 如果有关联技能，将技能信息添加到提示词中
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
        
        # 获取所有绑定工具的函数调用schema
        tools = []
        functions = []
        if bound_tools_set:
            try:
                from base.plugins.agent.tools.registry import ToolRegistry
                all_tools_info = ToolRegistry.get_all_tools_info()
                # 只获取技能绑定的工具
                for tool_name in bound_tools_set:
                    if tool_name in all_tools_info:
                        tools.append(all_tools_info[tool_name])
                        functions.append(all_tools_info[tool_name])
                logger.info(f"获取到 {len(tools)} 个可用工具: {list(bound_tools_set)}")
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
                        
                        # 准备调用参数
                        chat_kwargs = {
                            "model": actual_model_for_call,
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }
                        
                        # 如果有工具，添加函数调用参数
                        if functions:
                            chat_kwargs["functions"] = functions
                            chat_kwargs["function_call"] = "auto"  # 允许模型自动选择是否调用工具
                        
                        response = await service.chat(**chat_kwargs)
                        
                        # 处理响应
                        if isinstance(response, dict) and response.get("choices"):
                            message = response["choices"][0].get("message", {})
                            
                            # 检查是否有函数调用
                            if message.get("function_call"):
                                function_call = message.get("function_call")
                                function_name = function_call.get("name")
                                function_args = function_call.get("arguments", {})
                                
                                logger.info(f"大模型请求调用工具: {function_name}, 参数: {function_args}")
                                
                                # 执行工具调用
                                try:
                                    tool_class = ToolRegistry.get_tool(function_name)
                                    if tool_class:
                                        tool_result = await tool_class.execute(**function_args)
                                        logger.info(f"工具执行成功: {function_name}, 结果: {tool_result}")
                                        
                                        # 将工具调用结果添加到消息中
                                        messages.append(message)
                                        messages.append({
                                            "role": "function",
                                            "name": function_name,
                                            "content": str(tool_result)
                                        })
                                        
                                        # 再次调用大模型获取最终响应
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
            logger.warning(f"使用模拟响应")
            llm_response = await LangGraphExecutor._generate_mock_response(input_text, prompt, node_label)
        
        # 尝试解析 LLM 响应中的 JSON
        parsed_response = None
        if llm_response:
            import json
            try:
                # 尝试找到 JSON 部分（支持在文本中嵌入 JSON）
                json_start = llm_response.find("{")
                json_end = llm_response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = llm_response[json_start:json_end]
                    parsed_response = json.loads(json_str)
                    logger.info(f"成功解析 LLM 输出 JSON: {parsed_response}")
            except Exception as e:
                logger.warning(f"解析 JSON 失败: {e}")
        
        output_variable = node_data.get("output_variable", "llm_output")
        if parsed_response:
            # 直接将解析后的对象存储为变量
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
        
        import logging
        logger = logging.getLogger(__name__)
        
        # 加载关联的技能和解析绑定的工具
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
                        # 解析技能绑定的工具
                        bound_tools = SkillService.parse_bound_tools(skill.implementation)
                        if bound_tools:
                            for tool in bound_tools:
                                bound_tools_set.add(tool)
            except Exception as e:
                logger.exception(f"获取技能信息失败: {e}")
        
        # 如果有关联技能，将技能信息添加到提示词中
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
        
        # 获取所有绑定工具的函数调用schema
        tools = []
        functions = []
        if bound_tools_set:
            try:
                from base.plugins.agent.tools.registry import ToolRegistry
                all_tools_info = ToolRegistry.get_all_tools_info()
                # 只获取技能绑定的工具
                for tool_name in bound_tools_set:
                    if tool_name in all_tools_info:
                        tools.append(all_tools_info[tool_name])
                        functions.append(all_tools_info[tool_name])
                logger.info(f"获取到 {len(tools)} 个可用工具: {list(bound_tools_set)}")
            except Exception as e:
                logger.exception(f"获取工具信息失败: {e}")
        
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
                from base.plugins.agent.tools.registry import ToolRegistry
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
                        
                        # 准备调用参数
                        chat_kwargs = {
                            "model": actual_model_for_call,
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 2000
                        }
                        
                        # 如果有工具，添加函数调用参数
                        if functions:
                            chat_kwargs["functions"] = functions
                            chat_kwargs["function_call"] = "auto"
                        
                        response = await service.chat(**chat_kwargs)
                        
                        # 处理响应
                        if isinstance(response, dict) and response.get("choices"):
                            message = response["choices"][0].get("message", {})
                            
                            # 检查是否有函数调用
                            if message.get("function_call"):
                                function_call = message.get("function_call")
                                function_name = function_call.get("name")
                                function_args = function_call.get("arguments", {})
                                
                                logger.info(f"大模型请求调用工具: {function_name}, 参数: {function_args}")
                                
                                # 执行工具调用
                                try:
                                    tool_class = ToolRegistry.get_tool(function_name)
                                    if tool_class:
                                        tool_result = await tool_class.execute(**function_args)
                                        logger.info(f"工具执行成功: {function_name}, 结果: {tool_result}")
                                        
                                        # 将工具调用结果添加到消息中
                                        messages.append(message)
                                        messages.append({
                                            "role": "function",
                                            "name": function_name,
                                            "content": str(tool_result)
                                        })
                                        
                                        # 再次调用大模型获取最终响应
                                        second_response = await service.chat(**chat_kwargs)
                                        if isinstance(second_response, dict) and second_response.get("choices"):
                                            full_response = second_response["choices"][0].get("message", {}).get("content", "")
                                        else:
                                            full_response = str(second_response)
                                    else:
                                        full_response = f"工具 {function_name} 未找到"
                                except Exception as tool_e:
                                    logger.exception(f"工具执行失败: {tool_e}")
                                    full_response = f"工具执行失败: {str(tool_e)}"
                            else:
                                full_response = message.get("content", "")
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
    async def _execute_tool_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行工具节点"""
        import logging
        logger = logging.getLogger(__name__)
        
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        tool_name = node_config.get("tool_name", "")
        
        if not tool_name:
            logger.error("工具节点缺少 tool_name")
            state["variables"]["tool_result"] = {
                "success": False,
                "message": "缺少工具名称"
            }
            return state
        
        # 从变量中获取参数，或者使用默认参数
        variables = state.get("variables", {})
        
        # 先尝试从 think 节点的输出中获取工具参数
        tool_params = {}
        
        # 遍历所有变量，查找可能的工具输出
        for var_name, var_value in variables.items():
            if isinstance(var_value, dict):
                # 检查是否是 LLM 输出，并且包含 tool_name 和 tool_args
                if "tool_args" in var_value:
                    tool_params = var_value["tool_args"]
                    logger.info(f"从变量 {var_name} 提取工具参数")
                    break
        
        # 如果没有找到，尝试从 variables 的根级别查找
        if not tool_params:
            # 提取所有参数
            tool_params = {k: v for k, v in variables.items() if k not in ["input", "output", "tool_result"]}
        
        # 也支持在工具节点中直接配置参数
        if node_config.get("params"):
            node_params = node_config.get("params", {})
            
            # 替换参数中的变量
            processed_params = {}
            variables = state.get("variables", {})
            
            for key, value in node_params.items():
                processed_value = value
                if isinstance(value, str):
                    # 替换 {{var}} 格式的变量
                    # 支持 {{key.nested_key}} 格式
                    for var_name, var_value in variables.items():
                        if isinstance(var_value, dict):
                            # 支持嵌套变量替换
                            for nested_key, nested_value in var_value.items():
                                placeholder = f"{{{{{var_name}.{nested_key}}}}}"
                                if placeholder in processed_value:
                                    processed_value = processed_value.replace(placeholder, str(nested_value))
                        # 支持简单变量替换
                        placeholder = f"{{{{{var_name}}}}}"
                        if placeholder in processed_value:
                            processed_value = processed_value.replace(placeholder, str(var_value))
                
                processed_params[key] = processed_value
            
            tool_params.update(processed_params)
        
        logger.info(f"执行工具: {tool_name}, 参数: {tool_params}")
        
        try:
            from base.plugins.agent.tools.registry import ToolRegistry
            
            tool_class = ToolRegistry.get_tool(tool_name)
            if not tool_class:
                raise ValueError(f"工具未注册: {tool_name}")
            
            result = await tool_class.execute(tool_params)
            
            logger.info(f"工具执行成功: {result}")
            # 存储结果到变量中，同时使用工具名作为变量名
            state["variables"]["tool_result"] = result
            state["variables"][tool_name] = result
            
        except Exception as e:
            logger.exception(f"工具执行失败: {e}")
            state["variables"]["tool_result"] = {
                "success": False,
                "message": str(e)
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
        
        # 如果有 params 参数，则批量设置多个变量
        params = node_config.get("params", {})
        if params and isinstance(params, dict):
            for key, value in params.items():
                processed_value = value
                if isinstance(processed_value, str):
                    # 替换变量引用
                    for var_key, var_value in variables.items():
                        # 支持简单变量替换 {{var}}
                        placeholder = f"{{{{{var_key}}}}}"
                        if placeholder in processed_value:
                            processed_value = processed_value.replace(placeholder, str(var_value))
                        
                        # 支持嵌套变量替换 {{var.key}}
                        if isinstance(var_value, dict):
                            for nested_key, nested_value in var_value.items():
                                nested_placeholder = f"{{{{{var_key}.{nested_key}}}}}"
                                if nested_placeholder in processed_value:
                                    processed_value = processed_value.replace(nested_placeholder, str(nested_value))
                
                state["variables"][key] = processed_value
        
        # 如果指定了单个变量名，也设置单个变量
        if variable_name:
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
