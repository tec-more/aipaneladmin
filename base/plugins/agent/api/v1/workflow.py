"""
Workflow API routes
"""
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from base.plugins.agent.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowNodeResponse,
    WorkflowEdgeCreate, WorkflowEdgeUpdate, WorkflowEdgeResponse,
    WorkflowExecutionCreate, WorkflowExecutionResponse
)
from base.plugins.agent.services.workflow_service import WorkflowService
from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
from base.plugins.agent.services.checkpoint_service import CheckpointService
from base.common.security import get_current_actor
from base.common.response import success_response, fail_response
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

workflow_execution_manager = {
}

workflow_router = APIRouter(prefix="/workflows", tags=["workflows"])
workflow_execution_router = APIRouter(prefix="/workflow-executions", tags=["workflow-executions"])


@workflow_router.post("/")
async def create_workflow(workflow: WorkflowCreate):
    """Create a new workflow"""
    try:
        created_workflow = await WorkflowService.create_workflow(workflow)
        
        data = {
            "id": created_workflow.id,
            "name": created_workflow.name,
            "description": created_workflow.description,
            "status": created_workflow.status,
            "definition": created_workflow.definition,
            "agent_ids": [],
            "created_at": created_workflow.created_at.isoformat() if created_workflow.created_at else None,
            "updated_at": created_workflow.updated_at.isoformat() if created_workflow.updated_at else None,
            "node_count": 0,
            "edge_count": 0
        }
        return success_response(data=data, msg="工作流创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@workflow_router.post("/import")
async def import_workflow(import_data: dict):
    """Import workflow from template"""
    try:
        imported_workflow = await WorkflowService.import_workflow(import_data)
        
        definition = imported_workflow.definition or {}
        node_count = len(definition.get('nodes', []))
        edge_count = len(definition.get('edges', []))
        
        data = {
            "id": imported_workflow.id,
            "name": imported_workflow.name,
            "description": imported_workflow.description,
            "status": imported_workflow.status,
            "definition": imported_workflow.definition,
            "created_at": imported_workflow.created_at.isoformat() if imported_workflow.created_at else None,
            "updated_at": imported_workflow.updated_at.isoformat() if imported_workflow.updated_at else None,
            "node_count": node_count,
            "edge_count": edge_count
        }
        
        return success_response(data=data, msg="工作流导入成功")
    except Exception as e:
        import traceback
        return fail_response(msg=f"导入失败: {str(e)}", data={"traceback": traceback.format_exc()})


@workflow_router.get("/")
async def get_workflows(skip: int = 0, limit: int = 100, name: str = "", status: str = ""):
    """Get all workflows"""
    from base.plugins.agent.models.workflow import Workflow
    
    # 构建查询条件
    query = Workflow.all()
    
    if name:
        query = query.filter(name__icontains=name)
    
    if status:
        query = query.filter(status=status)
    
    # 获取总数
    total = await query.count()
    
    # 获取分页数据
    workflows = await query.offset(skip).limit(limit).order_by("-created_at").all()
    
    response = []
    for workflow in workflows:
        response.append({
            "id": workflow.id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status,
            "definition": workflow.definition,
            "agent_ids": [],
            "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
            "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
            "node_count": 0,
            "edge_count": 0
        })
    return success_response(data={"items": response, "total": total})


@workflow_router.get("/{workflow_id}")
async def get_workflow(workflow_id: int):
    """Get workflow by ID"""
    workflow = await WorkflowService.get_workflow_by_id(workflow_id)
    if not workflow:
        return fail_response(msg="工作流不存在", code=404)
    
    data = {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "definition": workflow.definition,
        "agent_ids": [],
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
        "node_count": 0,
        "edge_count": 0
    }
    return success_response(data=data)


@workflow_router.put("/{workflow_id}")
async def update_workflow(workflow_id: int, workflow: WorkflowUpdate):
    """Update workflow"""
    updated_workflow = await WorkflowService.update_workflow(workflow_id, workflow)
    if not updated_workflow:
        return fail_response(msg="工作流不存在", code=404)
    
    data = {
        "id": updated_workflow.id,
        "name": updated_workflow.name,
        "description": updated_workflow.description,
        "status": updated_workflow.status,
        "definition": updated_workflow.definition,
        "agent_ids": [],
        "created_at": updated_workflow.created_at.isoformat() if updated_workflow.created_at else None,
        "updated_at": updated_workflow.updated_at.isoformat() if updated_workflow.updated_at else None,
        "node_count": 0,
        "edge_count": 0
    }
    return success_response(data=data, msg="工作流更新成功")


@workflow_router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: int):
    """Delete workflow"""
    success = await WorkflowService.delete_workflow(workflow_id)
    if not success:
        return fail_response(msg="工作流不存在", code=404)
    return success_response(msg="工作流删除成功")


@workflow_router.post("/{workflow_id}/nodes")
async def create_workflow_node(workflow_id: int, node: WorkflowNodeCreate):
    """Create workflow node"""
    try:
        node_data = node.model_dump()
        created_node = await WorkflowService.create_workflow_node(workflow_id, node_data)
        data = {
            "id": created_node.id,
            "workflow_id": workflow_id,
            "name": created_node.name,
            "type": created_node.type,
            "config": created_node.config,
            "position": created_node.position,
            "agent_id": created_node.agent_id,
            "skill_id": created_node.skill_id,
            "created_at": created_node.created_at.isoformat() if created_node.created_at else None,
            "updated_at": created_node.updated_at.isoformat() if created_node.updated_at else None
        }
        return success_response(data=data, msg="节点创建成功")
    except ValueError as e:
        return fail_response(msg=str(e), code=404)
    except Exception as e:
        return fail_response(msg=str(e))


@workflow_router.post("/{workflow_id}/edges")
async def create_workflow_edge(workflow_id: int, edge: WorkflowEdgeCreate):
    """Create workflow edge"""
    try:
        edge_data = edge.model_dump()
        created_edge = await WorkflowService.create_workflow_edge(workflow_id, edge_data)
        data = {
            "id": created_edge.id,
            "workflow_id": workflow_id,
            "source_node_id": created_edge.source_node_id,
            "target_node_id": created_edge.target_node_id,
            "condition": created_edge.condition,
            "label": created_edge.label,
            "created_at": created_edge.created_at.isoformat() if created_edge.created_at else None,
            "updated_at": created_edge.updated_at.isoformat() if created_edge.updated_at else None
        }
        return success_response(data=data, msg="边创建成功")
    except ValueError as e:
        return fail_response(msg=str(e), code=404)
    except Exception as e:
        return fail_response(msg=str(e))


@workflow_router.get("/{workflow_id}/graph")
async def get_workflow_graph(workflow_id: int):
    """Get workflow graph definition"""
    try:
        logger.info(f"=== 获取工作流结构图: workflow_id={workflow_id} ===")
        
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            logger.error(f"工作流不存在: workflow_id={workflow_id}")
            return fail_response(msg="工作流不存在", code=404)
        
        logger.info(f"workflow.definition: {workflow.definition}")
        
        return success_response(data={"graph_definition": workflow.definition})
    except Exception as e:
        logger.exception(f"获取工作流结构图失败: {e}")
        return fail_response(msg=str(e))


@workflow_router.put("/{workflow_id}/graph")
async def update_workflow_graph(workflow_id: int, graph_data: dict):
    """Update workflow graph definition"""
    try:
        logger.info(f"=== 保存工作流结构图: workflow_id={workflow_id} ===")
        logger.info(f"接收到的 graph_data: {graph_data}")
        
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            logger.error(f"工作流不存在: workflow_id={workflow_id}")
            return fail_response(msg="工作流不存在", code=404)
        
        logger.info(f"保存前 workflow.definition: {workflow.definition}")
        
        workflow.definition = graph_data
        await workflow.save()
        
        logger.info(f"保存后 workflow.definition: {workflow.definition}")
        
        return success_response(data={"graph_definition": workflow.definition}, msg="工作流结构图保存成功")
    except Exception as e:
        logger.exception(f"保存工作流结构图失败: {e}")
        return fail_response(msg=str(e))


@workflow_router.post("/{workflow_id}/execute")
async def execute_workflow_unified(
    workflow_id: int,
    input_data: dict,
    stream: Optional[bool] = Query(None, description="是否强制使用流式返回"),
    actor: dict = Depends(get_current_actor)
):
    """
    统一工作流执行接口
    根据工作流图结构自动判断使用普通模式还是SSE模式
    
    Args:
        workflow_id: 工作流ID
        input_data: 输入数据
        stream: 是否强制使用流式返回（可选）
        actor: 当前用户（从依赖注入获取）
    
    Returns:
        普通响应或SSE流式响应
    """
    try:
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            return fail_response(msg="工作流不存在", code=404)
        
        if workflow.status != "active":
            return fail_response(msg="工作流未激活", code=400)
        
        checkpoint_service = CheckpointService.get_instance()
        use_sse = stream if stream is not None else WorkflowService.should_use_sse(workflow)
        
        if use_sse:
            for exec_id, info in workflow_execution_manager.items():
                if info.get('workflow_id') == workflow_id:
                    return fail_response(msg="工作流正在执行中，请稍后再试", code=409)
            
            flow_data = workflow.definition or {}
            nodes = flow_data.get("nodes", [])
            
            print(f"[Workflow API] 开始预加载资源...")
            try:
                llm_resources = await LangGraphExecutor._preload_llm_resources(nodes)
                skill_resources = await LangGraphExecutor._preload_skill_resources(nodes)
                print(f"[Workflow API] 预加载成功，LLM资源: {len(llm_resources)}, 技能资源: {len(skill_resources)}")
            except ValueError as e:
                print(f"[Workflow API] 预加载失败: {e}")
                return fail_response(msg=str(e), code=400)
            except Exception as e:
                print(f"[Workflow API] 预加载异常: {e}")
                import traceback
                traceback.print_exc()
                return fail_response(msg=f"资源预加载失败: {str(e)}", code=500)
            
            logger.info(f"[Workflow API] input_data: {input_data.get('text', '')}")
            execution_id = input_data.get('execution_id', '')
            execution_id = execution_id or checkpoint_service.create_thread_id(actor, execution_id)
            
            workflow_execution_manager[execution_id] = {
                'workflow_id': workflow_id,
                'is_cancelled': False,
                '_llm_resources': llm_resources,
                '_skill_resources': skill_resources
            }
            
            class MockAgent:
                def __init__(self, definition, wid, wname):
                    self.graph_definition = definition
                    self.id = wid
                    self.name = wname
            
            mock_agent = MockAgent(flow_data, workflow_id, workflow.name)
            
            async def sse_generator():
                try:
                    async for data in WorkflowService.sse_execution_generator(
                        mock_agent, input_data, execution_id, workflow_execution_manager, actor
                    ):
                        yield data
                finally:
                    if execution_id in workflow_execution_manager:
                        del workflow_execution_manager[execution_id]
            
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
        else:
            execution_id = input_data.get('execution_id', '') or checkpoint_service.create_thread_id(actor, '')
            result = await WorkflowService.execute_workflow_direct(workflow_id, input_data, actor, execution_id)
            if result.get("success"):
                return success_response(data=result, msg="工作流执行成功")
            else:
                return fail_response(msg=result.get("message", "执行失败"))
    
    except Exception as e:
        import traceback
        return fail_response(msg=str(e), data={"traceback": traceback.format_exc()}, code=500)


@workflow_execution_router.post("/{execution_id}/cancel")
async def cancel_workflow_execution(execution_id: str):
    """取消执行中的工作流任务"""
    try:
        print(f"[Workflow API] 收到取消请求，execution_id: {execution_id}")
        
        exec_info = workflow_execution_manager.get(execution_id)
        if not exec_info:
            return fail_response(msg="执行任务不存在或已结束", code=404)
        
        exec_info['is_cancelled'] = True
        print(f"[Workflow API] 已标记任务为取消状态，execution_id: {execution_id}")
        
        return success_response(msg="取消请求已发送，执行将在安全点停止")
    except Exception as e:
        import traceback
        print(f"[Workflow API] 取消执行错误: {e}")
        print(traceback.format_exc())
        return fail_response(msg=str(e), code=500)


@workflow_execution_router.get("/running")
async def list_running_workflow_executions():
    """列出所有正在执行的工作流任务"""
    try:
        executions_list = []
        for exec_id, exec_info in workflow_execution_manager.items():
            executions_list.append({
                'execution_id': exec_id,
                'workflow_id': exec_info.get('workflow_id'),
                'is_cancelled': exec_info.get('is_cancelled', False)
            })
        
        return success_response(data={"executions": executions_list, "count": len(executions_list)})
    except Exception as e:
        import traceback
        print(f"[Workflow API] 列执行错误: {e}")
        print(traceback.format_exc())
        return fail_response(msg=str(e), code=500)


@workflow_execution_router.get("/")
async def get_all_workflow_executions(skip: int = 0, limit: int = 100, status: str = ""):
    """Get all workflow executions"""
    try:
        from base.plugins.agent.models.workflow import WorkflowExecution
        
        # 先获取总数
        query = WorkflowExecution.all()
        if status:
            query = query.filter(status=status)
        total = await query.count()
        
        # 获取分页数据
        executions = await WorkflowService.get_all_workflow_executions(skip=skip, limit=limit, status=status)
        response = []
        for execution in executions:
            response.append({
                "id": execution.id,
                "workflow_id": execution.workflow_id,
                "input_data": execution.input_data,
                "status": execution.status,
                "output_data": execution.output_data,
                "error_message": execution.error_message,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "created_at": execution.created_at.isoformat() if execution.created_at else None,
                "updated_at": execution.updated_at.isoformat() if execution.updated_at else None
            })
        return success_response(data={"items": response, "total": total})
    except Exception as e:
        return fail_response(msg=str(e))


@workflow_execution_router.get("/{execution_id}")
async def get_workflow_execution(execution_id: int):
    """Get workflow execution by ID"""
    try:
        execution = await WorkflowService.get_workflow_execution_by_id(execution_id)
        if not execution:
            return fail_response(msg="执行记录不存在", code=404)
        
        data = {
            "id": execution.id,
            "workflow_id": execution.workflow_id,
            "input_data": execution.input_data,
            "status": execution.status,
            "output_data": execution.output_data,
            "error_message": execution.error_message,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "created_at": execution.created_at.isoformat() if execution.created_at else None,
            "updated_at": execution.updated_at.isoformat() if execution.updated_at else None
        }
        return success_response(data=data)
    except Exception as e:
        return fail_response(msg=str(e))
