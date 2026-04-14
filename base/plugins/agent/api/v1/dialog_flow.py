from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from base.plugins.agent.schemas.dialog_flow import (
    DialogFlowCreate, DialogFlowUpdate, DialogFlowResponse,
    DialogFlowNodeCreate, DialogFlowNodeUpdate, DialogFlowNodeResponse,
    DialogFlowEdgeCreate, DialogFlowEdgeUpdate, DialogFlowEdgeResponse,
    DialogFlowExecutionCreate, DialogFlowExecutionResponse
)
from base.plugins.agent.services.dialog_flow_service import DialogFlowService
from base.common.response import success_response, fail_response

dialog_flow_router = APIRouter()


@dialog_flow_router.post("/dialog-flows")
async def create_dialog_flow(data: DialogFlowCreate):
    """创建新的对话流"""
    try:
        dialog_flow = await DialogFlowService.create_dialog_flow(data)
        return success_response(data=dialog_flow, msg="对话流创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@dialog_flow_router.get("/dialog-flows/{dialog_flow_id}")
async def get_dialog_flow(dialog_flow_id: int):
    """根据ID获取对话流详情"""
    dialog_flow = await DialogFlowService.get_dialog_flow(dialog_flow_id)
    if not dialog_flow:
        return fail_response(msg="对话流不存在", code=404)
    return success_response(data=dialog_flow)


@dialog_flow_router.get("/dialog-flows")
async def list_dialog_flows(
    agent_id: Optional[int] = Query(None, description="智能体ID"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数")
):
    """列出对话流，可按智能体ID过滤"""
    dialog_flows = await DialogFlowService.list_dialog_flows(agent_id, skip, limit)
    return success_response(data={"items": dialog_flows, "total": len(dialog_flows)})


@dialog_flow_router.put("/dialog-flows/{dialog_flow_id}")
async def update_dialog_flow(dialog_flow_id: int, data: DialogFlowUpdate):
    """更新对话流信息"""
    dialog_flow = await DialogFlowService.update_dialog_flow(dialog_flow_id, data)
    if not dialog_flow:
        return fail_response(msg="对话流不存在", code=404)
    return success_response(data=dialog_flow, msg="对话流更新成功")


@dialog_flow_router.delete("/dialog-flows/{dialog_flow_id}")
async def delete_dialog_flow(dialog_flow_id: int):
    """删除对话流"""
    success = await DialogFlowService.delete_dialog_flow(dialog_flow_id)
    if not success:
        return fail_response(msg="对话流不存在", code=404)
    return success_response(msg="对话流删除成功")


@dialog_flow_router.post("/dialog-flows/{dialog_flow_id}/nodes")
async def create_node(dialog_flow_id: int, data: DialogFlowNodeCreate):
    """在指定对话流中创建节点"""
    data.dialog_flow_id = dialog_flow_id
    try:
        node = await DialogFlowService.create_node(data)
        return success_response(data=node, msg="节点创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@dialog_flow_router.get("/dialog-flows/{dialog_flow_id}/nodes")
async def list_nodes(dialog_flow_id: int):
    """列出指定对话流的所有节点"""
    nodes = await DialogFlowService.list_nodes(dialog_flow_id)
    return success_response(data=nodes)


@dialog_flow_router.get("/dialog-flow-nodes/{node_id}")
async def get_node(node_id: int):
    """根据ID获取对话流节点"""
    node = await DialogFlowService.get_node(node_id)
    if not node:
        return fail_response(msg="节点不存在", code=404)
    return success_response(data=node)


@dialog_flow_router.put("/dialog-flow-nodes/{node_id}")
async def update_node(node_id: int, data: DialogFlowNodeUpdate):
    """更新对话流节点信息"""
    node = await DialogFlowService.update_node(node_id, data)
    if not node:
        return fail_response(msg="节点不存在", code=404)
    return success_response(data=node, msg="节点更新成功")


@dialog_flow_router.delete("/dialog-flow-nodes/{node_id}")
async def delete_node(node_id: int):
    """删除对话流节点"""
    success = await DialogFlowService.delete_node(node_id)
    if not success:
        return fail_response(msg="节点不存在", code=404)
    return success_response(msg="节点删除成功")


@dialog_flow_router.post("/dialog-flows/{dialog_flow_id}/edges")
async def create_edge(dialog_flow_id: int, data: DialogFlowEdgeCreate):
    """在指定对话流中创建边"""
    data.dialog_flow_id = dialog_flow_id
    try:
        edge = await DialogFlowService.create_edge(data)
        return success_response(data=edge, msg="边创建成功")
    except Exception as e:
        return fail_response(msg=str(e))


@dialog_flow_router.get("/dialog-flows/{dialog_flow_id}/edges")
async def list_edges(dialog_flow_id: int):
    """列出指定对话流的所有边"""
    edges = await DialogFlowService.list_edges(dialog_flow_id)
    return success_response(data=edges)


@dialog_flow_router.get("/dialog-flow-edges/{edge_id}")
async def get_edge(edge_id: int):
    """根据ID获取对话流边"""
    edge = await DialogFlowService.get_edge(edge_id)
    if not edge:
        return fail_response(msg="边不存在", code=404)
    return success_response(data=edge)


@dialog_flow_router.put("/dialog-flow-edges/{edge_id}")
async def update_edge(edge_id: int, data: DialogFlowEdgeUpdate):
    """更新对话流边信息"""
    edge = await DialogFlowService.update_edge(edge_id, data)
    if not edge:
        return fail_response(msg="边不存在", code=404)
    return success_response(data=edge, msg="边更新成功")


@dialog_flow_router.delete("/dialog-flow-edges/{edge_id}")
async def delete_edge(edge_id: int):
    """删除对话流边"""
    success = await DialogFlowService.delete_edge(edge_id)
    if not success:
        return fail_response(msg="边不存在", code=404)
    return success_response(msg="边删除成功")


@dialog_flow_router.post("/dialog-flows/execute")
async def execute_dialog_flow(data: DialogFlowExecutionCreate):
    """执行指定的对话流"""
    try:
        execution = await DialogFlowService.execute_dialog_flow(
            dialog_flow_id=data.dialog_flow_id,
            input_data=data.input_data,
            agent_id=data.agent_id,
            user_id=data.user_id
        )
        return success_response(data=execution, msg="对话流执行成功")
    except Exception as e:
        return fail_response(msg=str(e))


@dialog_flow_router.get("/dialog-flow-executions/{execution_id}")
async def get_execution(execution_id: int):
    """根据ID获取对话流执行记录"""
    execution = await DialogFlowService.get_execution(execution_id)
    if not execution:
        return fail_response(msg="执行记录不存在", code=404)
    return success_response(data=execution)


@dialog_flow_router.get("/dialog-flow-executions")
async def list_executions(
    dialog_flow_id: Optional[int] = Query(None, description="对话流ID"),
    agent_id: Optional[int] = Query(None, description="智能体ID"),
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数")
):
    """列出对话流执行记录，可按对话流ID或智能体ID过滤"""
    executions = await DialogFlowService.list_executions(dialog_flow_id, agent_id, skip, limit)
    return success_response(data={"items": executions, "total": len(executions)})
