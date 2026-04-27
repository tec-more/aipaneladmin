"""
Agent API routes
"""
from typing import List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from base.plugins.agent.services.agent_service import AgentService
from base.common.response import success_response, fail_response

agent_router = APIRouter(prefix="/agents", tags=["agents"])


@agent_router.post("/")
async def create_agent(agent: AgentCreate):
    """Create a new agent"""
    try:
        created_agent = await AgentService.create_agent(agent)
        
        skill_count = 0
        memory_count = 0
        workflow_count = 0
        dialog_flow_count = 0
        
        data = AgentResponse(
            id=created_agent.id,
            name=created_agent.name,
            description=created_agent.description,
            status=created_agent.status,
            memory_capacity=created_agent.memory_capacity,
            system_prompt=created_agent.system_prompt,
            reasoning_strategy=created_agent.reasoning_strategy,
            llm_model_id=None,
            created_at=created_agent.created_at,
            updated_at=created_agent.updated_at,
            skill_count=skill_count,
            memory_count=memory_count,
            workflow_count=workflow_count,
            dialog_flow_count=dialog_flow_count
        )
        
        return success_response(data=data, msg="智能体创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.get("/")
async def get_agents(skip: int = 0, limit: int = 100, name: str = "", status: str = ""):
    """Get all agents"""
    from base.plugins.agent.models.agent import Agent
    
    # 构建查询条件
    query = Agent.all()
    
    if name:
        query = query.filter(name__icontains=name)
    
    if status:
        query = query.filter(status=status)
    
    # 获取总数
    total = await query.count()
    
    # 获取分页数据
    agents = await query.offset(skip).limit(limit).order_by("-created_at").all()
    
    response = []
    for agent in agents:
        skill_count = 0
        memory_count = 0
        
        response.append({
            "id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "status": agent.status,
            "memory_capacity": agent.memory_capacity,
            "system_prompt": agent.system_prompt,
            "reasoning_strategy": agent.reasoning_strategy,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
            "skill_count": skill_count,
            "memory_count": memory_count
        })
    return success_response(data={"items": response, "total": total})


@agent_router.get("/{agent_id}")
async def get_agent(agent_id: int):
    """Get agent by ID"""
    agent = await AgentService.get_agent_by_id(agent_id)
    if not agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = 0
    memory_count = 0
    
    data = {
        "id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "status": agent.status,
        "memory_capacity": agent.memory_capacity,
        "system_prompt": agent.system_prompt,
        "reasoning_strategy": agent.reasoning_strategy,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        "skill_count": skill_count,
        "memory_count": memory_count
    }
    return success_response(data=data)


@agent_router.put("/{agent_id}")
async def update_agent(agent_id: int, agent: AgentUpdate):
    """Update agent"""
    updated_agent = await AgentService.update_agent(agent_id, agent)
    if not updated_agent:
        return fail_response(msg="智能体不存在", code=404)
    
    skill_count = 0
    memory_count = 0
    
    data = {
        "id": updated_agent.id,
        "name": updated_agent.name,
        "description": updated_agent.description,
        "status": updated_agent.status,
        "memory_capacity": updated_agent.memory_capacity,
        "system_prompt": updated_agent.system_prompt,
        "reasoning_strategy": updated_agent.reasoning_strategy,
        "created_at": updated_agent.created_at.isoformat() if updated_agent.created_at else None,
        "updated_at": updated_agent.updated_at.isoformat() if updated_agent.updated_at else None,
        "skill_count": skill_count,
        "memory_count": memory_count
    }
    return success_response(data=data, msg="智能体更新成功")


@agent_router.delete("/{agent_id}")
async def delete_agent(agent_id: int):
    """Delete agent"""
    success = await AgentService.delete_agent(agent_id)
    if not success:
        return fail_response(msg="智能体不存在", code=404)
    return success_response(msg="智能体删除成功")


@agent_router.post("/{agent_id}/execute")
async def execute_agent(agent_id: int, input_data: dict):
    """Execute agent"""
    result = await AgentService.execute_agent(agent_id, input_data)
    if result.get("success"):
        return success_response(data=result, msg="智能体执行成功")
    else:
        return fail_response(msg=result.get("message", "执行失败"))


@agent_router.post("/{agent_id}/graph/execute")
async def execute_agent_graph(agent_id: int, input_data: dict):
    """Execute agent graph diagram using LangGraph"""
    print(f"=== 执行智能体结构图: agent_id={agent_id}, input_data={input_data} ===")
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"执行智能体结构图: agent_id={agent_id}, input_data={input_data}")
        
        print(f"1. 导入LangGraphExecutor")
        from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
        
        print(f"2. 获取智能体: agent_id={agent_id}")
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            print(f"智能体不存在: agent_id={agent_id}")
            logger.error(f"智能体不存在: agent_id={agent_id}")
            return fail_response(msg="智能体不存在", code=404)
        
        print(f"3. 智能体信息: id={agent.id}, name={agent.name}")
        print(f"4. graph_definition类型: {type(agent.graph_definition)}")
        print(f"5. graph_definition值: {agent.graph_definition}")
        logger.info(f"智能体信息: id={agent.id}, name={agent.name}")
        logger.info(f"graph_definition类型: {type(agent.graph_definition)}")
        logger.info(f"graph_definition值: {agent.graph_definition}")
        
        print(f"6. 创建执行记录")
        from base.plugins.agent.models.dialog_flow import DialogFlowExecution
        execution_record = await DialogFlowExecution.create(
            dialog_flow_id=0,  # 用0表示是智能体图执行
            user_id=None,
            input_data=input_data,
            status="running",
            execution_path=[]
        )
        logger.info(f"创建执行记录: id={execution_record.id}")
        
        print(f"7. 执行智能体")
        result = await LangGraphExecutor.execute_agent(agent, input_data)
        
        print(f"8. 执行结果: {result}")
        logger.info(f"执行结果类型: {type(result)}")
        logger.info(f"执行结果: {result}")
        
        print(f"9. 更新执行记录")
        execution_record.output_data = result
        
        # 提取执行路径 - 从结果的多个位置尝试获取
        execution_path = []
        if isinstance(result, dict):
            if result.get('variables') and result['variables'].get('execution_path'):
                execution_path = result['variables']['execution_path']
            elif result.get('execution_path'):
                execution_path = result['execution_path']
            elif result.get('trace'):
                execution_path = result['trace']
            elif result.get('execution_trace'):
                execution_path = result['execution_trace']
        
        execution_record.execution_path = execution_path
        logger.info(f"提取到的执行路径: {execution_path}")
        
        from datetime import datetime
        execution_record.completed_at = datetime.now()
        execution_record.status = "completed" if (isinstance(result, dict) and result.get("success")) else "failed"
        
        # 显式保存并检查
        await execution_record.save()
        
        # 重新获取以确认保存成功
        saved_record = await DialogFlowExecution.get(id=execution_record.id)
        logger.info(f"保存后的执行记录: id={saved_record.id}, status={saved_record.status}")
        logger.info(f"保存后的输出数据: {saved_record.output_data}")
        logger.info(f"保存后的执行路径: {saved_record.execution_path}")
        
        if isinstance(result, dict) and result.get("success"):
            print(f"10. 执行成功")
            return success_response(data=result, msg="结构图执行成功")
        else:
            error_msg = result.get("message", "结构图执行失败") if isinstance(result, dict) else str(result)
            print(f"10. 执行失败: {error_msg}")
            return fail_response(msg=error_msg)
    except Exception as e:
        import traceback
        print(f"=== 异常: {e} ===")
        print(traceback.format_exc())
        logger.exception(f"执行智能体结构图失败: {e}")
        return fail_response(msg=f"结构图执行失败: {str(e)}", data={"traceback": traceback.format_exc()})


async def sse_execution_generator(agent, input_data) -> AsyncGenerator[str, None]:
    """SSE事件生成器 - 实时推送执行过程（支持边思考边输出）"""
    import json
    from datetime import datetime
    from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
    
    # 创建SSE推送函数
    async def sse_yield(event_data):
        """SSE数据推送helper"""
        yield f"data: {json.dumps({
            **event_data,
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False)}\n\n"
    
    # 推送开始
    async for data in sse_yield({
        'type': 'start',
        'message': '开始执行智能体'
    }):
        yield data
    
    try:
        import asyncio
        
        # 检查是否有结构图配置
        flow_data = None
        if agent.graph_definition:
            if isinstance(agent.graph_definition, str):
                try:
                    flow_data = json.loads(agent.graph_definition)
                except json.JSONDecodeError:
                    flow_data = None
            else:
                flow_data = agent.graph_definition
        
        if flow_data and isinstance(flow_data, dict) and flow_data.get("nodes"):
            # 使用结构图执行
            nodes = flow_data.get("nodes", [])
            edges = flow_data.get("edges", [])
            
            # 查找开始节点
            start_node = None
            for node in nodes:
                if node.get("type") == "start":
                    start_node = node
                    break
            if not start_node and nodes:
                start_node = nodes[0]
            
            if start_node:
                # 推送初始化信息
                async for data in sse_yield({
                    'type': 'info',
                    'label': '初始化',
                    'message': '初始化执行环境'
                }):
                    yield data
                
                # 构建节点映射
                node_map = {node.get("id"): node for node in nodes}
                current_node_id = start_node.get("id")
                
                # 初始化状态
                state = {
                    "input": input_data,
                    "output": {},
                    "variables": {},
                    "execution_trace": [],
                    "current_node": None,
                    "error": None,
                    "agent": agent
                }
                
                step_count = 0
                max_steps = 100
                
                while current_node_id and step_count < max_steps:
                    step_count += 1
                    
                    current_node = node_map.get(current_node_id)
                    if not current_node:
                        break
                    
                    node_type = current_node.get("type")
                    node_data = current_node.get("data", {})
                    node_label = node_data.get("label", node_type)
                    
                    # 推送节点开始
                    async for data in sse_yield({
                        'type': 'node_start',
                        'node_id': current_node_id,
                        'node_type': node_type,
                        'node_label': node_label,
                        'step': step_count
                    }):
                        yield data
                    
                    try:
                        if node_type == "start":
                            async for data in sse_yield({
                                'type': 'info',
                                'label': '开始节点',
                                'message': '开始执行...'
                            }):
                                yield data
                            state["variables"]["start_time"] = datetime.now().isoformat()
                        
                        elif node_type == "end":
                            async for data in sse_yield({
                                'type': 'info',
                                'label': '结束节点',
                                'message': '执行结束'
                            }):
                                yield data
                            state["output"]["end_time"] = datetime.now().isoformat()
                            break
                        
                        elif node_type == "llm":
                            # LLM节点 - 根据配置决定流式或非流式
                            async for data in sse_yield({
                                'type': 'thinking',
                                'label': node_label,
                                'message': f'正在调用大模型...'
                            }):
                                yield data
                            
                            # 检查是否启用流式输出
                            is_streaming = node_data.get("stream", False)
                            
                            if is_streaming:
                                # 流式执行 - 边思考边输出
                                async def llm_stream_callback(chunk_data):
                                    """LLM流式回调 - 实时推送每个片段"""
                                    async for data in sse_yield({
                                        'type': 'thinking_stream',
                                        'content': chunk_data.get('content', ''),
                                        'full_content': chunk_data.get('full_content', ''),
                                        'label': node_label
                                    }):
                                        yield data
                                
                                # 执行LLM节点（流式版本）
                                state = await LangGraphExecutor._execute_llm_node_streaming(
                                    current_node, 
                                    state,
                                    sse_yield_func=llm_stream_callback
                                )
                                
                                # 获取完整响应
                                llm_output = state["variables"].get("llm_output", {})
                                full_response = llm_output.get("response", "")
                            else:
                                # 非流式执行 - 一次性返回
                                state = await LangGraphExecutor._execute_llm_node(current_node, state)
                                
                                # 获取完整响应
                                llm_output = state["variables"].get("llm_output", {})
                                full_response = llm_output.get("response", "")
                            
                            async for data in sse_yield({
                                'type': 'thinking_result',
                                'label': node_label,
                                'content': full_response[:200] + ('...' if len(full_response) > 200 else ''),
                                'full_content': full_response
                            }):
                                yield data
                        
                        elif node_type == "skill":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': f'执行技能: {node_data.get("skill_id", "unknown")}'
                            }):
                                yield data
                            
                            state = await LangGraphExecutor._execute_skill_node(node_data, state)
                            
                            skill_result = state["variables"].get("skill_output", {})
                            async for data in sse_yield({
                                'type': 'observation',
                                'label': '技能执行结果',
                                'content': str(skill_result)[:500]
                            }):
                                yield data
                        
                        elif node_type == "agent":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '执行智能体...'
                            }):
                                yield data
                            
                            state = await LangGraphExecutor._execute_agent_node(node_data, state)
                        
                        elif node_type == "condition":
                            async for data in sse_yield({
                                'type': 'thinking',
                                'label': node_label,
                                'message': '条件判断中...'
                            }):
                                yield data
                            
                            state = await LangGraphExecutor._execute_condition_node(node_data, state)
                            
                            condition_result = state["variables"].get("condition_result", {}).get("result", False)
                            async for data in sse_yield({
                                'type': 'observation',
                                'label': '条件判断结果',
                                'content': f'结果: {condition_result}'
                            }):
                                yield data
                        
                        elif node_type == "loop":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '循环节点'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_loop_node(node_data, state)
                        
                        elif node_type == "output":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '生成输出'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_output_node(node_data, state)
                        
                        elif node_type == "input":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '处理输入'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_input_node(node_data, state)
                        
                        elif node_type == "iteration":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '执行迭代'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_iteration_node(node_data, state)
                        
                        elif node_type == "http":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '发送HTTP请求'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_http_node(node_data, state)
                        
                        elif node_type == "code":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '执行代码'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_code_node(node_data, state)
                        
                        elif node_type == "template":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '处理模板'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_template_node(node_data, state)
                        
                        elif node_type == "variable_aggregator":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '聚合变量'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_variable_aggregator_node(node_data, state)
                        
                        elif node_type == "document_extractor":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '提取文档'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_document_extractor_node(node_data, state)
                        
                        elif node_type == "variable_assigner":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '赋值变量'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_variable_assigner_node(node_data, state)
                        
                        elif node_type == "parameter_extractor":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '提取参数'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_parameter_extractor_node(node_data, state)
                        
                        elif node_type == "json_extractor":
                            async for data in sse_yield({
                                'type': 'action',
                                'label': node_label,
                                'message': '提取JSON'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_json_extractor_node(node_data, state)
                        
                        else:
                            async for data in sse_yield({
                                'type': 'info',
                                'label': node_label,
                                'message': f'执行节点: {node_type}'
                            }):
                                yield data
                            state = await LangGraphExecutor._execute_default_node(node_data, state)
                        
                        # 推送节点完成
                        async for data in sse_yield({
                            'type': 'node_complete',
                            'node_id': current_node_id,
                            'node_type': node_type,
                            'node_label': node_label
                        }):
                            yield data
                        
                    except Exception as e:
                        async for data in sse_yield({
                            'type': 'error',
                            'node_id': current_node_id,
                            'message': str(e)
                        }):
                            yield data
                        state["error"] = str(e)
                        break
                    
                    # 确定下一个节点
                    if node_type == "condition":
                        condition_result = state.get("variables", {}).get("condition_result", {}).get("result", False)
                        outgoing_edges = [e for e in edges if e.get("source") == current_node_id]
                        if len(outgoing_edges) >= 2:
                            target_idx = 0 if condition_result else 1
                            current_node_id = outgoing_edges[target_idx].get("target") if target_idx < len(outgoing_edges) else None
                        elif outgoing_edges:
                            current_node_id = outgoing_edges[0].get("target")
                        else:
                            current_node_id = None
                    else:
                        outgoing_edges = [e for e in edges if e.get("source") == current_node_id]
                        current_node_id = outgoing_edges[0].get("target") if outgoing_edges else None
                
                # 执行完成
                async for data in sse_yield({
                    'type': 'complete',
                    'result': state.get("output", {}),
                    'variables': state.get("variables", {})
                }):
                    yield data
            else:
                # 没有开始节点
                async for data in sse_yield({
                    'type': 'error',
                    'message': '结构图没有开始节点'
                }):
                    yield data
        else:
            # 没有结构图，使用简化执行
            async for data in sse_yield({
                'type': 'thinking',
                'label': '智能体执行',
                'message': '执行中...'
            }):
                yield data
            
            result = await LangGraphExecutor.execute_agent(agent, input_data)
            
            async for data in sse_yield({
                'type': 'complete',
                'result': result.get('output', {}) if isinstance(result, dict) else {},
                'variables': result.get('variables', {}) if isinstance(result, dict) else result
            }):
                yield data
            
    except Exception as e:
        import traceback
        async for data in sse_yield({
            'type': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }):
            yield data


@agent_router.post("/{agent_id}/graph/execute/sse")
async def execute_agent_graph_sse(agent_id: int, input_data: dict):
    """使用SSE实时执行智能体结构图"""
    try:
        from base.plugins.agent.models.agent import Agent
        
        agent = await Agent.get_or_none(id=agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        return StreamingResponse(
            sse_execution_generator(agent, input_data),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        import traceback
        print(f"SSE执行错误: {e}")
        print(traceback.format_exc())
        return fail_response(msg=str(e), code=500)


@agent_router.get("/{agent_id}/graph")
async def get_agent_graph(agent_id: int):
    """Get agent graph definition"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== 获取智能体结构图: agent_id={agent_id} ===")
        
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            logger.error(f"智能体不存在: agent_id={agent_id}")
            return fail_response(msg="智能体不存在", code=404)
        
        logger.info(f"agent.graph_definition: {agent.graph_definition}")
        logger.info(f"agent.graph_definition 类型: {type(agent.graph_definition)}")
        
        return success_response(data={
            "graph_definition": agent.graph_definition
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"获取智能体结构图失败: {e}")
        return fail_response(msg=str(e))


@agent_router.put("/{agent_id}/graph")
async def update_agent_graph(agent_id: int, graph_data: dict):
    """Update agent graph definition"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"=== 保存智能体结构图: agent_id={agent_id} ===")
        logger.info(f"接收到的 graph_data: {graph_data}")
        logger.info(f"graph_data 类型: {type(graph_data)}")
        
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            logger.error(f"智能体不存在: agent_id={agent_id}")
            return fail_response(msg="智能体不存在", code=404)
        
        logger.info(f"保存前 agent.graph_definition: {agent.graph_definition}")
        
        agent.graph_definition = graph_data
        await agent.save()
        
        logger.info(f"保存后 agent.graph_definition: {agent.graph_definition}")
        logger.info(f"保存后 agent.graph_definition 类型: {type(agent.graph_definition)}")
        
        return success_response(data={"graph_definition": agent.graph_definition}, msg="智能体结构图保存成功")
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.exception(f"保存智能体结构图失败: {e}")
        return fail_response(msg=str(e))


@agent_router.get("/test")
async def test_endpoint():
    """测试端点"""
    print("=== 测试端点被调用 ===")
    return success_response(data={"message": "测试成功"}, msg="测试端点响应成功")


@agent_router.post("/process-documents")
async def process_documents(
    directory_path: str = Query(..., description="文档目录路径"),
    vector_store_path: str = Query(..., description="向量库存储路径")
):
    """处理文档并生成向量库"""
    try:
        from base.plugins.agent.services.document_processing_service import DocumentProcessingService, VECTOR_SUPPORT
        import os
        
        # 检查向量支持是否启用
        if not VECTOR_SUPPORT:
            return fail_response(msg="向量支持未启用，请安装相关依赖", code=400)
        
        # 检查目录是否存在
        if not os.path.exists(directory_path):
            return fail_response(msg="文档目录不存在", code=404)
        
        # 确保向量库存储路径存在
        os.makedirs(vector_store_path, exist_ok=True)
        
        # 处理文档并创建向量库
        vector_store = DocumentProcessingService.process_document_directory(directory_path, vector_store_path)
        
        # 获取向量库信息
        collection_name = vector_store._collection.name
        document_count = vector_store._collection.count()
        
        return success_response(
            data={
                "vector_store_path": vector_store_path,
                "collection_name": collection_name,
                "document_count": document_count,
                "message": f"成功处理文档并生成向量库，共处理 {document_count} 个文档片段"
            },
            msg="文档处理成功"
        )
    except Exception as e:
        return fail_response(msg=str(e), code=500)


@agent_router.get("/{agent_id}/skills")
async def get_agent_skills(agent_id: int):
    """Get agent skills"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        config = agent.config or {}
        skill_ids = config.get("skills", [])
        
        from base.plugins.agent.models.skill import Skill
        skills = []
        if skill_ids:
            skills = await Skill.filter(id__in=skill_ids).all()
        
        return success_response(data={"skills": skills})
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.post("/{agent_id}/skills/{skill_id}")
async def add_skill_to_agent(agent_id: int, skill_id: int):
    """Add skill to agent"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        if not agent.config:
            agent.config = {}
        
        skills = agent.config.get("skills", [])
        if skill_id not in skills:
            skills.append(skill_id)
            agent.config["skills"] = skills
            await agent.save()
        
        return success_response(msg="技能添加成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.delete("/{agent_id}/skills/{skill_id}")
async def remove_skill_from_agent(agent_id: int, skill_id: int):
    """Remove skill from agent"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        if not agent.config:
            agent.config = {}
        
        skills = agent.config.get("skills", [])
        if skill_id in skills:
            skills.remove(skill_id)
            agent.config["skills"] = skills
            await agent.save()
        
        return success_response(msg="技能移除成功")
    except Exception as e:
        return fail_response(msg=str(e))


@agent_router.put("/{agent_id}/skills")
async def set_agent_skills(agent_id: int, data: dict):
    """Set agent skills"""
    try:
        agent = await AgentService.get_agent_by_id(agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        if not agent.config:
            agent.config = {}
        
        skill_ids = data.get("skill_ids", [])
        agent.config["skills"] = skill_ids
        await agent.save()
        
        return success_response(msg="技能设置成功")
    except Exception as e:
        return fail_response(msg=str(e))



