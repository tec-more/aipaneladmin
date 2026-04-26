"""
Workflow API routes
"""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from base.plugins.agent.schemas.workflow import (
    WorkflowCreate, WorkflowUpdate, WorkflowResponse,
    WorkflowNodeCreate, WorkflowNodeUpdate, WorkflowNodeResponse,
    WorkflowEdgeCreate, WorkflowEdgeUpdate, WorkflowEdgeResponse,
    WorkflowExecutionCreate, WorkflowExecutionResponse
)
from base.plugins.agent.services.workflow_service import WorkflowService
from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
from base.common.response import success_response, fail_response

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


@workflow_router.post("/{workflow_id}/execute")
async def execute_workflow(workflow_id: int, input_data: Dict[str, Any]):
    """Execute workflow using LangGraph"""
    try:
        workflow = await WorkflowService.get_workflow_by_id(workflow_id)
        if not workflow:
            return fail_response(msg="工作流不存在", code=404)
        
        flow_data = workflow.definition or {}
        
        # 使用 LangGraph 执行工作流
        # 创建一个临时的 agent 对象（或者扩展 LangGraphExecutor 支持 workflow）
        # 这里我们直接调用 LangGraphExecutor 的核心逻辑
        # 或者创建一个通用的执行函数
        
        # 临时方案：直接使用 LangGraphExecutor 的内部方法
        from base.plugins.agent.services.langgraph_executor import LangGraphExecutor
        
        # 创建一个 mock agent
        class MockAgent:
            def __init__(self, definition):
                self.graph_definition = definition
                self.id = workflow_id
                self.name = workflow.name
        
        mock_agent = MockAgent(flow_data)
        
        # 执行
        result = await LangGraphExecutor.execute_agent(mock_agent, input_data)
        
        return success_response(data=result, msg="工作流执行成功")
    except ValueError as e:
        return fail_response(msg=str(e), code=404)
    except Exception as e:
        return fail_response(msg=str(e))


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
