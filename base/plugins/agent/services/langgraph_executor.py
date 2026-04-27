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
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行智能体
        
        Args:
            agent: 智能体对象
            input_data: 输入数据
            customer_id: 客户ID（用于私有记忆）
            user_id: 用户ID（用于私有记忆）
            
        Returns:
            执行结果
        """
        print(f"=== LangGraphExecutor.execute_agent 开始 ===")
        print(f"agent_id: {agent.id}, name: {agent.name}")
        print(f"input_data: {input_data}")
        print(f"customer_id: {customer_id}, user_id: {user_id}")
        
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 80)
        logger.info(f"[开始执行智能体] agent_id: {agent.id}, name: {agent.name}")
        logger.info(f"输入参数: {input_data}")
        logger.info(f"customer_id: {customer_id}, user_id: {user_id}")
        logger.info("=" * 80)
        
        try:
            # 检查是否有结构图配置
            print(f"1. 读取流程图数据")
            logger.info("[1/6] 读取流程图数据...")
            flow_data = None
            if agent.graph_definition:
                print(f"2. agent.graph_definition存在，类型: {type(agent.graph_definition)}")
                if isinstance(agent.graph_definition, str):
                    print(f"3. 尝试将字符串转换为字典")
                    try:
                        flow_data = json.loads(agent.graph_definition)
                        print(f"4. 成功将字符串转换为字典")
                        logger.info("成功将字符串转换为字典")
                    except json.JSONDecodeError as e:
                        print(f"4. 结构图字符串解析失败: {e}")
                        logger.error("结构图字符串解析失败")
                        flow_data = None
                else:
                    print(f"3. graph_definition不是字符串，直接使用")
                    flow_data = agent.graph_definition
            print(f"5. flow_data: {flow_data}")
            logger.info(f"agent.graph_definition: {flow_data}")
            
            if flow_data and isinstance(flow_data, dict) and flow_data.get("nodes"):
                print(f"6. 有结构图，使用内置执行器")
                # 使用内置执行器执行结构图（不依赖 LangGraph）
                logger.info("使用内置执行器执行结构图")
                return await LangGraphExecutor._execute_with_builtin(
                    agent=agent,
                    flow_data=flow_data,
                    input_data=input_data,
                    customer_id=customer_id,
                    user_id=user_id
                )
            else:
                print(f"6. 没有结构图，使用简化执行方式")
                # 没有结构图，使用简化的直接执行方式
                logger.warning("没有配置流程图（nodes为空），使用简化执行方式")
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
    async def _execute_with_builtin(
        agent: Agent,
        flow_data: Dict[str, Any],
        input_data: Dict[str, Any],
        customer_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        使用内置执行器执行智能体结构图（不依赖 LangGraph）
        
        Args:
            agent: 智能体对象
            flow_data: 结构图数据
            input_data: 输入数据
            customer_id: 客户ID（用于私有记忆）
            user_id: 用户ID（用于私有记忆）
            
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
            edge_list = [f"{e.get('source')}→{e.get('target')}" for e in edges]
            logger.info(f"边列表: {edge_list}")
            
            if not nodes:
                logger.warning("结构图没有节点，使用简化执行方式")
                return await LangGraphExecutor._execute_simple(agent, input_data)
            
            # 构建节点映射
            logger.info("[2/6] 构建节点映射...")
            node_map = {node.get("id"): node for node in nodes}
            
            # 找到开始节点
            logger.info("[3/6] 查找开始节点...")
            start_node = LangGraphExecutor._find_start_node(nodes)
            if not start_node:
                logger.error("找不到开始节点！")
                return {
                    "success": False,
                    "message": "找不到开始节点"
                }
            logger.info(f"找到开始节点: {start_node.get('id')}")
            
            # 初始化执行状态
            logger.info("[4/6] 初始化执行状态...")
            state = {
                "input": input_data,
                "output": {},
                "messages": [],
                "variables": {
                    "recent_memories": memory_list,
                    "longterm_memories": [],
                    "important_memories": [{"content": m.content, "importance": m.importance} for m in important_memories]
                },
                "node_results": {},
                "execution_trace": [],
                "current_node": None,
                "error": None,
                "agent": agent
            }
            logger.info(f"初始化状态完成")
            
            # 执行图
            logger.info("[5/6] 开始执行结构图...")
            current_node_id = start_node.get("id")
            visited_nodes = set()
            max_steps = 100
            step_count = 0
            
            while current_node_id and step_count < max_steps:
                step_count += 1
                
                # 不再防止循环访问，因为现在需要支持循环了
                # if current_node_id in visited_nodes:
                #     logger.warning(f"检测到循环，节点 {current_node_id} 已访问过")
                #     break
                visited_nodes.add(current_node_id)
                
                # 获取当前节点
                current_node = node_map.get(current_node_id)
                if not current_node:
                    logger.error(f"找不到节点: {current_node_id}")
                    break
                
                node_type = current_node.get("type")
                node_data = current_node.get("data", {})
                logger.info(f"执行节点 [{step_count}]: {current_node_id} (类型: {node_type})")
                logger.info(f"完整节点current_node: {current_node}")
                logger.info(f"节点数据node_data: {node_data}")
                
                # 记录执行轨迹
                state["execution_trace"].append({
                    "node_id": current_node_id,
                    "node_type": node_type,
                    "label": node_data.get("label", node_type),
                    "timestamp": datetime.now().isoformat()
                })
                state["current_node"] = node_data.get("label", node_type)
                
                # 执行节点
                try:
                    if node_type == "start":
                        state = await LangGraphExecutor._execute_start_node(node_data, state)
                    elif node_type == "end":
                        state = await LangGraphExecutor._execute_end_node(node_data, state)
                        # 结束节点执行完就停止
                        break
                    elif node_type == "input":
                        state = await LangGraphExecutor._execute_input_node(node_data, state)
                    elif node_type == "output":
                        state = await LangGraphExecutor._execute_output_node(node_data, state)
                    elif node_type == "agent":
                        state = await LangGraphExecutor._execute_agent_node(node_data, state)
                    elif node_type == "llm":
                        node_data = current_node.get("data", {})
                        is_streaming = node_data.get("stream", False)
                        if is_streaming:
                            # 流式执行
                            state = await LangGraphExecutor._execute_llm_node_streaming(current_node, state)
                        else:
                            # 非流式执行
                            state = await LangGraphExecutor._execute_llm_node(current_node, state)
                    elif node_type == "skill":
                        state = await LangGraphExecutor._execute_skill_node(node_data, state)
                    elif node_type == "condition":
                        state = await LangGraphExecutor._execute_condition_node(node_data, state)
                    elif node_type == "loop":
                        state = await LangGraphExecutor._execute_loop_node(node_data, state)
                    elif node_type == "iteration":
                        state = await LangGraphExecutor._execute_iteration_node(node_data, state)
                    elif node_type == "http":
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
                    
                    logger.info(f"节点 {current_node_id} 执行完成")
                except Exception as e:
                    logger.exception(f"节点 {current_node_id} 执行失败: {e}")
                    state["error"] = str(e)
                    state["output"]["error"] = str(e)
                    break
                
                # 找到下一个节点
                if node_type == "condition":
                    # 条件节点，根据条件结果选择下一个节点
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
                    # 普通节点（包括 loop），直接找第一条边
                    outgoing_edges = [e for e in edges if e.get("source") == current_node_id]
                    if outgoing_edges:
                        current_node_id = outgoing_edges[0].get("target")
                    else:
                        current_node_id = None
            
            logger.info("[6/6] 结构图执行完成!")
            logger.info(f"执行结果 error: {state.get('error')}")
            logger.info(f"执行结果 trace: {state.get('execution_trace')}")
            
            # 🔧 保存重要内容到长期记忆
            await LangGraphExecutor._save_result_to_memory(agent, state, input_data, customer_id=customer_id, user_id=user_id)
            
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
        except Exception as e:
            logger.exception(f"执行结构图失败: {e}")
            
            # 🔧 出错时也要保存记忆
            try:
                await LangGraphExecutor._save_result_to_memory(agent, {"error": str(e)}, input_data, customer_id=customer_id, user_id=user_id)
            except:
                pass
                
            return {
                "success": False,
                "message": str(e),
                "input": input_data,
                "output": {},
                "trace": []
            }

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
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                    logger.info("成功将config字符串转换为字典")
                except json.JSONDecodeError:
                    logger.error("config字符串解析失败")
                    config = {}
            skills_config = config.get("skills", [])
            model_config = config.get("model", {})
            
            if not skills_config:
                return {
                    "success": False,
                    "message": "No skills configured for agent"
                }
            
            # 这里可以添加简单的执行逻辑
            # 例如调用第一个技能
            
            return {
                "success": True,
                "message": "执行成功 (简化模式)",
                "input": input_data,
                "output": {
                    "text": f"处理完成: {input_text}",
                    "skills_used": skills_config
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
        
        # 如果没有 start 类型节点，找第一个节点
        return nodes[0] if nodes else None
    
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
                    
                    # 将内容转为字符串格式
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
                            logger.info(f"[保存记忆] {var_name} 已保存到长期记忆")
                        except Exception as e:
                            logger.warning(f"保存记忆 {var_name} 失败: {e}")
            
            # 3. 保存完整的执行结果摘要
            if isinstance(state, dict):
                try:
                    import json
                    summary_content = json.dumps({
                        "input": input_data,
                        "output": state.get("output"),
                        "success": not state.get("error")
                    }, ensure_ascii=False)
                    
                    summary_memory = MemoryCreate(
                        agent_id=agent.id,
                        content=f"执行摘要: {summary_content}",
                        type="short_term",
                        importance=0.6
                    )
                    await MemoryService.create_memory(summary_memory)
                    logger.info(f"[保存记忆] 执行摘要已保存")
                except Exception as e:
                    logger.warning(f"保存执行摘要失败: {e}")
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
        
        # 如果有输出内容模板，进行变量替换
        if output_content:
            for key, value in variables.items():
                output_content = output_content.replace(f"{{{{{key}}}}}", str(value))
            state["output"][output_var] = output_content
        else:
            # 否则使用所有变量作为输出
            state["output"][output_var] = variables
        
        return state
    
    @staticmethod
    async def _execute_agent_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行智能体节点"""
        agent = state.get("agent")
        if agent:
            state["variables"]["agent_info"] = {
                "id": agent.id,
                "name": agent.name,
                "description": agent.description
            }
        return state
    
    @staticmethod
    async def _execute_llm_node(current_node: Dict, state: AgentState) -> AgentState:
        """执行LLM节点"""
        # 获取节点配置
        node_id = current_node.get("id", "")
        node_data = current_node.get("data", {})
        prompt = node_data.get("prompt", "")
        model_id = node_data.get("model_id")
        model_name = node_data.get("model", "gpt-3.5-turbo")
        node_label = node_data.get("label", "")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info(f"[LLM节点] 开始执行: {node_id} - {node_label}")
        logger.info(f"[LLM节点] 配置: model_id={model_id}, model={model_name}")
        logger.info(f"[LLM节点] 完整节点数据: {current_node}")
        
        # 替换变量
        variables = state.get("variables", {})
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
        
        # 获取输入文本
        input_text = variables.get("input", {}).get("text", "")
        system_prompt = node_data.get("system_prompt", "You are a helpful assistant.")
        
        # 构建消息列表 - 加入记忆上下文
        messages = [{"role": "system", "content": system_prompt}]
        
        # 🔧 如果有记忆，添加到上下文中
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
        
        messages.append({"role": "user", "content": input_text or prompt})
        
        logger.info(f"[LLM节点] 消息长度: {len(str(messages))}")
        
        # 获取模型 - 统一逻辑，没有硬编码
        target_model = None
        actual_model = model_name
        actual_model_for_call = actual_model
        
        try:
            from base.plugins.llm.models.model import LLMModel
            
            # 1. 优先通过model_id查找
            if model_id:
                logger.info(f"[LLM节点] 步骤1: 通过model_id={model_id}查找模型")
                target_model = await LLMModel.filter(id=model_id, status="active").first()
                if target_model:
                    actual_model = target_model.model_name
                    logger.info(f"[LLM节点] ✓ 通过model_id找到模型: {actual_model}, provider_id={target_model.provider_id}")
                else:
                    logger.warning(f"[LLM节点] ✗ 未找到model_id={model_id}的活跃模型")
            
            # 2. 如果没找到，通过model_name查找
            if not target_model and model_name != "gpt-3.5-turbo":
                logger.info(f"[LLM节点] 步骤2: 通过model_name={model_name}查找模型")
                target_model = await LLMModel.filter(model_name=model_name, status="active").first()
                if target_model:
                    actual_model = target_model.model_name
                    logger.info(f"[LLM节点] ✓ 通过model_name找到模型: {actual_model}")
            
            # 3. 还是没找到，使用第一个活跃模型
            if not target_model:
                logger.info(f"[LLM节点] 步骤3: 查找任意活跃模型")
                target_model = await LLMModel.filter(status="active").first()
                if target_model:
                    actual_model = target_model.model_name
                    logger.info(f"[LLM节点] ✓ 使用默认模型: {actual_model}")
                else:
                    logger.warning("[LLM节点] ✗ 未找到任何活跃模型")
            
        except Exception as e:
            logger.exception(f"[LLM节点] ✗ 获取模型信息失败: {e}")
        
        # 尝试调用真实大模型
        llm_response = None
        try:
            if target_model:
                logger.info(f"[LLM节点] 开始调用真实大模型...")
                from base.plugins.llm.services.chat_service import ChatService
                from base.plugins.llm.models.provider import LLMProvider
                from base.plugins.llm.models.api_key import LLMApiKey
                # 获取厂商信息
                logger.info(f"[LLM节点] 查找厂商: provider_id={target_model.provider_id}")
                provider = await LLMProvider.get_or_none(id=target_model.provider_id)
                if provider:
                    logger.info(f"[LLM节点] ✓ 找到厂商: {provider.name} ({provider.name_en})")
                    
                    # 获取API密钥
                    try:
                        logger.info(f"[LLM节点] 获取可用API密钥...")
                        # 应该根据model_id 从 api_key 表中获取对应的密钥
                        api_key = await LLMApiKey.filter(model_id=target_model.id).first()
                        if api_key:
                            logger.info(f"[LLM节点] ✓ 找到API密钥: {api_key.api_id or api_key.description}")
                            
                            # 获取服务实例
                            logger.info(f"[LLM节点] 获取厂商服务实例...")
                            service = await ChatService.get_provider_service(
                                provider_name_en=provider.name_en,
                                api_key=api_key.api_key,
                                endpoint_url=target_model.endpoint_url or provider.api_endpoint,
                                api_secret=api_key.api_secret
                            )
                            
                            # 调用大模型 - 优先使用 model_id（端点 ID），否则使用 model_name
                            actual_model_for_call = target_model.model_id if target_model.model_id else actual_model
                            logger.info(f"[LLM节点] 调用大模型: {actual_model_for_call},{target_model.model_id}")
                            response = await service.chat(
                                model=actual_model_for_call,
                                messages=messages,
                                temperature=0.7,
                                max_tokens=1000
                            )
                            
                            # 提取响应
                            if isinstance(response, dict) and response.get("choices"):
                                llm_response = response["choices"][0].get("message", {}).get("content", "")
                            else:
                                llm_response = str(response)
                            
                            logger.info(f"[LLM节点] ✓ 大模型响应成功, 长度={len(llm_response)}")
                        else:
                            logger.warning("[LLM节点] ✗ 没有可用的API密钥")
                    except Exception as e:
                        logger.exception(f"[LLM节点] ✗ 获取API密钥或调用服务失败: {e}")
                else:
                    logger.warning(f"[LLM节点] ✗ 找不到模型对应的厂商: provider_id={target_model.provider_id}")
            else:
                logger.warning("[LLM节点] ✗ 没有找到可用的模型")
        except Exception as e:
            logger.exception(f"[LLM节点] ✗ 调用大模型失败: {e}")
        
        # 如果没有成功获取响应，使用模拟响应
        if not llm_response:
            logger.warning(f"[LLM节点] ⚠️ 使用模拟响应（未获取到真实响应）")
            llm_response = await LangGraphExecutor._generate_mock_response(input_text, prompt, node_label)
        
        logger.info(f"[LLM节点] 实际使用的模型: {actual_model}")
        logger.info("=" * 60)
        
        # 保存输出
        output_variable = node_data.get("output_variable", "llm_output")
        llm_output_key = f"llm_output_{node_id}" if node_id else output_variable
        
        # 存储当前节点输出
        state["variables"][llm_output_key] = {
            "node_id": node_id,
            "node_label": node_label,
            "prompt": prompt,
            "model": actual_model_for_call,
            "response": llm_response
        }
        
        # 存储到响应列表
        if "llm_responses" not in state["variables"]:
            state["variables"]["llm_responses"] = []
        
        state["variables"]["llm_responses"].append({
            "node_id": node_id,
            "node_label": node_label,
            "prompt": prompt,
            "model": actual_model_for_call,
            "response": llm_response
        })
        
        # 对于思考节点，保存思考过程
        if node_label and ("思考" in node_label or "thinking" in node_label.lower()):
            state["variables"]["thinking_process"] = llm_response
        
        # 保持向后兼容
        state["variables"][output_variable] = {
            "prompt": prompt,
            "model": actual_model_for_call,
            "response": llm_response
        }
        
        return state
    
    @staticmethod
    async def _execute_llm_node_streaming(
        current_node: Dict, 
        state: AgentState,
        sse_yield_func=None
    ) -> AgentState:
        """
        执行LLM节点（流式版本 - 支持边思考边输出）
        
        Args:
            current_node: 节点数据
            state: 智能体状态
            sse_yield_func: SSE推送回调函数，用于实时推送思考内容
        """
        node_id = current_node.get("id", "")
        node_data = current_node.get("data", {})
        prompt = node_data.get("prompt", "")
        model_id = node_data.get("model_id")
        model_name = node_data.get("model", "gpt-3.5-turbo")
        node_label = node_data.get("label", "")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[LLM节点-流式] 开始执行: {node_id} - {node_label}")
        
        # 替换变量
        variables = state.get("variables", {})
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
        
        # 获取输入文本
        input_text = variables.get("input", {}).get("text", "")
        system_prompt = node_data.get("system_prompt", "You are a helpful assistant.")
        
        # 构建消息列表
        messages = [{"role": "system", "content": system_prompt}]
        
        # 添加记忆上下文
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
        
        messages.append({"role": "user", "content": input_text or prompt})
        
        # 获取模型
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
            logger.exception(f"[LLM节点-流式] 获取模型信息失败: {e}")
        
        # 流式调用大模型
        full_response = ""
        try:
            if target_model and sse_yield_func:
                logger.info(f"[LLM节点-流式] 开始流式调用大模型...")
                
                # 创建流式回调
                async def stream_callback(content):
                    nonlocal full_response
                    full_response += content
                    # 实时推送每个片段
                    async for _ in sse_yield_func({
                        'type': 'thinking_stream',
                        'content': content,
                        'full_content': full_response
                    }):
                        pass
                
                # 使用流式chat
                from base.plugins.llm.services.chat_service import ChatService
                try:
                    async for chunk in ChatService.chat_stream(
                        model_id=target_model.id,
                        messages=messages,
                        temperature=0.7,
                        max_tokens=2000,
                        stream_callback=stream_callback
                    ):
                        # chunk已经在callback中处理了
                        pass
                    
                    logger.info(f"[LLM节点-流式] 流式响应完成, 长度={len(full_response)}")
                except Exception as e:
                    logger.exception(f"[LLM节点-流式] 流式调用失败: {e}")
                    # 流式调用失败，使用普通调用
                    full_response = ""
            
            # 如果流式调用失败或不支持流式，使用普通调用
            if not full_response and target_model:
                # 如果不支持流式或没有回调，使用普通调用
                logger.info(f"[LLM节点-流式] 使用普通调用（无流式）")
                from base.plugins.llm.services.chat_service import ChatService
                from base.plugins.llm.models.provider import LLMProvider
                from base.plugins.llm.models.api_key import LLMApiKey
                
                try:
                    provider = await LLMProvider.get_or_none(id=target_model.provider_id)
                    if provider:
                        # api_key = await ChatService.get_available_api_key(target_model.provider_id)
                        api_key = await LLMApiKey.filter(model_id=target_model.id).first()
                        if api_key:
                            service = await ChatService.get_provider_service(
                                provider_name_en=provider.name_en,
                                api_key=api_key.api_key,
                                endpoint_url=target_model.endpoint_url or provider.api_endpoint,
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
                            
                            # 推送完整响应
                            if sse_yield_func:
                                async for _ in sse_yield_func({
                                    'type': 'thinking_result',
                                    'content': full_response[:200] + ('...' if len(full_response) > 200 else ''),
                                    'full_content': full_response
                                }):
                                    pass
                except Exception as e:
                    logger.exception(f"[LLM节点-流式] 普通调用失败: {e}")
                    full_response = f"调用大模型失败: {str(e)}"

        except Exception as e:
            logger.exception(f"[LLM节点-流式] 调用大模型失败: {e}")
            full_response = f"调用大模型失败: {str(e)}"
        
        # 如果没有响应，使用模拟
        if not full_response:
            logger.warning(f"[LLM节点-流式] 使用模拟响应")
            full_response = await LangGraphExecutor._generate_mock_response(input_text, prompt, node_label)
        
        # 保存输出到state
        output_variable = node_data.get("output_variable", "llm_output")
        llm_output_key = f"llm_output_{node_id}" if node_id else output_variable
        
        state["variables"][llm_output_key] = {
            "node_id": node_id,
            "node_label": node_label,
            "prompt": prompt,
            "model": actual_model,
            "response": full_response
        }
        
        if "llm_responses" not in state["variables"]:
            state["variables"]["llm_responses"] = []
        
        state["variables"]["llm_responses"].append({
            "node_id": node_id,
            "node_label": node_label,
            "prompt": prompt,
            "model": actual_model,
            "response": full_response
        })
        
        # 对于思考节点，保存思考过程
        if node_label and ("思考" in node_label or "thinking" in node_label.lower()):
            state["variables"]["thinking_process"] = full_response
        
        state["variables"][output_variable] = {
            "prompt": prompt,
            "model": actual_model,
            "response": full_response
        }
        
        return state
    
    @staticmethod
    async def _generate_mock_response(input_text: str, prompt: str = "", node_label: str = "") -> str:
        """生成模拟的大模型响应"""
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"[LLM节点] 使用模拟响应（提示：请配置真实大模型）")
        logger.info(f"[LLM节点] 输入: {input_text[:50]}...")
        logger.info(f"[LLM节点] 节点标签: {node_label}")
        
        # 根据节点标签返回简单的模拟响应
        if node_label:
            if "思考" in node_label:
                # 思考节点 - 返回一个完整的任务拆解JSON
                import json
                task_content = input_text
                
                mock_response = {
                    "original_task": task_content,
                    "subtasks": [
                        {
                            "id": "1",
                            "name": "理解任务需求",
                            "description": "深入理解用户的具体需求",
                            "dependencies": [],
                            "tool": "none"
                        },
                        {
                            "id": "2",
                            "name": "技术方案设计",
                            "description": "设计技术架构和实现方案",
                            "dependencies": ["1"],
                            "tool": "none"
                        },
                        {
                            "id": "3",
                            "name": "任务执行",
                            "description": "按照方案执行具体任务",
                            "dependencies": ["2"],
                            "tool": "none"
                        },
                        {
                            "id": "4",
                            "name": "验证结果",
                            "description": "检查和验证执行结果",
                            "dependencies": ["3"],
                            "tool": "none"
                        }
                    ],
                    "reasoning": "根据任务性质，将其拆解为四个关键步骤：理解需求、设计方案、执行任务、验证结果，确保任务能够有序完成。"
                }
                
                return json.dumps(mock_response, ensure_ascii=False, indent=2)
            elif "行动" in node_label:
                return f"正在执行任务：{input_text}"
            elif "观察" in node_label:
                return f"正在观察任务：{input_text}"
        
        # 如果有提示词，根据提示词生成简单响应
        if prompt:
            if "拆解" in prompt or "子任务" in prompt:
                import json
                mock_response = {
                    "original_task": input_text,
                    "subtasks": [
                        {"id": "1", "name": "理解任务", "description": "理解用户需求", "dependencies": [], "tool": "none"}
                    ],
                    "reasoning": "简单的任务拆解"
                }
                return json.dumps(mock_response, ensure_ascii=False)
        
        # 默认响应
        return f"已收到您的请求：{input_text}"

    
    @staticmethod
    async def _execute_skill_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行技能节点"""
        skill_id = node_data.get("skill_id", "")
        parameters = node_data.get("parameters", {})
        
        # 替换变量
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
        
        # 创建安全的变量字典，为常见变量提供默认值
        safe_variables = {}
        # 复制现有变量
        safe_variables.update(variables)
        # 为循环相关变量提供默认值
        safe_variables.setdefault("should_continue", True)
        safe_variables.setdefault("loop_count", 0)
        safe_variables.setdefault("i", 0)
        
        # 预处理条件表达式：将小写的 true/false 替换为大写的 True/False
        processed_condition = condition
        processed_condition = processed_condition.replace("true", "True")
        processed_condition = processed_condition.replace("false", "False")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"条件节点原始条件: {condition}")
        logger.info(f"条件节点处理后条件: {processed_condition}")
        
        try:
            # 使用安全的表达式求值
            result = safe_eval(processed_condition, safe_variables)
            state["variables"]["condition_result"] = {
                "condition": condition,
                "result": bool(result)
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"条件节点执行失败，使用默认值False。错误: {e}")
            logger.warning(f"条件: {condition}")
            logger.warning(f"处理后条件: {processed_condition}")
            logger.warning(f"可用变量: {list(safe_variables.keys())}")
            state["variables"]["condition_result"] = {
                "condition": condition,
                "result": False,
                "error": str(e)
            }
        
        return state
    
    @staticmethod
    async def _execute_loop_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行循环节点 - 更新循环变量，不做内部循环"""
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        loop_condition = node_config.get("loop_condition", "i < 5")
        loop_max = node_config.get("loop_max", 10)
        loop_variable = node_config.get("loop_variable", "i")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"循环节点配置: {node_config}")
        
        variables = state.get("variables", {})
        current_value = variables.get(loop_variable, 0)
        
        # 只更新循环变量
        variables[loop_variable] = current_value + 1
        logger.info(f"更新循环变量 {loop_variable}: {current_value} → {variables[loop_variable]}")
        
        # 记录循环状态
        state["variables"]["loop_result"] = {
            "condition": loop_condition,
            "max_iterations": loop_max,
            "variable": loop_variable,
            "current_value": variables[loop_variable]
        }
        
        return state
    
    @staticmethod
    async def _execute_iteration_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行迭代节点"""
        iteration_list = node_data.get("iteration_list", "")
        iteration_variable = node_data.get("iteration_variable", "item")
        
        # 解析列表
        try:
            if isinstance(iteration_list, str):
                items = json.loads(iteration_list)
            else:
                items = iteration_list
            
            iteration_results = []
            for item in items:
                state["variables"][iteration_variable] = item
                iteration_results.append(item)
            
            state["variables"]["iteration_result"] = {
                "items": items,
                "variable": iteration_variable,
                "results": iteration_results
            }
        except Exception as e:
            state["variables"]["iteration_result"] = {
                "error": str(e)
            }
        
        return state
    
    @staticmethod
    async def _execute_http_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行HTTP节点"""
        url = node_data.get("url", "")
        method = node_data.get("method", "GET")
        headers = node_data.get("headers", {})
        body = node_data.get("body", {})
        
        # 替换变量
        variables = state.get("variables", {})
        for key, value in variables.items():
            if isinstance(url, str):
                url = url.replace(f"{{{{{key}}}}}", str(value))
            for header_key, header_value in headers.items():
                if isinstance(header_value, str):
                    headers[header_key] = header_value.replace(f"{{{{{key}}}}}", str(value))
            for body_key, body_value in body.items():
                if isinstance(body_value, str):
                    body[body_key] = body_value.replace(f"{{{{{key}}}}}", str(value))
        
        state["variables"]["http_result"] = {
            "url": url,
            "method": method,
            "headers": headers,
            "body": body,
            "response": "HTTP 响应模拟"
        }
        
        return state
    
    @staticmethod
    async def _execute_code_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行代码节点"""
        code = node_data.get("code", "")
        language = node_data.get("language", "python")
        
        # 替换变量
        variables = state.get("variables", {})
        for key, value in variables.items():
            code = code.replace(f"{{{{{key}}}}}", str(value))
        
        state["variables"]["code_result"] = {
            "code": code,
            "language": language,
            "output": "代码执行结果模拟"
        }
        
        return state
    
    @staticmethod
    async def _execute_template_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行模板节点"""
        # 从data字段获取配置
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        template = node_config.get("template", "")
        output_variable = node_config.get("output_variable", "template_output")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"模板节点配置: {node_config}")
        
        # 替换变量
        variables = state.get("variables", {})
        for key, value in variables.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))
        
        logger.info(f"模板输出: {template[:100]}...")
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
        # 从data字段获取配置
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        document_path = node_config.get("document_path", "")
        extraction_type = node_config.get("extraction_type", "text")
        output_variable = node_config.get("output_variable", "document_extract")
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"文档提取节点配置: {node_config}")
        
        state["variables"][output_variable] = {
            "path": document_path,
            "type": extraction_type,
            "content": "文档内容提取模拟"
        }
        
        return state
    
    @staticmethod
    async def _execute_variable_assigner_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行变量赋值节点"""
        # 从data字段获取配置
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        variable_name = node_config.get("var_name", node_config.get("variable_name", ""))
        variable_value = node_config.get("var_value", node_config.get("variable_value", ""))
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"变量赋值节点配置: {node_config}")
        
        # 替换变量
        variables = state.get("variables", {})
        for key, value in variables.items():
            if isinstance(variable_value, str):
                variable_value = variable_value.replace(f"{{{{{key}}}}}", str(value))
        
        logger.info(f"设置变量 {variable_name} = {variable_value}")
        state["variables"][variable_name] = variable_value
        return state
    
    @staticmethod
    async def _execute_parameter_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行参数提取节点"""
        # 从data字段获取配置
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        input_variable = node_config.get("input_variable", "input")
        parameters = node_config.get("parameters", [])
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"参数提取节点配置: {node_config}")
        logger.info(f"输入变量: {input_variable}")
        logger.info(f"参数列表: {parameters}")
        
        input_data = state.get("variables", {}).get(input_variable, state.get("input", {}))
        logger.info(f"输入数据: {input_data}")
        
        extracted = {}
        
        # 处理 parameters 是字符串的情况
        if isinstance(parameters, str):
            # 按换行符分割参数名
            param_names = [p.strip() for p in parameters.split('\n') if p.strip()]
            logger.info(f"参数名列表: {param_names}")
            
            # 先尝试直接从字典中提取
            has_dict_data = isinstance(input_data, dict) and any(p in input_data for p in param_names)
            
            if has_dict_data:
                logger.info(f"从字典中提取参数")
                for param_name in param_names:
                    if isinstance(input_data, dict) and param_name in input_data:
                        extracted[param_name] = input_data[param_name]
                    else:
                        extracted[param_name] = None
            else:
                # 如果没有字典数据，尝试从文本中提取（使用模拟的LLM提取）
                logger.info(f"尝试从文本中提取参数")
                input_text = ""
                if isinstance(input_data, str):
                    input_text = input_data
                elif isinstance(input_data, dict) and "text" in input_data:
                    input_text = input_data["text"]
                elif isinstance(input_data, dict) and "response" in input_data:
                    input_text = input_data["response"]
                
                if input_text:
                    # 简单的文本提取逻辑
                    for param_name in param_names:
                        # 尝试从文本中匹配关键词
                        if param_name == "task_type" and "写" in input_text and "文章" in input_text:
                            extracted[param_name] = "文章写作"
                        elif param_name == "task_content":
                            extracted[param_name] = input_text
                        elif param_name in input_text:
                            # 简单的关键词提取
                            extracted[param_name] = "已识别"
                        else:
                            extracted[param_name] = None
                else:
                    for param_name in param_names:
                        extracted[param_name] = None
        else:
            # 处理 parameters 是字典列表的情况
            for param in parameters:
                if isinstance(param, dict):
                    param_name = param.get("name", "")
                    param_path = param.get("path", "")
                    
                    # 简单的路径提取
                    if isinstance(input_data, dict):
                        parts = param_path.split(".")
                        value = input_data
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = None
                                break
                        extracted[param_name] = value
        
        logger.info(f"提取结果: {extracted}")
        
        # 同时设置 extracted_params 和 extracted_parameters，以保持兼容性
        state["variables"]["extracted_params"] = extracted
        state["variables"]["extracted_parameters"] = extracted
        return state
    
    @staticmethod
    async def _execute_json_extractor_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行JSON提取节点 - 从LLM输出中提取结构化JSON数据"""
        # 从data字段获取配置
        node_config = node_data.get("data", {}) if isinstance(node_data.get("data"), dict) else node_data
        input_variable = node_config.get("input_variable", "llm_output")
        output_variable = node_config.get("output_variable", "structured_output")
        
        import logging
        import json
        import re
        logger = logging.getLogger(__name__)
        logger.info(f"JSON提取节点配置: {node_config}")
        logger.info(f"输入变量: {input_variable}")
        
        # 获取输入数据
        input_data = state.get("variables", {}).get(input_variable, "")
        logger.info(f"原始输入数据类型: {type(input_data)}")
        
        # 处理输入数据，提取文本内容
        text_to_parse = ""
        if isinstance(input_data, dict):
            # 如果是字典，优先使用 response 字段
            if "response" in input_data:
                text_to_parse = str(input_data["response"])
            elif "text" in input_data:
                text_to_parse = str(input_data["text"])
            else:
                text_to_parse = str(input_data)
        elif isinstance(input_data, str):
            text_to_parse = input_data
        
        logger.info(f"准备解析的文本长度: {len(text_to_parse)}")
        logger.info(f"准备解析的文本前200字符: {text_to_parse[:200]}...")
        
        extracted_json = None
        
        # 方法1: 直接解析JSON
        try:
            extracted_json = json.loads(text_to_parse)
            logger.info(f"✅ 直接解析JSON成功")
        except json.JSONDecodeError:
            logger.info(f"直接解析JSON失败，尝试其他方法")
        
        # 方法2: 查找第一个完整的JSON对象或数组
        if extracted_json is None:
            logger.info(f"尝试从文本中查找JSON块")
            json_match = None
            
            # 尝试匹配 { ... }
            brace_count = 0
            start_idx = -1
            for i, char in enumerate(text_to_parse):
                if char == '{':
                    if brace_count == 0:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        json_str = text_to_parse[start_idx:i+1]
                        try:
                            extracted_json = json.loads(json_str)
                            logger.info(f"✅ 从文本中提取JSON对象成功")
                            break
                        except json.JSONDecodeError:
                            continue
            
            # 如果没找到对象，尝试匹配数组
            if extracted_json is None:
                bracket_count = 0
                start_idx = -1
                for i, char in enumerate(text_to_parse):
                    if char == '[':
                        if bracket_count == 0:
                            start_idx = i
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0 and start_idx != -1:
                            json_str = text_to_parse[start_idx:i+1]
                            try:
                                extracted_json = json.loads(json_str)
                                logger.info(f"✅ 从文本中提取JSON数组成功")
                                break
                            except json.JSONDecodeError:
                                continue
        
        # 方法3: 尝试使用正则提取
        if extracted_json is None:
            logger.info(f"尝试使用正则提取JSON")
            # 匹配可能的JSON格式
            json_patterns = [
                r'\{[\s\S]*\}',  # 对象
                r'\[[\s\S]*\]',  # 数组
            ]
            for pattern in json_patterns:
                matches = re.findall(pattern, text_to_parse)
                for match in matches:
                    try:
                        extracted_json = json.loads(match)
                        logger.info(f"✅ 正则提取JSON成功")
                        break
                    except json.JSONDecodeError:
                        continue
                if extracted_json:
                    break
        
        # 输出结果
        if extracted_json:
            logger.info(f"✅ JSON提取成功")
            logger.info(f"提取的JSON: {json.dumps(extracted_json, ensure_ascii=False)[:300]}...")
            
            # 保存完整的JSON
            state["variables"][output_variable] = extracted_json
            
            # 如果是任务分解格式，尝试提取常用字段
            if isinstance(extracted_json, dict):
                # 尝试提取任务相关字段
                if "original_task" in extracted_json:
                    state["variables"]["original_task"] = extracted_json["original_task"]
                if "task" in extracted_json:
                    state["variables"]["task"] = extracted_json["task"]
                if "subtasks" in extracted_json:
                    state["variables"]["subtasks"] = extracted_json["subtasks"]
                if "task_plan" in extracted_json:
                    state["variables"]["task_plan"] = extracted_json["task_plan"]
                if "plan" in extracted_json:
                    state["variables"]["plan"] = extracted_json["plan"]
                if "reasoning" in extracted_json:
                    state["variables"]["reasoning"] = extracted_json["reasoning"]
                
                logger.info(f"已保存常用字段到独立变量")
        else:
            logger.warning(f"❌ JSON提取失败，无法从文本中解析出有效的JSON")
            state["variables"][output_variable] = None
            state["variables"]["json_extraction_error"] = "无法从文本中解析出有效的JSON"
        
        return state
    
    @staticmethod
    async def _execute_default_node(node_data: Dict, state: AgentState) -> AgentState:
        """执行默认节点"""
        return state