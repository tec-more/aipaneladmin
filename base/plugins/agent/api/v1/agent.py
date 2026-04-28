"""
Agent API routes
"""
from typing import List, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from base.plugins.agent.schemas.agent import AgentCreate, AgentUpdate, AgentResponse
from base.plugins.agent.services.agent_service import AgentService
from base.common.response import success_response, fail_response
import uuid
import asyncio

# 执行管理器 - 跟踪所有执行的任务
execution_manager = {
    # execution_id: {
    #     'task': asyncio.Task,
    #     'agent_id': int,
    #     'is_cancelled': bool
    # }
}

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


async def sse_execution_generator(agent, input_data, execution_id: str) -> AsyncGenerator[str, None]:
    """SSE事件生成器 - 实时推送执行过程（支持边思考边输出）"""
    import json
    from datetime import datetime
    from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
    
    print(f"[Execution] 开始执行，execution_id: {execution_id}")
    
    # 创建SSE推送函数 - 直接return字符串，yield是主函数调用
    def send_event(event_data):
        """SSE数据推送helper"""
        return f"data: {json.dumps({**event_data, 'timestamp': datetime.now().isoformat()}, ensure_ascii=False)}\n\n"
    
    # 检查是否被取消的辅助函数
    async def check_cancelled():
        exec_info = execution_manager.get(execution_id)
        return exec_info and exec_info.get('is_cancelled', False)
    
    # 推送开始
    yield send_event({'type': 'start', 'execution_id': execution_id, 'message': '开始执行智能体'})
    
    try:
        import asyncio
        
        # 创建 SSE 队列供 LangGraph 使用
        class SSEQueue:
            def __init__(self):
                self.queue = asyncio.Queue()
            
            async def put(self, event):
                await self.queue.put(event)
            
            async def get(self):
                return await self.queue.get()
            
            def empty(self):
                return self.queue.empty()
        
        sse_queue = SSEQueue()
        
        # 创建包装后的 sse_yield_func，把数据推送到队列
        async def wrapped_sse_yield(event):
            logger.info(f"[agent API] wrapped_sse_yield 收到事件: {event}")
            await sse_queue.put(event)
            logger.info(f"[agent API] 事件已入队列")
        
        # 启动 LangGraph 执行任务
        async def execute_task():
            try:
                return await LangGraphExecutor.execute_agent(
                    agent=agent,
                    input_data=input_data,
                    sse_yield_func=wrapped_sse_yield
                )
            except Exception as e:
                print(f"[LangGraph 执行失败] {e}")
                import traceback
                traceback.print_exc()
                return {
                    "success": False,
                    "message": str(e),
                    "traceback": traceback.format_exc()
                }
        
        # 同时运行执行和队列消费
        task = asyncio.create_task(execute_task())
        
        # 推送初始化信息
        yield send_event({'type': 'info', 'label': '初始化', 'message': '初始化执行环境...'})
        
        # 消费队列中的事件
        done = False
        while not done or not sse_queue.empty():
            try:
                # 检查取消
                if await check_cancelled():
                    print(f"[Execution] 检测到取消信号，停止执行")
                    yield send_event({'type': 'cancelled', 'message': '执行被用户中断'})
                    task.cancel()
                    break
                
                # 尝试获取队列事件
                try:
                    if not sse_queue.empty():
                        event = await asyncio.wait_for(sse_queue.get(), timeout=0.01)
                        logger.info(f"[agent API] 从队列获取事件: {event}")
                        yield send_event(event)
                except asyncio.TimeoutError:
                    pass
                except Exception as e:
                    logger.error(f"[agent API] 获取或发送事件失败: {e}")
                
                # 检查任务完成
                if task.done():
                    done = True
                    
            except Exception as e:
                print(f"[SSE 推送失败] {e}")
                break
        
        # 获取执行结果
        try:
            if not task.cancelled():
                result = await task
                
                # 推送完成事件
                yield send_event({
                    'type': 'complete',
                    'result': result.get('output', {}),
                    'variables': result.get('variables', {})
                })
        except Exception as e:
            print(f"获取执行结果失败: {e}")
            yield send_event({'type': 'error', 'message': str(e)})
        
    except Exception as e:
        import traceback
        yield send_event({'type': 'error', 'message': str(e), 'traceback': traceback.format_exc()})


@agent_router.post("/{agent_id}/graph/execute/sse")
async def execute_agent_graph_sse(agent_id: int, input_data: dict):
    """使用SSE实时执行智能体结构图 - 简化版本"""
    try:
        from base.plugins.agent.models.agent import Agent
        
        agent = await Agent.get_or_none(id=agent_id)
        if not agent:
            return fail_response(msg="智能体不存在", code=404)
        
        # 生成执行ID
        execution_id = str(uuid.uuid4())
        print(f"[API] 创建执行任务，execution_id: {execution_id}")
        
        # 注册执行
        execution_manager[execution_id] = {'agent_id': agent_id, 'is_cancelled': False}
        
        async def sse_generator():
            """SSE事件生成器"""
            try:
                # 直接执行并yield事件
                async for data in sse_execution_generator(agent, input_data, execution_id):
                    yield data
            finally:
                # 清理
                print(f"[API] 清理执行任务，execution_id: {execution_id}")
                if execution_id in execution_manager:
                    del execution_manager[execution_id]
        
        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive", 
                "Access-Control-Allow-Origin": "*",
                "X-Accel-Buffering": "no"
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
        
        return success_response(data={"graph_definition": agent.graph_definition})
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
async def process_documents(directory_path: str = Query(..., description="文档目录路径"), vector_store_path: str = Query(..., description="向量库存储路径")):
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
            data={"vector_store_path": vector_store_path, "collection_name": collection_name, "document_count": document_count, "message": f"成功处理文档并生成向量库，共处理 {document_count} 个文档片段"},
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


@agent_router.post("/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """取消执行中的任务"""
    try:
        print(f"[API] 收到取消请求，execution_id: {execution_id}")
        
        # 检查执行是否存在
        exec_info = execution_manager.get(execution_id)
        if not exec_info:
            return fail_response(msg="执行任务不存在或已结束", code=404)
        
        # 标记为取消
        exec_info['is_cancelled'] = True
        print(f"[API] 已标记任务为取消状态，execution_id: {execution_id}")
        
        return success_response(msg="取消请求已发送，执行将在安全点停止")
    except Exception as e:
        import traceback
        print(f"[API] 取消执行错误: {e}")
        print(traceback.format_exc())
        return fail_response(msg=str(e), code=500)


@agent_router.get("/executions")
async def list_executions():
    """列出所有正在执行的任务"""
    try:
        executions_list = []
        for exec_id, exec_info in execution_manager.items():
            executions_list.append({'execution_id': exec_id, 'agent_id': exec_info.get('agent_id'), 'is_cancelled': exec_info.get('is_cancelled', False)})
        
        return success_response(data={"executions": executions_list, "count": len(executions_list)})
    except Exception as e:
        import traceback
        print(f"[API] 列执行错误: {e}")
        print(traceback.format_exc())
        return fail_response(msg=str(e), code=500)
